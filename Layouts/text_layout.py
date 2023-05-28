import tkinter

from draw import DrawText

FONTS = {}


class TextLayout:
    def __init__(self, node, word, parent, previous, in_bullet=False):
        self.node = node
        self.word = word
        self.children = []
        self.parent = parent
        self.previous = previous
        # position and word details
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.font = None
        self.in_bullet = in_bullet

    def layout(self, font_size):
        family = self.node.style["font-family"]
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.font = get_cached_font(family, size, weight, style)
        # compute word’s size and x position
        # stack words left to write based on computed position
        self.width = self.font.measure(self.word)
        if self.previous:
            space = self.previous.font.measure(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x
        if self.in_bullet:
            self.x += 5 + self.font.measure(" ")
        self.height = self.font.metrics("linespace")

    def paint(self, display_list):
        color = self.node.style["color"]
        display_list.append(
            DrawText(self.x, self.y, self.word, self.font, color))


def get_cached_font(family, size, weight, slant):
    key = (family, size, weight, slant)
    if key not in FONTS:
        font = tkinter.font.Font(family=family, size=size, weight=weight, slant=slant)
        FONTS[key] = font
    return FONTS[key]
