# Web pages are constructed out of blocks (headings, paragraphs, and menus) that are stacked
# vertically one after another
import tkinter

from draw import DrawText, DrawRect
from token import Text, Element

FONTS = {}


class BlockLayout:
    LAST_LINE_START_POS = (0, 0)
    SUPERSCRIPT = False
    SUPERSCRIPT_WORDS = []
    IN_PRE_TAG = False
    HSTEP = 13
    VSTEP = 18

    BLOCK_ELEMENTS = [
        "html", "body", "article", "section", "nav", "aside",
        "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
        "footer", "address", "p", "hr", "pre", "blockquote",
        "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
        "figcaption", "main", "div", "table", "form", "fieldset",
        "legend", "details", "summary"
    ]

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

    def layout_intermediate(self):
        # reads from HTML to tree and writes to Layout tree
        previous = None
        for child in self.node.children:
            inter = BlockLayout(child, self, previous)
            self.children.append(inter)
            previous = inter

    def layout(self, font_size):
        # start attributes relative to parent attributes
        self.width = self.parent.width
        self.x = self.parent.x
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
        # layout block depending on its type
        mode = self.layout_mode(self.node)
        if mode == "block":
            self.layout_intermediate()
        else:
            # display and line information
            self.display_list = []
            self.line = []
            self.center_line = False
            # cursor information
            self.cursor_x = 0
            self.cursor_y = 0
            # font information
            self.font_family = "Didot"
            self.weight = "normal"
            self.style = "roman"
            self.size = font_size
            # go through the tree
            self.recurse(self.node)
            self.flush()
        # recursively call layout on each child
        for child in self.children:
            child.layout(font_size)
        # height of the block should be the sum of its children heights
        if mode == "block":
            self.height = sum([child.height for child in self.children])
        else:
            # in the case the block is simply a text block
            self.height = self.cursor_y

    def text(self, tok: Text):
        def adjust_line():
            self.cursor_y += font.metrics("linespace") * 1.25
            self.cursor_x = self.HSTEP
            self.flush(self.center_line)

        font = self.get_font(self.size, self.weight, self.style)
        words = self.construct_words(tok)

        for word in words:
            # check if word should be superscript
            if self.SUPERSCRIPT:
                self.SUPERSCRIPT_WORDS.append(word)
            # Add words to line
            w = font.measure(word)
            if self.cursor_x + w > self.width:
                first_word, second_word = self.hyphenate_word(word, font)
                if first_word == "" or (self.IN_PRE_TAG and word == "\n"):
                    # no need to hyphenate
                    adjust_line()
                else:
                    # add the first word to this line
                    self.line.append((self.cursor_x, first_word, font))
                    self.cursor_x += font.measure(first_word) + font.measure(" ")
                    adjust_line()
                    # add the second word to the next line
                    sw = font.measure(second_word)
                    self.line.append((self.cursor_x, second_word, font))
                    self.cursor_x += sw + font.measure(" ")
                    continue
            self.line.append((self.cursor_x, word, font))
            self.cursor_x += w
            if not self.IN_PRE_TAG:
                self.cursor_x += font.measure(" ")

    def recurse(self, tree):
        if isinstance(tree, Text):
            self.text(tree)
        else:
            self.open_tag(tree)
            for child in tree.children:
                self.recurse(child)
            self.close_tag(tree)

    def open_tag(self, elem: Element):
        match elem.tag:
            case "i":
                self.style = "italic"
            case "b":
                self.weight = "bold"
            case "small":
                self.size -= 2
            case "big":
                self.size += 4
            case "p":
                self.flush()
                self.cursor_y += self.VSTEP
            case "br":
                self.flush()
            case "h1":
                if ("class", "title") in elem.attributes.items():
                    self.center_line = True
            case "title":
                self.LAST_LINE_START_POS = (self.cursor_x, self.cursor_y)
            case "sup":
                self.size = int(self.size / 2)
                self.SUPERSCRIPT = True
            case "sub":
                self.size = int(self.size / 2)
            case "pre":
                self.font_family = "Courier New"
                self.IN_PRE_TAG = True

    def close_tag(self, elem: Element):
        match elem.tag:
            case "i":
                self.style = "roman"
            case "b":
                self.weight = "normal"
            case "small":
                self.size += 2
            case "big":
                self.size -= 4
            case "p":
                self.flush()
                self.cursor_y += 1.5 * self.VSTEP
            case "h1":
                if self.center_line:
                    self.flush(center_line=True)
                    self.center_line = False
            case "title":
                self.line = []
                self.cursor_x = self.LAST_LINE_START_POS[0]
                self.cursor_y = self.LAST_LINE_START_POS[1]
            case "sup" | "sub":
                self.size *= 2
                self.SUPERSCRIPT = False
            case "pre":
                self.font_family = "Times"
                self.IN_PRE_TAG = False

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
        metrics = [font.metrics() for x, word, font in self.line]
        # figure out the tallest word
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        # increase the position of the text if it is superscript text
        if self.SUPERSCRIPT:
            baseline = self.cursor_y + 1.75 * max_ascent
        # place each word relative to the line
        # then add to display list
        for rel_x, word, font in self.line:
            x = self.x + rel_x
            y = self.y + baseline - font.metrics("ascent")
            # adjust position for superscript words
            if word in self.SUPERSCRIPT_WORDS:
                y = self.y + self.cursor_y + 0.75 * max_ascent - font.metrics("ascent")
                self.SUPERSCRIPT_WORDS.remove(word)
            # center text if line should be centered
            if center_line:
                new_x = x + (self.width - line_length) / 2
                self.display_list.append((new_x, y, word, font))
            else:
                self.display_list.append((x, y, word, font))
        # update the x, y, and line fields
        self.cursor_x = 0
        self.line = []
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent

    def paint(self, display_list):
        # add DrawRect commands for backgrounds
        if isinstance(self.node, Element) and self.node.tag == "pre":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, "gray")
            display_list.append(rect)
        # add DrawText for text objects
        if self.layout_mode(self.node) == "inline":
            for x, y, word, font in self.display_list:
                display_list.append(DrawText(x, y, word, font))
        # apply the following for the node's children
        for child in self.children:
            child.paint(display_list)

    def construct_words(self, tok: Text):
        if self.IN_PRE_TAG:
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

    def get_font(self, size, weight, slant):
        key = (size, weight, slant)
        if key not in FONTS:
            font = tkinter.font.Font(family=self.font_family, size=size, weight=weight, slant=slant)
            FONTS[key] = font
        return FONTS[key]

    def layout_mode(self, node):
        if isinstance(node, Text):
            return "inline"
        elif node.children:
            if any([isinstance(child, Element) and child.tag in
                    self.BLOCK_ELEMENTS for child in node.children]):
                return "block"
            else:
                return "inline"
        else:
            return "block"

    def print_line(self):
        print("the line: ")
        for thing in self.line:
            print(thing[1] + " ", end="")
        print("")
