from Helper.font_manager import get_font, linespace
from Helper.draw import DrawText

FONTS = {}


class TextLayout:
    def __init__(self, node, word, parent, previous, in_pre_tag=False, in_bullet=False):
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
        self.in_pre_tag = in_pre_tag
        self.in_bullet = in_bullet
        self.font_delta = None

    def layout(self, font_delta):
        self.font_delta = font_delta
        self.font = get_font(self.node, self.font_delta)
        # compute word’s size and x position
        # stack words left to write based on computed position
        self.width = self.font.measureText(self.word)
        if self.previous:
            self.x = self.previous.x + self.previous.width
            if not self.in_pre_tag:
                space = self.previous.font.measureText(" ")
                self.x += space
        else:
            self.x = self.parent.x
            if self.in_bullet:
                self.x += 10 + self.font.measureText(" ")
        self.height = linespace(self.font)

    def paint(self, display_list):
        color = self.node.style["color"]
        display_list.append(
            DrawText(self.x, self.y, self.word, self.font, color))
