class Token:
    pass


class Text(Token):
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


class Tag(Token):
    def __init__(self, tag):
        self.tag = tag

    def __str__(self):
        return self.tag
