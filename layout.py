import tkinter

from token import Text

FONTS = {}


class Layout:
    def __init__(self, tree, hstep, vstep, font, width):
        # display and line information
        self.display_list = []
        self.line = []
        self.center_line = False
        # browser information
        self.hstep = hstep
        self.vstep = vstep
        self.width = width
        # cursor information
        self.cursor_x = hstep
        self.cursor_y = vstep
        # font information
        self.font_family = "Times"
        self.weight = "normal"
        self.style = "roman"
        self.size = 16
        # go through tokens
        self.recurse(tree)
        self.flush()

    def recurse(self, tree):
        if isinstance(tree, Text):
            self.text(tree)
        else:
            self.open_tag(tree.tag)
            for child in tree.children:
                self.recurse(child)
            self.close_tag(tree.tag)

    def open_tag(self, tag):
        match tag:
            case "i":
                self.style = "italic"
            case "b":
                self.weight = "bold"
                print("it should be bolding")
            case "small":
                self.size -= 2
            case "big":
                self.size += 4
            case "br":
                self.flush()
            case "h1 class=\"title\"":
                self.center_line = True

    def close_tag(self, tag):
        match tag:
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
                self.cursor_y += self.vstep
            case "h1":
                self.center_line = False

    def text(self, tok):
        font = self.get_font(self.size, self.weight, self.style)
        print("this is the weight: ", self.weight)
        for word in tok.text.split():
            w = font.measure(word)
            if self.cursor_x + w > self.width - self.hstep:
                self.cursor_y += font.metrics("linespace") * 1.25
                self.cursor_x = self.hstep
                self.flush(self.center_line)
            self.line.append((self.cursor_x, word, font))
            if self.center_line:
                pass
            self.cursor_x += w + font.measure(" ")

    def flush(self, center_line=False):
        if not self.line:
            return
        # If we want to center line, first compute the length of the line
        line_length = 0
        # compute the metrics to figure out where the line should be
        metrics = [font.metrics() for x, word, font in self.line]
        # figure out the tallest word
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        # place each word relative to the line
        # then add to display list
        for x, word, font in self.line:
            y = baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))
        # update the x, y, and line fields
        self.cursor_x = self.hstep
        self.line = []
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent

    def centerline(self):
        # first_char_pos = self.line[0][0]
        # last_word_info = self.line[len(self.line) - 1]
        # last_char_pos = last_word_info[0] + last_word_info[2].measure(last_word_info[1])
        # line_length = last_char_pos - first_char_pos
        # new_x = x + (self.width - line_length) / 2
        # print("width: ", self.width)
        # print("length: ", line_length)
        # print("initial x: ", x)
        # print("new x: ", new_x)
        # self.display_list.append((new_x, y, word, font))
        pass

    def get_font(self, size, weight, slant):
        key = (size, weight, slant)
        if key not in FONTS:
            font = tkinter.font.Font(family=self.font_family, size=size, weight=weight, slant=slant)
            FONTS[key] = font
        return FONTS[key]
