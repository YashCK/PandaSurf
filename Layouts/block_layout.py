# Web pages are constructed out of blocks (headings, paragraphs, and menus) that are stacked
# vertically one after another
import tkinter

from Layouts.line_layout import LineLayout
from Layouts.text_layout import TextLayout
from draw import DrawText, DrawRect
from token import Text, Element

FONTS = {}


class BlockLayout:
    HSTEP = 13
    VSTEP = 18

    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        # relative positions of x and y
        self.cursor_x = 0
        self.cursor_y = 0
        # blocks actual position
        self.x = None
        self.y = None
        # size of block
        self.width = None
        self.height = None
        # font information
        self.font_family = "Didot"
        self.weight = "normal"
        self.style = "roman"
        self.size = 16
        # display and line information
        self.display_list = []
        self.line = []
        self.center_line = False
        self.create_bullet = False
        self.style_sheet = []
        # word info
        self.previous_word = None
        self.in_bullet = False

    def layout_intermediate(self):
        # reads from HTML to tree and writes to Layout tree
        previous = None
        for child in self.node.children:
            inter = BlockLayout(child, self, previous)
            self.children.append(inter)
            previous = inter

    def layout(self, font_size):
        # set up width
        width = self.node.style.get('width')
        self.width = to_pixel(width) if (width != "auto" and width is not None) else self.parent.width
        # start attributes relative to parent attributes
        self.x = self.parent.x
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
        # layout block depending on its type
        mode = layout_mode(self.node)
        if mode == "block":
            self.layout_intermediate()
        else:
            self.new_line()
            self.recurse(self.node)
        # recursively call layout on each child
        for child in self.children:
            child.layout(font_size)
            # self.style_sheet += child.style_sheet
        height = self.node.style.get('height')
        if height == "auto" or height is None:
            # height of the block should be the sum of its children heights
            self.height = sum([child.height for child in self.children])
        else:
            # set height to dimension specified by container
            self.height = to_pixel(height)

    def text(self, node, pre_tag):
        def add_to_line(the_word, word_width):
            # self.line.append((self.cursor_x, the_word, font, color))
            line = self.children[-1]
            text = TextLayout(node, word, line, self.previous_word)
            line.children.append(text)
            self.previous_word = text
            self.cursor_x += word_width
            if not to_bool(pre_tag):
                self.cursor_x += font.measure(" ")
        # apply centering to the line
        if self.center_line:
            self.new_line(center_line=True)
            self.center_line = False
        # style properties and the words list t use
        font = get_font(node)
        words = construct_words(node, to_bool(pre_tag))
        # find positions for all the words in the list
        for word in words:
            # add words to lines
            w = font.measure(word)
            if self.cursor_x + w > self.width:
                first_word, second_word = self.hyphenate_word(word, font)
                if first_word == "":  # no need to hyphenate
                    self.new_line(self.center_line)
                else:
                    # add the first word to this line, go to next line, add second word to next line
                    add_to_line(first_word, font.measure(first_word))
                    self.new_line(self.center_line)
                    add_to_line(second_word, font.measure(second_word))
                    continue
            elif to_bool(pre_tag) and word == "\n":
                self.new_line()
            # add to end of the line
            add_to_line(word, w)

    def new_line(self, center_line=False):
        self.previous_word = None
        self.cursor_x = 0
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line, center_line)
        self.children.append(new_line)

    def recurse(self, node):
        if isinstance(node, Text):
            if to_bool(node.style["show-contents"]):
                self.text(node, node.style["in-pre-tag"])
        else:
            self.handle_tags(node)
            for child in node.children:
                self.recurse(child)

    def handle_tags(self, node):
        if node.tag == "br" or node.tag == "p":
            self.new_line()
        if node.tag == "h1":
            if ("class", "title") in node.attributes.items():
                self.center_line = True
        if node.tag == "nav":
            if ("id", "toc") in node.attributes.items():
                toc = Text("Table of Contents", None)
                toc.style = {"font-weight": "bold",
                             "color": "black",
                             "font-family": "Didot",
                             "font-style": "normal",
                             "font-size": "150%"}
                self.text(toc, "False")
                self.new_line()
        if node.tag == "li":
            self.in_bullet = True
        # if node.tag == "link":
        #     if ("rel", "stylesheet") in node.attributes.items():
        #         self.style_sheet.append(node.attributes["href"])

    def flush(self, center_line=False):
        if not self.line:
            return
        # first compute the length of the line
        line_length = 0
        if center_line:
            first_char_pos = self.line[0][0]
            last_word_info = self.line[len(self.line) - 1]
            last_char_pos = last_word_info[0] + last_word_info[2].measure(last_word_info[1])
            line_length = last_char_pos - first_char_pos
        # compute the metrics to figure out where the line should be
        metrics = [font.metrics() for x, word, font, color in self.line]
        # figure out the tallest word
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        # place each word relative to the line, then add to display list
        for x, word, font, color in self.line:
            y = baseline - font.metrics("ascent")
            if center_line:
                new_x = x + (self.width - line_length) / 2
                self.display_list.append((new_x, y, word, font, color))
            else:
                self.display_list.append((x, y, word, font, color))
        self.cursor_x = self.x
        self.line = []
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent

    def paint(self, display_list):
        # browser can consult element for styling information
        bgcolor = self.node.style.get("background-color", "transparent")
        # fix for when it encounters rgba and crashes
        if bgcolor == "rgba" or bgcolor == "var":
            bgcolor = "transparent"
        # draw background colors
        if bgcolor != "transparent":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, bgcolor)
            display_list.append(rect)
        # links bar
        if isinstance(self.node, Element) and self.node.tag == "nav":
            if ("class", "links") in self.node.attributes.items():
                x2, y2 = self.x + self.width, self.y + self.height
                rect = DrawRect(self.x, self.y, x2, y2, "light grey")
                display_list.append(rect)
        # bullet points
        if isinstance(self.node, Element) and self.node.tag == "li":
            x2, y2 = self.x + 5, self.y + self.height / 2 + 5
            rect = DrawRect(self.x, self.y + self.height / 2, x2, y2, "black")
            display_list.append(rect)
            self.create_bullet = True
        # apply the following for the node's children
        for child in self.children:
            child.paint(display_list)

    def hyphenate_word(self, word, word_font):
        # find soft hyphen positions
        hyphen_positions = []
        for i, char in enumerate(word):
            if char == '\N{soft hyphen}':
                hyphen_positions.append(i)
        # determine which hyphen position to use
        first_part = ""
        second_part = word
        for pos in hyphen_positions:
            first_word = word[:pos] + '-'
            fw_width = word_font.measure(first_word)
            if self.cursor_x + fw_width < self.width:
                first_part = first_word
                second_part = word[pos + 1:]
            else:
                break
        return first_part, second_part

    def print_line(self):
        print("the line: ")
        for thing in self.line:
            print(thing[1] + " ", end="")
        print("")


