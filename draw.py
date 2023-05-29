import tkinter

from Layouts.font_manager import get_cached_font


class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.top = y1
        self.left = x1
        self.text = text
        self.font = font
        self.bottom = y1 + font.metrics("linespace")
        self.color = color

    def execute(self, scroll, canvas, delta=None):
        font = self.font
        # if delta:
        #     font = get_cached_font(self.font['family'], self.font['size'] + delta,
        #                            self.font['weight'], self.font['slant'])
        if self.color == "var":
            self.color = "black"
        canvas.create_text(
            self.left, self.top - scroll,
            text=self.text,
            font=font,
            anchor='nw',
            fill=self.color,
        )


class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color

    def execute(self, scroll, canvas, alternate_size=None):
        canvas.create_rectangle(
            self.left, self.top - scroll,
            self.right, self.bottom - scroll,
            width=0,
            fill=self.color,
        )


def catch_color_errors(color):
    try:
        tkinter.font.nametofont(color)
        return True
    except tkinter.TclError:
        return False
