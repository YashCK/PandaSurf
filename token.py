class Token:
    pass


class Text(Token):
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent

    def __repr__(self):
        return repr(self.text)

    def __str__(self):
        return str(self.text)


class Element(Token):
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent

    def __repr__(self):
        return "<" + self.tag + ">"

    def __str__(self):
        return "<" + self.tag + ">"