def layout_mode(node):
    if isinstance(node, Text):
        return "inline"
    elif node.children:
        for child in node.children:
            if isinstance(child, Element) and child.style.get("display") == "block":
                return "block"
        return "inline"
    else:
        return "block"


def construct_words(tok, in_pre_tag):
    if in_pre_tag:
        # to not ignore whitespace and line breaks, we construct words character by character
        words = []
        w = ''
        for c in tok.text:
            if c.isspace():
                if w:
                    words.append(w)
                w = ''
                words.append(c)
            else:
                w += c
        if w:
            words.append(w)
        return words
    else:
        return tok.text.split()


def to_bool(in_pre_tag):
    return in_pre_tag == "True"


def to_pixel(value):
    value = value[:-2]
    return int(value)


def get_font(node):
    family = node.style["font-family"]
    weight = node.style["font-weight"]
    style = node.style["font-style"]
    # In case of var
    if weight == "var":
        weight = "normal"
    # translate CSS normal to Tk roman
    if style == "normal":
        style = "roman"
    # manage inherited properties
    # find_inherited_property(node, "color", "black")
    # find_inherited_property(node, "font-family", "Didot")
    # find_inherited_property(node, "font-size", 16)
    # find_inherited_property(node, "font-style", "roman")
    # find_inherited_property(node, "font-weight", "normal")
    # convert CSS pixels to Tk points
    size = int(float(node.style["font-size"][:-2]) * .75)
    return get_cached_font(family, size, weight, style)


def find_inherited_property(node, prop, default_val):
    if node.style[prop] == "inherit":
        new_prop = default_val
        while node.parent:
            node_prop = node.style["color"]
            if node_prop != "inherit":
                new_prop = node_prop
                break
            node = node.parent
        node.style[prop] = new_prop


def get_cached_font(family, size, weight, slant):
    key = (family, size, weight, slant)
    if key not in FONTS:
        font = tkinter.font.Font(family=family, size=size, weight=weight, slant=slant)
        FONTS[key] = font
    return FONTS[key]
