import threading

import dukpy

from CSSParser import CSSParser
from HTMLParser import HTMLParser
from Helper.style import tree_to_list
from Helper.task import Task
from Requests.request import resolve_url, url_origin, RequestHandler

EVENT_DISPATCH_CODE = "new Node(dukpy.handle).dispatchEvent(new Event(dukpy.type))"
SETTIMEOUT_CODE = "__runSetTimeout(dukpy.handle)"
XHR_ONLOAD_CODE = "__runXHROnload(dukpy.out, dukpy.handle)"


class JSContext:
    def __init__(self, tab):
        self.tab = tab
        self.node_to_handle = {}
        self.handle_to_node = {}
        self.rq = RequestHandler()
        # export js functions to corresponding python functions
        self.interp = dukpy.JSInterpreter()
        self.interp.export_function("log", print)
        self.interp.export_function("querySelectorAll", self.query_selector_all)
        self.interp.export_function("getAttribute", self.get_attribute)
        self.interp.export_function("innerHTML_set", self.innerHTML_set)
        self.interp.export_function("setTimeout", self.setTimeout)
        with open("Sheets/runtime.js") as f:
            self.interp.evaljs(f.read())

    def run(self, code):
        return self.interp.evaljs(code)

    def query_selector_all(self, selector_text):
        # find all nodes matching a selector
        selector = CSSParser(selector_text).selector()
        nodes = [node for node
                 in tree_to_list(self.tab.nodes, [])
                 if selector.matches(node)]
        return [self.get_handle(node) for node in nodes]

    def get_handle(self, elt):
        # create a new handle if one doesn't exist yet
        if elt not in self.node_to_handle:
            handle = len(self.node_to_handle)
            self.node_to_handle[elt] = handle
            self.handle_to_node[handle] = elt
        else:
            handle = self.node_to_handle[elt]
        return handle

    def get_attribute(self, handle, attr):
        elt = self.handle_to_node[handle]
        return elt.attributes.get(attr, None)

    def innerHTML_set(self, handle, s):
        # parse the HTML string
        doc = HTMLParser("<html><body>" + s + "</body></html>").parse()
        new_nodes = doc.children[0].children
        # extract all children of the body element
        elt = self.handle_to_node[handle]
        elt.children = new_nodes
        for child in elt.children:
            child.parent = elt
        # modify the web page
        self.tab.render()

    def XMLHttpRequest_send(self, method, url, body):
        # resolve the url and do security checks
        full_url = resolve_url(url, self.tab.url)
        # prevent cross site scripting
        if not self.tab.allowed_request(full_url):
            raise Exception("Cross-origin XHR blocked by CSP")
        headers, out = self.rq.request(full_url, self.tab.url, payload=body)
        # implement same origin policy
        if url_origin(full_url) != url_origin(self.tab.url):
            raise Exception("Cross-origin XHR request not allowed")

        # function which makes a request and enqueues a task for running callbacks
        def run_load():
            headers, response = self.rq.request(full_url, self.tab.url, body)
            task = Task(self.dispatch_xhr_onload, response, handle)
            self.tab.task_runner.schedule_task(task)
            if not isasync:
                return response
        # browser can decide to call this right away or in a new thread
        if not isasync:
            return run_load()
        else:
            threading.Thread(target=run_load).start()
        return out

    def setTimeout(self, handle, time):
        def run_callback():
            task = Task(self.dispatch_set_timeout, handle)
            self.tab.task_runner.schedule_task(task)

        threading.Timer(time / 1000.0, run_callback).start()

    def dispatch_event(self, event_type, elt):
        handle = self.node_to_handle.get(elt, -1)
        do_default = self.interp.evaljs(EVENT_DISPATCH_CODE, type=event_type, handle=handle)
        return not do_default

    def dispatch_set_timeout(self, handle):
        self.interp.evaljs(SETTIMEOUT_CODE, handle=handle)

    def dispatch_xhr_onload(self, out, handle):
        do_default = self.interp.evaljs(
            XHR_ONLOAD_CODE, out=out, handle=handle)
