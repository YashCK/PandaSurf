import math
import os
import urllib.parse

import skia

from CSSParser import CSSParser
from HTMLParser import HTMLParser
from Helper.measure_time import MeasureTime
from Helper.task import TaskRunner, Task, CommitData, SingleThreadedTaskRunner
from JSContext import JSContext
from Layouts.document_layout import DocumentLayout
from Layouts.input_layout import InputLayout
from Requests.header import Header
from Requests.request import resolve_url, RequestHandler, url_origin
from Helper.draw import DrawLine, absolute_bounds_for_obj
from Helper.style import style, tree_to_list
from Helper.tokens import Text, Element


class Tab:
    WIDTH, HEIGHT = 1000, 800
    HSTEP, VSTEP = 13, 18
    SCROLL_STEP = 70
    CHROME_PX = 80
    LAST_SCROLL = False  # Was not Down

    def __init__(self, browser, bookmarks):
        # to set up display
        self.rq = RequestHandler()
        self.nodes = None
        self.url = None
        self.document = None
        self.display_list = []
        # what should be shown on screen
        self.font_delta = 0
        # browser info
        self.scroll = 0
        self.composited_updates = []
        self.history = []
        self.future = []
        self.bookmarks = bookmarks
        self.focus = None
        self.rules = None
        self.js = None
        # what has changed
        self.browser = browser
        self.allowed_origins = None
        self.scroll_changed_in_tab = False
        self.needs_style = False
        self.needs_layout = False
        self.needs_paint = False
        # start tasks
        if browser.single_threaded:
            self.task_runner = SingleThreadedTaskRunner(self)
        else:
            self.task_runner = TaskRunner(self)
        self.task_runner.start_thread()
        self.measure_render = MeasureTime("render")
        # store browser's style sheet
        with open("Sheets/browser.css") as f:
            self.default_style_sheet = CSSParser(f.read()).parse()

    def load(self, url: str = None, payload=None):
        self.scroll = 0
        # reset pages and tasks
        self.scroll_changed_in_tab = True
        self.task_runner.clear_pending_tasks()
        # create headers
        user_agent_header = Header("User-Agent", "This is the PandaSurf Browser.")
        accept_encoding_header = Header("Accept-Encoding", "gzip")
        accept_language_header = Header('Accept-Language', 'en-US,en;q=0.9', )
        header_list = [user_agent_header, accept_encoding_header, accept_language_header]
        try:
            headers, body = None, None
            if url is None:
                url = "file://" + os.getcwd() + '/panda_surf_df.txt'
                self.url = url
                self.history.append(url)
            elif url == "about:bookmarks":
                data_url = self.construct_bookmarks_page()
                headers, body = self.rq.request(data_url, self.url)
                self.url = "about:bookmarks"
                self.history.append("about:bookmarks")
            else:
                headers, body = self.rq.request(url, self.url, header_list, payload)
                self.url = url
                self.history.append(url)
                # extract and parse content of Content-Security-Policy header
                self.allowed_origins = None
                if "content-security-policy" in headers:
                    csp = headers["content-security-policy"].split()
                    if len(csp) > 0 and csp[0] == "default-src":
                        self.allowed_origins = csp[1:]

            self.nodes = HTMLParser(body).parse()
            self.js = JSContext(self)
            # self.form_doc_layout()
            # if os.path.getsize("external.css") != 0:
            #     with open("external.css") as f:
            #         self.default_style_sheet = CSSParser(f.read()).parse()
            self.reload_document()
            self.set_needs_render()
        except FileNotFoundError:
            print("The path to the file you entered does not exist.")
        except ValueError:
            # construct URL
            google_url = "https://google.com/search?q="
            for c in url:
                if c == " ":
                    google_url += "+"
                else:
                    google_url += c
            # create headers list
            headers, body = self.rq.request(google_url, self.url, header_list)
            self.url = google_url
            self.history.append(google_url)
            self.nodes = HTMLParser(body).parse()
            self.reload_document()

    def reload_document(self):
        # find all the scripts
        scripts = [node.attributes["src"] for node
                   in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == "script"
                   and "src" in node.attributes]
        # run all the scripts
        for script in scripts:
            script_url = resolve_url(script, self.url)
            # check whether the request is allowed
            if not self.allowed_request(script_url):
                print("Blocked script", script, "due to CSP")
                continue
            header, body = self.rq.request(script_url, self.url)
            task = Task(self.js.run, script_url, body)
            self.task_runner.schedule_task(task)
        # copy rules
        self.rules = self.default_style_sheet.copy()
        # grab the URL of each linked style sheet
        links = [node.attributes["href"]
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and "href" in node.attributes
                 and node.attributes.get("rel") == "stylesheet"]
        # browser can request each linked style sheet and add its rules to the rules list
        for link in links:
            style_url = resolve_url(link, self.url)
            if not self.allowed_request(style_url):
                print("Blocked style", link, "due to CSP")
                continue
            try:
                header, body = self.rq.request(style_url, self.url)
            except:
                # ignores style sheets that fail to download
                continue
            self.rules.extend(CSSParser(body).parse())
        self.set_needs_render()

    def render(self):
        self.measure_render.start_timing()
        # redo the styling, layout, paint and draw phases
        # apply style in cascading order
        if self.needs_style:
            style(self.nodes, sorted(self.rules, key=cascade_priority), self)
            self.needs_layout = True
            self.needs_style = False
        # compute the layout to be displayed in the browser
        if self.needs_layout:
            self.document = DocumentLayout(self.nodes)
            self.document.layout(self.WIDTH, self.font_delta, self.url)
            self.needs_paint = True
            self.needs_layout = False
        # check if screen needs to be redrawn
        if self.needs_paint:
            self.display_list = []
            self.document.paint(self.display_list)
            # draw cursor if necessary
            if self.focus:
                obj = [obj for obj in tree_to_list(self.document, [])
                       if obj.node == self.focus and
                       isinstance(obj, InputLayout)][0]
                text = self.focus.attributes.get("value", "")
                x = obj.x + obj.font.measureText(text)
                y = obj.y
                self.display_list.append(DrawLine(x, y, x, y + obj.height))
            self.needs_paint = False
        self.measure_render.stop_timing()

    def configure(self, width, height):
        if self.WIDTH != 1 and self.HEIGHT != 1:
            self.WIDTH = width
            self.HEIGHT = height
            self.reload_document()

    def click(self, x, y):
        self.render()
        self.focus = None
        # account for scrolling
        y += self.scroll
        # what elements are at the location
        loc_rect = skia.Rect.MakeXYWH(x, y, 1, 1)
        objs = [obj for obj in tree_to_list(self.document, [])
                if absolute_bounds_for_obj(obj).intersects(loc_rect)]
        # which object is closest to the top
        if not objs: return
        elt = objs[-1].node
        # climb html tree to find element
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                if self.js.dispatch_event("click", elt): return
                if elt.attributes["href"].startswith("#"):
                    word_to_find = elt.attributes["href"]
                    self.url = resolve_url(word_to_find, self.url)
                    loc = self.find_location(elt.attributes.get("href"))
                    if loc is not None:
                        self.browser.scroll = loc[1]
                else:
                    # extract url and load it
                    url = resolve_url(elt.attributes["href"], self.url)
                    return self.load(url)
            elif elt.tag == "input":
                elt.attributes["value"] = ""
                if elt != self.focus:
                    self.set_needs_render()
                self.focus = elt
                return
            elif elt.tag == "button":
                if self.js.dispatch_event("click", elt): return
                while elt:
                    if elt.tag == "form" and "action" in elt.attributes:
                        return self.submit_form(elt)
                    elt = elt.parent
                break
            elt = elt.parent

    def find_location(self, identify):
        identify = identify[1:]
        last_x, last_y = None, None
        for obj in tree_to_list(self.document, []):
            if isinstance(obj.node, Element) and "id" in obj.node.attributes:
                if obj.node.attributes["id"] == identify:
                    last_x, last_y = obj.x, obj.y
        return last_x, last_y

    def submit_form(self, elt):
        if self.js.dispatch_event("submit", elt): return
        # look through the descendants of the form to find input elements
        inputs = [node for node in tree_to_list(elt, [])
                  if isinstance(node, Element)
                  and node.tag == "input"
                  and "name" in node.attributes]
        # extract name and value attributes, and form encode both of them
        body = ""
        for i in inputs:
            name = i.attributes["name"]
            value = i.attributes.get("value", "")
            # replace special characters
            name = urllib.parse.quote(name)
            value = urllib.parse.quote(value)
            body += "&" + name + "=" + value
        body = body[1:]
        # make a POST request
        url = resolve_url(elt.attributes["action"], self.url)
        self.load(url, body)

    def key_press_handler(self, key):
        match key:
            case '+':
                self.font_delta += 1
                self.set_needs_render()
            case '-':
                if self.font_delta > -10:
                    self.font_delta -= 1
                    self.set_needs_render()

    def keypress(self, char):
        if self.focus:
            if self.js.dispatch_event("keydown", self.focus): return
            self.focus.attributes["value"] += char
            self.set_needs_render()

    def go_back(self):
        if len(self.history) > 1:
            self.future.append(self.url)
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def go_forward(self):
        if len(self.future) >= 1:
            ahead = self.future.pop()
            self.load(ahead)

    def construct_bookmarks_page(self):
        page = "data:text/html,<!DOCTYPE html> \
                      <html> \
                      <head> \
                      <title>Bookmarks Page</title> \
                      </head> \
                      <body> "
        page += "<h1 class=\"title\">"
        page += "Bookmarks"
        page += "</h1>"
        for mark in self.bookmarks:
            page += "<h1 class=\"title\">"
            page += mark
            page += "</h1>"
        page += "<br> <br> </body> </html> "
        return page

    def allowed_request(self, url):
        return self.allowed_origins is None or url_origin(url) in self.allowed_origins

    def set_needs_render(self):
        self.needs_style = True
        self.browser.set_needs_animation_frame(self)

    def set_needs_layout(self):
        self.needs_layout = True
        self.browser.set_needs_animation_frame(self)

    def set_needs_paint(self):
        self.needs_paint = True
        self.browser.set_needs_animation_frame(self)

    def run_animation_frame(self, scroll):
        if not self.scroll_changed_in_tab:
            self.scroll = scroll
        self.js.interp.evaljs("__runRAFHandlers()")
        #  during an animation, run layout and paint, but not style
        for node in tree_to_list(self.nodes, []):
            for (property_name, animation) in node.animations.items():
                value = animation.animate()
                if value:
                    node.style[property_name] = value
                    if property_name == "opacity":
                        self.composited_updates.append(node)
                        self.set_needs_paint()
                    else:
                        self.set_needs_layout()
        needs_composite = self.needs_style or self.needs_layout
        self.render()
        # set scroll_changed_in_tab when loading a new page or when
        # browser thread’s scroll offset is past the bottom of page
        document_height = math.ceil(self.document.height)
        clamped_scroll = self.clamp_scroll(self.scroll, document_height)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_tab = True
        self.scroll = clamped_scroll
        # If main thread has not overridden the browser’s scroll offset, set scroll offset to None
        scroll = None
        if self.scroll_changed_in_tab:
            scroll = self.scroll
        # composited updates
        composited_updates = {}
        if not needs_composite:
            for node in self.composited_updates:
                composited_updates[node] = node.save_layer
        self.composited_updates = []
        # commit data
        commit_data = CommitData(self.url, scroll, document_height, self.display_list, composited_updates,)
        self.display_list = None
        self.scroll_changed_in_tab = False
        self.browser.commit(self, commit_data)

    def clamp_scroll(self, scroll, tab_height):
        return max(0, min(scroll, tab_height - (self.HEIGHT - self.CHROME_PX)))


def cascade_priority(rule):
    selector, body = rule
    return selector.priority
