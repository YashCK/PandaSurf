class LineLayout:
    def __init__(self, node, parent, previous, center_line=False):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        # line details
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.center_line = center_line

    def layout(self, font_size):
        # set position relative to parent's position
        self.width = self.parent.width
        self.x = self.parent.x
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
        # apply layout to words in line
        for word in self.children:
            word.layout(font_size)
        # no words on the line
        if not self.children:
            self.height = 0
            return
        # first compute the length of the line
        line_length = 0
        if self.center_line:
            first_char_pos = self.children[0].x
            last_word_info = self.children[len(self.children) - 1]
            last_char_pos = last_word_info.x + last_word_info.font.measure(last_word_info.word)
            line_length = last_char_pos - first_char_pos
        # calculate metrics to figure out the tallest word and where to put each word relative to the line
        max_ascent = max([word.font.metrics("ascent") for word in self.children])
        baseline = self.y + 1.25 * max_ascent
        passed_words = []
        for word in self.children:
            if self.center_line:
                passed = find_passed(passed_words)
                word.x = self.x + (self.width - line_length) / 2 + word.font.measure(passed)
            word.y = baseline - word.font.metrics("ascent")
            passed_words.append(word.word)
        max_descent = max([word.font.metrics("descent") for word in self.children])
        self.height = 1.25 * (max_ascent + max_descent)

    def paint(self, display_list):
        for child in self.children:
            child.paint(display_list)


def find_passed(passed):
    s = ""
    for word in passed:
        s += word + " "
    return s
