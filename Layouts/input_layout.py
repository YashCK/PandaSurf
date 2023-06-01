import skia

from Helper.font_manager import get_font, linespace
from Helper.draw import DrawRect, DrawText, DrawRRect, paint_visual_effects
from Helper.tokens import Text

INPUT_WIDTH_PX = 200


class InputLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.children = []
        self.parent = parent
        self.previous = previous
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.font = None

    def layout(self, font_delta):
        self.font = get_font(self.node, font_delta)
        # set up width
        width = self.node.style.get('width')
        self.width = to_pixel(width) if (width != "auto" and width is not None) else INPUT_WIDTH_PX
        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x
        # set up height
        height = self.node.style.get('height')
        if height == "auto" or height is None:
            self.height = linespace(self.font)
        else:
            self.height = to_pixel(height)

    def paint(self, display_list):
        cmds = []
        rect = skia.Rect.MakeLTRB(self.x, self.y, self.x + self.width, self.y + self.height)
        # draw the background
        bgcolor = self.node.style.get("background-color", "transparent")
        if bgcolor != "transparent":
            radius = float(self.node.style.get("border-radius", "0px")[:-2])
            cmds.append(DrawRRect(rect, radius, bgcolor))
        # get input element's text contents
        text = ""
        if self.node.tag == "input":
            text = self.node.attributes.get("value", "")
        elif self.node.tag == "button":
            if len(self.node.children) == 1 and \
                    isinstance(self.node.children[0], Text):
                text = self.node.children[0].text
            else:
                print("Ignoring HTML contents inside button")
                text = ""
        # draw the text
        color = self.node.style["color"]
        cmds.append(DrawText(self.x, self.y, text, self.font, color))
        cmds = paint_visual_effects(self.node, cmds, rect)
        display_list.extend(cmds)


def to_pixel(value):
    value = value[:-2]
    return int(value)
