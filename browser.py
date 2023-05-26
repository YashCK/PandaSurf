import os
import tkinter
import tkinter.font

from CSSParser import CSSParser
from HTMLParser import HTMLParser
from document_layout import DocumentLayout
from header import Header
from request import RequestHandler
from token import Element


class Browser:
    WIDTH, HEIGHT = 1000, 800
    HSTEP, VSTEP = 13, 18
    SCROLL_STEP = 70

    INHERITED_PROPERTIES = {
        "font-size": "16px",
        "font-style": "normal",
        "font-weight": "normal",
        "color": "black",
    }

    def __init__(self):
        # attributes
        self.window = tkinter.Tk()
        self.scroll = 0
        self.canvas = tkinter.Canvas(
            self.window,
            width=self.WIDTH,
            height=self.HEIGHT,
            bg="white",
        )
        # request handler
        self.rq = RequestHandler()
        # content attributes
        self.current_url = None
        self.document = None
        self.display_list = []
        self.nodes = None
        self.font_size = 16
        # set up canvas
        self.canvas.pack(expand=True, fill=tkinter.BOTH)
        # bind keys
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<MouseWheel>", self.on_mouse_wheel)
        self.window.bind("<Button-4>", self.mouse_scrollup)
        self.window.bind("<Button-5>", self.mouse_scrolldown)
        self.window.bind("<Configure>", self.configure)
        self.window.bind("<KeyPress>", self.key_press_handler)
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
            self.current_url = url
            # Begin layout tree
            self.nodes = HTMLParser(body).parse()
            self.redraw()
        except FileNotFoundError:
            print("The path to the file you entered does not exist.")
        except ValueError:
            print("The path entered was likely not in the correct format.")

    def draw(self, redraw=False):
        self.canvas.delete("all")
        for cmd in self.display_list:
            if cmd.top > self.scroll + self.HEIGHT: continue
            if cmd.bottom < self.scroll: continue
            if redraw:
                cmd.execute(self.scroll, self.canvas, self.font_size)
            else:
                cmd.execute(self.scroll, self.canvas)

    def redraw(self, adjust_text_size=False):
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
                header, body = self.rq.request(resolve_url(link, self.current_url))
            except:
                # ignores style sheets that fail to download
                continue
            rules.extend(CSSParser(body).parse())
        # apply style in cascading order
        self.style(self.nodes, sorted(rules, key=cascade_priority))
        # compute the layout to be displayed in the browser
        self.document.layout(self.WIDTH, self.HEIGHT, self.font_size)
        self.display_list = []
        self.document.paint(self.display_list)
        self.draw(adjust_text_size)

    def key_press_handler(self, e):
        match e.keysym:
            case 'plus':
                self.font_size += 1
                self.redraw(True)
            case 'minus':
                if self.font_size > 1:
                    self.font_size -= 1
                    self.redraw(True)

    def configure(self, e):
        self.WIDTH = e.width
        self.HEIGHT = e.height
        if self.WIDTH != 1 and self.HEIGHT != 1:
            self.redraw()

    def on_mouse_wheel(self, e):
        if sys.platform.startswith('win'):
            if e.delta > 0:
                self.mouse_scrolldown(e)
            else:
                self.mouse_scrollup(e)
        elif sys.platform.startswith('darwin'):
            if e.delta < 0:
                self.mouse_scrolldown(e)
            else:
                self.mouse_scrollup(e)

    def mouse_scrolldown(self, e):
        max_y = self.document.height - self.HEIGHT
        self.scroll = min(self.scroll + self.SCROLL_STEP / 3, max_y)
        self.draw()

    def mouse_scrollup(self, e):
        if self.scroll > 0:
            if self.scroll - self.SCROLL_STEP < 0:
                self.scroll = 0
            else:
                self.scroll -= self.SCROLL_STEP / 3
            self.draw()

    def scrolldown(self, e):
        max_y = self.document.height - self.HEIGHT
        self.scroll = min(self.scroll + self.SCROLL_STEP, max_y)
        self.draw()

    def scrollup(self, e):
        if self.scroll > 0:
            if self.scroll - self.SCROLL_STEP < 0:
                self.scroll = 0
            else:
                self.scroll -= self.SCROLL_STEP
            self.draw()

    def style(self, node, rules):
        node.style = {}
        #
        for prop, default_value in self.INHERITED_PROPERTIES.items():
            if node.parent:
                node.style[prop] = node.parent.style[prop]
            else:
                node.style[prop] = default_value
        # loop over all elements and all rules in order to add the property/value pairs
        # to the element's style information
        for selector, body in rules:
            if not selector.matches(node): continue
            for prop, value in body.items():
                computed_value = self.compute_style(node, prop, value)
                if not computed_value: continue
                node.style[prop] = computed_value
        # parse style attribute to fill in the style filed
        if isinstance(node, Element) and "style" in node.attributes:
            pairs = CSSParser(node.attributes["style"]).body()
            for prop, value in pairs.items():
                node.style[prop] = value
        #
        for child in node.children:
            self.style(child, rules)

    def compute_style(self, node, prop, value):
        # browsers resolve percentages to absolute pixel units
        # before they are storied in style or are inherited
        if prop == "font-size":
            if value.endswith("px"):
                return value
            elif value.endswith("%"):
                # percentage for the root html element is relative to default font size
                if node.parent:
                    parent_font_size = node.parent.style["font-size"]
                else:
                    parent_font_size = self.INHERITED_PROPERTIES["font-size"]
                node_pct = float(value[:-1]) / 100
                parent_px = float(parent_font_size[:-2])
                return str(node_pct * parent_px) + "px"
            else:
                return None
        else:
            return value


def resolve_url(url, current):
    # convert host-relative/path-relative URLs to full URLs
    if "://" in url:
        return url
    elif url.startswith("/"):
        scheme, hostpath = current.split("://", 1)
        host, oldpath = hostpath.split("/", 1)
        return scheme + "://" + host + url
    else:
        directory, _ = current.rsplit("/", 1)
        while url.startswith("../"):
            url = url[3:]
            if directory.count("/") == 2: continue
            directory, _ = directory.rsplit("/", 1)
        return directory + "/" + url


def tree_to_list(tree, array):
    array.append(tree)
    for child in tree.children:
        tree_to_list(child, array)
    return array


def cascade_priority(rule):
    selector, body = rule
    return selector.priority


# Main method
if __name__ == "__main__":
    import sys

    Browser().load(sys.argv[1])
    tkinter.mainloop()
