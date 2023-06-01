import os
import urllib.parse

import dukpy

from CSSParser import CSSParser
from HTMLParser import HTMLParser
from Helper.task import TaskRunner, Task
from JSContext import JSContext
from Layouts.document_layout import DocumentLayout
from Layouts.input_layout import InputLayout
from Requests.header import Header
from Requests.request import resolve_url, RequestHandler, url_origin
from Helper.draw import DrawLine
from Helper.style import style, tree_to_list
from Helper.tokens import Text, Element


class Tab:
    WIDTH, HEIGHT = 1000, 800
    HSTEP, VSTEP = 13, 18
    SCROLL_STEP = 70
    CHROME_PX = 80
    LAST_SCROLL = False  # Was not Down

    def __init__(self, bookmarks):
        self.rq = RequestHandler()
        self.nodes = None
        self.url = None
        self.document = None
        self.display_list = []
        self.font_delta = 0
        self.scroll = 0
        self.history = []
        self.future = []
        self.focus = None
        self.rules = None
        self.js = None
        self.allowed_origins = None
        self.task_runner = TaskRunner(self)
        # set bookmarks
        self.bookmarks = bookmarks
        # store browser's style sheet
        with open("Sheets/browser.css") as f:
            self.default_style_sheet = CSSParser(f.read()).parse()

    def load(self, url: str = None, payload=None):
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
            self.render()
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
            self.render()

    def draw(self, canvas):
        for cmd in self.display_list:
            if cmd.top > self.scroll + self.HEIGHT:
                continue
            if cmd.bottom < self.scroll:
                continue
            cmd.execute(self.scroll - self.CHROME_PX, canvas)
        # figure out where text entry is located
        if self.focus:
            obj = [obj for obj in tree_to_list(self.document, [])
                   if obj.node == self.focus and isinstance(obj, InputLayout)][0]
            # find coordinates of where cursor starts
            text = self.focus.attributes.get("value", "")
            x = obj.x + obj.font.measureText(text)
            y = obj.y - self.scroll + self.CHROME_PX
            # draw the cursor
            canvas.create_line(x, y, x, y + obj.height)

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
            task = Task(self.run_script, script_url, body)
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
            try:
                header, body = self.rq.request(style_url, self.url)
            except:
                # ignores style sheets that fail to download
                continue
            self.rules.extend(CSSParser(body).parse())

    def render(self):
        # redo the styling, layout, paint and draw phases
        # apply style in cascading order
        style(self.nodes, sorted(self.rules, key=cascade_priority))
        self.document = DocumentLayout(self.nodes)
        # compute the layout to be displayed in the browser
        self.document.layout(self.WIDTH, self.font_delta, self.url)
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

    def configure(self, width, height):
        self.WIDTH = width
        self.HEIGHT = height
        if self.WIDTH != 1 and self.HEIGHT != 1:
            self.reload_document()
            self.render()

    def click(self, x, y):
        # account for scrolling
        y += self.scroll
        # what elements are at the location
        objs = [obj for obj in tree_to_list(self.document, [])
                if obj.x <= x < obj.x + obj.width
                and obj.y <= y < obj.y + obj.height]
        # which object is closest to the top
        if not objs:
            return
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
                        self.scroll = loc[1]
                else:
                    # extract url and load it
                    url = resolve_url(elt.attributes["href"], self.url)
                    return self.load(url)
            elif elt.tag == "input":
                if self.js.dispatch_event("click", elt): return
                elt.attributes["value"] = ""
                self.focus = elt
                return self.render()
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

    def on_mouse_wheel(self, delta):
        if delta < 0 or delta == 0 and self.LAST_SCROLL:
            self.scrolldown()
            self.LAST_SCROLL = True
        else:
            self.scrollup()
            self.LAST_SCROLL = False

    def key_press_handler(self, key):
        match key:
            case '+':
                self.font_delta += 1
                # self.reload_document()
                self.render()
            case '-':
                if self.font_delta > -10:
                    self.font_delta -= 1
                    # self.reload_document()
                    self.render()

    def keypress(self, char):
        if self.focus:
            if self.js.dispatch_event("keydown", self.focus): return
            self.focus.attributes["value"] += char
            # self.render()
        self.document.paint(self.display_list)

    def scrolldown(self):
        max_y = self.document.height - (self.HEIGHT - self.CHROME_PX)
        self.scroll = min(self.scroll + self.SCROLL_STEP, max_y)

    def scrollup(self):
        if self.scroll > 0:
            if self.scroll - self.SCROLL_STEP < 0:
                self.scroll = 0
            else:
                self.scroll -= self.SCROLL_STEP

    def go_back(self):
        if len(self.history) > 1:
            self.future.append(self.url)
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def go_forward(self):
        if len(self.future) > 1:
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

    def raster(self, canvas):
        for cmd in self.display_list:
            cmd.execute(canvas)

    def run_script(self, url, body):
        try:
            print("Script returned: ", self.js.run(body))
        except dukpy.JSRuntimeError as e:
            print("Script", url, "crashed", e)


def cascade_priority(rule):
    selector, body = rule
    return selector.priority
