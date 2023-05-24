import tkinter

from token import Text, Element

FONTS = {}


class Layout:
    LAST_LINE_START_POS = (0, 0)
    SUPERSCRIPT = False
    SUPERSCRIPT_WORDS = []
    IN_PRE_TAG = False
    HSTEP = 13
    VSTEP = 18

    def __init__(self, tree, width, font_size):
        # display and line information
        self.display_list = []
        self.line = []
        self.center_line = False
        # browser information
        self.width = width
        # cursor information
        self.cursor_x = self.HSTEP
        self.cursor_y = self.VSTEP
        # font information
        self.font_family = "Times"
        self.weight = "normal"
        self.style = "roman"
        self.size = font_size
        # go through tokens
        self.recurse(tree)
        self.flush()

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
                self.cursor_y += 1.5*self.VSTEP
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
            if self.cursor_x + w > self.width - self.HSTEP:
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
        for x, word, font in self.line:
            y = baseline - font.metrics("ascent")
            # adjust position for superscript words
            if word in self.SUPERSCRIPT_WORDS:
                y = self.cursor_y + 0.75 * max_ascent - font.metrics("ascent")
                self.SUPERSCRIPT_WORDS.remove(word)
            # center text if line should be centered
            if center_line:
                new_x = x + (self.width - line_length) / 2
                self.display_list.append((new_x, y, word, font))
            else:
                self.display_list.append((x, y, word, font))
        # update the x, y, and line fields
        self.cursor_x = self.HSTEP
        self.line = []
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent

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
            if self.cursor_x + fw_width < self.width - self.HSTEP:
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

    def print_line(self):
        print("the line: ")
        for thing in self.line:
            print(thing[1] + " ", end="")
        print("")
