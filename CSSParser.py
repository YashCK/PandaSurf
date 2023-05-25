from selector import TagSelector, DescendantSelector


class CSSParser:
    def __init__(self, s):
        # text
        self.s = s
        # parser's current position in text
        self.i = 0

    def whitespace(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    def word(self):
        start = self.i
        # increments i through all the word characters
        # stores where it started and the substring it extracted
        while self.i < len(self.s):
            if self.s[self.i].isalnum() or self.s[self.i] in "#-.%":
                self.i += 1
            else:
                break
        # check that i advanced though at least one character
        # otherwise it did not point at a word
        assert self.i > start
        return self.s[start:self.i]

    def literal(self, literal):
        # check if a character is literally something
        assert self.i < len(self.s) and self.s[self.i] == literal
        self.i += 1

    def pair(self):
        prop = self.word()
        self.whitespace()
        self.literal(":")
        self.whitespace()
        val = self.word()
        return prop.lower(), val

    def body(self):
        # parse sequences by calling the parsing functions in a loop
        pairs = {}
        while self.i < len(self.s) and self.s[self.i] != "}":
            try:
                prop, val = self.pair()
                pairs[prop.lower()] = val
                self.whitespace()
                self.literal(";")
                self.whitespace()
            except AssertionError:
                # when we cannot correctly parse a property, value pair
                # skip to the next semicolon/end of string
                why = self.ignore_until([";"])
                if why == ";":
                    self.literal(";")
                    self.whitespace()
                else:
                    break
        return pairs

    def ignore_until(self, chars):
        # stops at any one of a set of characters and returns it
        # returns None if at end of file
        while self.i < len(self.s):
            if self.s[self.i] in chars:
                return self.s[self.i]
            else:
                self.i += 1

    def selector(self):
        # create selector objects
        out = TagSelector(self.word().lower())
        self.whitespace()
        while self.i < len(self.s) and self.s[self.i] != "{":
            tag = self.word()
            descendant = TagSelector(tag.lower())
            out = DescendantSelector(out, descendant)
            self.whitespace()
        return out

    def parse(self):
        # css files are a sequence of selectors and blocks
        rules = []
        while self.i < len(self.s):
            try:
                self.whitespace()
                selector = self.selector()
                self.literal("{")
                self.whitespace()
                body = self.body()
                self.literal("}")
                rules.append((selector, body))
            except AssertionError:
                # if there is a parse error skip the whole rule
                why = self.ignore_until(["}"])
                if why == "}":
                    self.literal("}")
                    self.whitespace()
                else:
                    break
        return rules
