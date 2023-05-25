from HTMLParser import HTMLParser


class SourceParser(HTMLParser):

    def __init__(self, body):
        self.body = self.construct_new_body(body)
        print(self.body)
        self.unfinished = []

    def construct_new_body(self, body):
        new_body = ""
        last_br_tag_closed = True
        in_bold = False
        last_four_chars = "    "
        for c in body:
            last_four_chars = last_four_chars[1:4] + c
            if last_br_tag_closed:
                new_body += "<br>" + c
                last_br_tag_closed = False
            elif c == "\n" and not last_br_tag_closed:
                if in_bold:
                    new_body += "</pre></b>"
                    new_body += "</br>"
                    new_body += "<b><pre>"
                else:
                    new_body += "</br>"
                last_br_tag_closed = True
            elif last_four_chars == "&lt;":
                new_body = new_body[:-3]
                new_body += "</pre></b>" + last_four_chars
                in_bold = False
            elif last_four_chars == "&gt;":
                new_body += c
                new_body += "<b><pre>"
                in_bold = True
            else:
                new_body += c
        return new_body

