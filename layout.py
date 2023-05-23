from token import Text

FONTS = {}


class Layout:
    def __init__(self, tokens, hstep, vstep, font, width):
        self.display_list = []
        self.line = []
        self.hstep = hstep
        self.vstep = vstep
        self.cursor_x = hstep
        self.cursor_y = vstep
        self.weight = "normal"
        self.style = "roman"
        self.size = 16
        self.font = font
        self.width = width
        for tok in tokens:
            self.token(tok)

    def token(self, tok):
        weight = "normal"
        style = "roman"
        if isinstance(tok, Text):
            self.text(tok, weight, style)
        else:
            match tok.tag:
                case "i":
                    self.style = "italic"
                case "/i":
                    self.style = "roman"
                case "b":
                    self.weight = "bold"
                case "/b":
                    self.weight = "normal"
                case "small":
                    self.size -= 2
                case "/small":
                    self.size += 2
                case "big":
                    self.size += 4
                case "/big":
                    self.size -= 4
                case "br":
                    self.flush()
                case "/p":
                    self.flush()
                    self.cursor_y += self.vstep

    def text(self, tok, weight, style):
        font = self.get_font(self.size, self.weight, self.style)
        for word in tok.text.split():
            w = font.measure(word)
            if self.cursor_x + w > self.width - self.hstep:
                self.cursor_y += font.metrics("linespace") * 1.25
                self.cursor_x = self.hstep
                self.flush()
            self.line.append((self.cursor_x, word, font))
            self.cursor_x += w + font.measure(" ")

    def flush(self):
        if not self.line:
            return
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

    def get_font(self, size, weight, slant):
        key = (size, weight, slant)
        if key not in FONTS:
            self.font.configure(size=size, weight=weight, slant=slant)
            font = self.font
            FONTS[key] = font
        return FONTS[key]
