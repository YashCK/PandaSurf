import os
import sys
import urllib.parse

import dukpy
from requests import request

from CSSParser import CSSParser
from HTMLParser import HTMLParser
from JSContext import JSContext
from Layouts.document_layout import DocumentLayout
from Layouts.input_layout import InputLayout
from Requests.header import Header
from Requests.request import resolve_url, RequestHandler
from Helper.draw import DrawRect
from Helper.style import style, tree_to_list
from Helper.tokens import Text, Element


class Tab:
    WIDTH, HEIGHT = 1000, 800
    HSTEP, VSTEP = 13, 18
    SCROLL_STEP = 70
    CHROME_PX = 80

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
        # set bookmarks
        self.bookmarks = bookmarks
        # store browser's style sheet
        with open("Sheets/browser.css") as f:
            self.default_style_sheet = CSSParser(f.read()).parse()

    def load(self, url: str = None, body = None):
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
                headers, body = self.rq.request(data_url)
                self.url = "about:bookmarks"
                self.history.append("about:bookmarks")
            else:
                headers, body = self.rq.request(url, header_list, body)
                self.url = url
                self.history.append(url)
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
            headers, body = self.rq.request(google_url, header_list)
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
        self.draw_scrollbar(canvas)
        # figure out where text entry is located
        if self.focus:
            obj = [obj for obj in tree_to_list(self.document, [])
                   if obj.node == self.focus and \
                   isinstance(obj, InputLayout)][0]
            # find coordinates of where cursor starts
            text = self.focus.attributes.get("value", "")
            x = obj.x + obj.font.measure(text)
            y = obj.y - self.scroll + self.CHROME_PX
            # draw the cursor
            canvas.create_line(x, y, x, y + obj.height)

    def draw_scrollbar(self, canvas):
        max_y = self.document.height - self.HEIGHT
        if self.HEIGHT < max_y:
            amount_scrolled = (self.HEIGHT + self.scroll) / max_y - self.HEIGHT / max_y
            x2, y2 = self.WIDTH - 4, amount_scrolled * 0.9 * self.HEIGHT + self.HEIGHT / 10
            rect = DrawRect(self.WIDTH - self.HSTEP, amount_scrolled * 0.9 * self.HEIGHT, x2, y2, "mediumpurple3")
            rect.execute(0, canvas)

    def reload_document(self):
        # find all the scripts
        scripts = [node.attributes["src"] for node
                   in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == "script"
                   and "src" in node.attributes]
        # run all the scripts
        for script in scripts:
            header, body = self.rq.request(resolve_url(script, self.url))
            try:
                self.js.run(body)
            except dukpy.JSRuntimeError as e:
                print("Script", script, "crashed", e)
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
            try:
                header, body = self.rq.request(resolve_url(link, self.url))
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
                self.js.dispatch_event("click", elt)
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
                self.js.dispatch_event("click", elt)
                elt.attributes["value"] = ""
                self.focus = elt
                return self.render()
            elif elt.tag == "button":
                self.js.dispatch_event("click", elt)
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
        self.js.dispatch_event("submit", elt)
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
        if sys.platform.startswith('win'):
            if delta > 0:
                self.mouse_scrolldown()
            else:
                self.mouse_scrollup()
        elif sys.platform.startswith('darwin'):
            if delta < 0:
                self.mouse_scrolldown()
            else:
                self.mouse_scrollup()

    def key_press_handler(self, key):
        match key:
            case 'plus':
                self.font_delta += 1
                self.reload_document()
                self.render()
            case 'minus':
                if self.font_delta > -10:
                    self.font_delta -= 1
                    self.reload_document()
                    self.render()

    def keypress(self, char):
        if self.focus:
            self.js.dispatch_event("keydown", self.focus)
            self.focus.attributes["value"] += char
            self.render()

    def mouse_scrolldown(self):
        max_y = self.document.height - (self.HEIGHT - self.CHROME_PX)
        self.scroll = min(self.scroll + self.SCROLL_STEP / 3, max_y)

    def mouse_scrollup(self):
        if self.scroll > 0:
            if self.scroll - self.SCROLL_STEP < 0:
                self.scroll = 0
            else:
                self.scroll -= self.SCROLL_STEP / 3

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


def cascade_priority(rule):
    selector, body = rule
    return selector.priority
