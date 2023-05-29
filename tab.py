import os
import sys

from CSSParser import CSSParser
from HTMLParser import HTMLParser
from Layouts.document_layout import DocumentLayout
from Requests.header import Header
from Requests.request import resolve_url, RequestHandler
from draw import DrawRect
from style import style
from token import Text, Element


class Tab:

    WIDTH, HEIGHT = 1000, 800
    HSTEP, VSTEP = 13, 18
    SCROLL_STEP = 70

    def __init__(self):
        self.rq = RequestHandler()
        self.nodes = None
        self.url = None
        self.document = None
        self.display_list = []
        self.font_delta = 0
        self.scroll = 0
        # store browser's style sheet
        with open("browser.css") as f:
            self.default_style_sheet = CSSParser(f.read()).parse()

    def load(self, url: str = None):
        try:
            if url is None:
                url = "file://" + os.getcwd() + '/panda_surf_df.txt'
            user_agent_header = Header("User-Agent", "This is the PandaSurf Browser.")
            accept_encoding_header = Header("Accept-Encoding", "gzip")
            header_list = [user_agent_header, accept_encoding_header]
            headers, body = self.rq.request(url, header_list)
            self.url = url
            self.nodes = HTMLParser(body).parse()
            # self.form_doc_layout()
            # if os.path.getsize("external.css") != 0:
            #     with open("external.css") as f:
            #         self.default_style_sheet = CSSParser(f.read()).parse()
            self.reload()
        except FileNotFoundError:
            print("The path to the file you entered does not exist.")
        except ValueError:
            print("The path entered was likely not in the correct format.")

    def draw(self, canvas):
        for cmd in self.display_list:
            if cmd.top > self.scroll + self.HEIGHT:
                continue
            if cmd.bottom < self.scroll:
                continue
            cmd.execute(self.scroll, canvas)
        self.draw_scrollbar(canvas)

    def draw_scrollbar(self, canvas):
        max_y = self.document.height - self.HEIGHT
        if self.HEIGHT < max_y:
            amount_scrolled = (self.HEIGHT + self.scroll) / max_y - self.HEIGHT / max_y
            x2, y2 = self.WIDTH - 4, amount_scrolled * 0.9 * self.HEIGHT + self.HEIGHT / 10
            rect = DrawRect(self.WIDTH - self.HSTEP, amount_scrolled * 0.9 * self.HEIGHT, x2, y2, "mediumpurple3")
            rect.execute(0, canvas)

    def form_doc_layout(self):
        self.document = DocumentLayout(self.nodes)
        rules = self.default_style_sheet.copy()
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
            rules.extend(CSSParser(body).parse())
        # apply style in cascading order
        style(self.nodes, sorted(rules, key=cascade_priority))
        # compute the layout to be displayed in the browser
        self.document.layout(self.WIDTH, self.font_delta, self.url)

    def reload(self):
        self.form_doc_layout()
        self.display_list = []
        self.document.paint(self.display_list)

    def configure(self, width, height):
        self.WIDTH = width
        self.HEIGHT = height
        if self.WIDTH != 1 and self.HEIGHT != 1:
            self.reload()

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
                # extract url and load it
                url = resolve_url(elt.attributes["href"], self.url)
                return self.load(url)
            elt = elt.parent

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
                self.reload()
            case 'minus':
                if self.font_delta > -10:
                    self.font_delta -= 1
                    self.reload()

    def mouse_scrolldown(self):
        max_y = self.document.height - self.HEIGHT
        self.scroll = min(self.scroll + self.SCROLL_STEP / 3, max_y)

    def mouse_scrollup(self):
        if self.scroll > 0:
            if self.scroll - self.SCROLL_STEP < 0:
                self.scroll = 0
            else:
                self.scroll -= self.SCROLL_STEP / 3

    def scrolldown(self):
        max_y = self.document.height - self.HEIGHT
        self.scroll = min(self.scroll + self.SCROLL_STEP, max_y)

    def scrollup(self):
        if self.scroll > 0:
            if self.scroll - self.SCROLL_STEP < 0:
                self.scroll = 0
            else:
                self.scroll -= self.SCROLL_STEP


def cascade_priority(rule):
    selector, body = rule
    return selector.priority


def tree_to_list(tree, array):
    array.append(tree)
    for child in tree.children:
        tree_to_list(child, array)
    return array
