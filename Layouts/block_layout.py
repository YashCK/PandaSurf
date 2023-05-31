# Web pages are constructed out of blocks (headings, paragraphs, and menus) that are stacked
# vertically one after another
from Layouts.font_manager import get_font
from Layouts.input_layout import InputLayout
from Layouts.line_layout import LineLayout
from Layouts.text_layout import TextLayout
from draw import DrawRect
from tokens import Text, Element

FONTS = {}
INPUT_WIDTH_PX = 200


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
        self.center_line = False
        self.font_delta = None
        self.previous_word = None

    def layout_intermediate(self):
        # reads from HTML to tree and writes to Layout tree
        previous = None
        for child in self.node.children:
            inter = BlockLayout(child, self, previous)
            self.children.append(inter)
            previous = inter

    def layout(self, font_delta):
        self.font_delta = font_delta
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
            child.layout(font_delta)
            # self.style_sheet += child.style_sheet
        height = self.node.style.get('height')
        if height == "auto" or height is None:
            # height of the block should be the sum of its children heights
            self.height = sum([child.height for child in self.children])
        else:
            # set height to dimension specified by container
            self.height = to_pixel(height)

    def text(self, node):
        def add_to_line(the_word, word_width):
            line = self.children[-1]
            text = TextLayout(node, the_word, line, self.previous_word, pre_tag, node.style["in-bullet"])
            line.children.append(text)
            self.previous_word = text
            self.cursor_x += word_width
            if not pre_tag:
                self.cursor_x += font.measure(" ")

        # calculate pre-tag
        pre_tag = to_bool(node.style["in-pre-tag"])
        # apply centering to the line
        if self.center_line:
            self.new_line(center_line=True)
            self.center_line = False
        # style properties and the words list t use
        font = get_font(node, self.font_delta)
        words = construct_words(node, pre_tag)
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
            elif pre_tag and word == "\n":
                self.new_line()
            # add to end of the line
            add_to_line(word, w)

    def new_line(self, center_line=False):
        self.previous_word = None
        self.cursor_x = self.HSTEP
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line, center_line)
        self.children.append(new_line)

    def input(self, node):
        w = INPUT_WIDTH_PX
        if self.cursor_x + w > self.width:
            self.new_line()
        line = self.children[-1]
        input_area = InputLayout(node, line, self.previous_word)
        line.children.append(input_area)
        self.previous_word = input_area
        font = get_font(node)
        self.cursor_x += w + font.measure(" ")

    def recurse(self, node):
        if isinstance(node, Text):
            if to_bool(node.style["show-contents"]):
                self.text(node)
        else:
            self.handle_tags(node)
            for child in node.children:
                self.recurse(child)

    def handle_tags(self, node):
        if node.tag == "br" or node.tag == "p":
            self.new_line()
        elif node.tag == "h1":
            if ("class", "title") in node.attributes.items():
                self.center_line = True
        elif node.tag == "nav":
            if ("id", "toc") in node.attributes.items():
                toc = Text("Table of Contents", None)
                toc.style = {"font-weight": "bold",
                             "color": "black",
                             "font-family": "Didot",
                             "font-style": "normal",
                             "font-size": "150%"}
                self.text(toc)
                self.new_line()
        elif node.tag == "input" or node.tag == "button":
            self.input(node)
        # if node.tag == "link":
        #     if ("rel", "stylesheet") in node.attributes.items():
        #         self.style_sheet.append(node.attributes["href"])

    def paint(self, display_list):
        # browser can consult element for styling information
        bgcolor = self.node.style.get("background-color", "transparent")
        # fix for when it encounters rgba and crashes
        if bgcolor == "rgba" or bgcolor == "var":
            bgcolor = "transparent"
        # draw background as long as its not an input layout wrapped in a block layout
        is_atomic = not isinstance(self.node, Text) and \
                    (self.node.tag == "input" or self.node.tag == "button")
        if not is_atomic:
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
            x2, y2 = self.x + 10, self.y + self.height / 2 + 5
            rect = DrawRect(self.x + 5, self.y + self.height / 2, x2, y2, "black")
            display_list.append(rect)
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
    elif node.tag == "input":
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
