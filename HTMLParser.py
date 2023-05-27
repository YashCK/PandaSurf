from token import Text, Element


class HTMLParser:
    SELF_CLOSING_TAGS = [
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    ]

    HEAD_TAGS = [
        "base", "basefont", "bgsound", "noscript",
        "link", "meta", "title", "style", "script",
    ]

    def __init__(self, body):
        self.body = body
        self.unfinished = []

    def parse(self):
        last_ten_chars = "          "
        text = ""
        in_tag = False
        in_quotes = False
        in_script = False
        read_text = True
        last_known_tag = False
        for c in self.body:
            last_ten_chars = last_ten_chars[-9:] + c
            if c == "\"":
                in_quotes = not in_quotes
            # check for comments
            if last_ten_chars[-4:] == "<!--":
                read_text = False
                in_tag = last_known_tag
                last_ten_chars = "          "
                text = text[:-2]
            elif last_ten_chars[-3:] == "-->":
                read_text = True
                continue
            # proceed if not in a comment
            if read_text:
                if in_script:
                    if last_ten_chars[-9:] == "</script>":
                        text = text[:-8]
                        # add content inside of script tags as text
                        if text:
                            self.add_text(text)
                        text = ""
                        # close of the tag
                        last_known_tag = False
                        in_tag = False
                        in_script = False
                        self.add_tag("/script")
                    else:
                        text += c
                else:
                    # check for tags
                    if c == "<":
                        last_known_tag = in_tag
                        in_tag = True
                        if text:
                            self.add_text(text)
                        text = ""
                    elif c == ">" and not in_quotes:
                        last_known_tag = in_tag
                        in_tag = False
                        self.add_tag(text)
                        in_script = check_in_script(text)
                        text = ""
                    else:
                        text += c
                        if text[-4:] == '&lt;':
                            text = text[:-4] + '<'
                        elif text[-4:] == '&gt;':
                            text = text[:-4] + '>'
                        elif text[-4:] == '&shy':
                            text = text[:-4] + '\N{soft hyphen}'
                        elif text[-5:] == '&amp;':
                            text = text[:-5] + '&'
                        elif text[-6:] == '&quot;':
                            text = text[:-6] + '\"'
        if not in_tag and text:
            self.add_text(text)
        return self.finish()

    # add a new node as the child of the last unfinished node
    def add_text(self, text):
        # ignore whitespace
        if text.isspace():
            return
        self.implicit_tags()
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    def add_tag(self, tag):
        tag, attributes = get_attributes(tag)
        # ignore doctype declarations and comments
        if tag.startswith("!"):
            return
        self.implicit_tags(tag)
        # Important Tags
        if tag.startswith("/"):
            if len(self.unfinished) == 1:
                return
            # close tag removes the last unfinished node and adds the  next unfinished node in the list
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        elif tag in self.SELF_CLOSING_TAGS:
            # auto close any tags that are part of this list
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)
        else:
            # open tag adds an unfinished node to the end of the list
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)

    # turn incomplete tree to a complete tree by finishing unfinished nodes
    def finish(self):
        if len(self.unfinished) == 0:
            self.add_tag("html")
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()

    def print_tree(self, node, indent=0):
        print(" " * indent, node)
        for child in node.children:
            self.print_tree(child, indent + 2)

    def tree_str(self, node, indent=0):
        t = " " * indent
        t += node.__str__()
        for child in node.children:
            t += "\n" + self.tree_str(child, indent + 2)
        return t

    def implicit_tags(self, tag=None):
        # compare the list of unfinished tags to figure out which ones have been omitted
        # more than one tag can be omitted in each row -> loop
        while True:
            open_tags = [node.tag for node in self.unfinished]
            # necessary when the first tag in the document is something other than <html>
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
                # head and body tags can be omitted
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            elif open_tags == ["html", "head"] and tag not in ["/head"] + self.HEAD_TAGS:
                # the /head tag can also be implicit
                self.add_tag("/head")
            else:
                break


def get_attributes(text):
    parts = text.split()
    tag = parts[0].lower()
    attributes = {}
    for attrpair in parts[1:]:
        if "=" in attrpair:
            key, value = attrpair.split("=", 1)
            # value can also be quoted -> strip the quote out
            if len(value) > 2 and value[0] in ["'", "\""]:
                value = value[1:-1]
            attributes[key.lower()] = value
        else:
            # empty string attribute
            attributes[attrpair.lower()] = ""
    return tag, attributes


def check_in_script(text):
    parts = text.split()
    tag = parts[0].lower()
    return tag == "script"
