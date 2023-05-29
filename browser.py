import os
import tkinter
import tkinter.font

from CSSParser import CSSParser
from HTMLParser import HTMLParser
from Layouts.document_layout import DocumentLayout
from draw import DrawRect
from Requests.header import Header
from Requests.request import RequestHandler, resolve_url
from tab import Tab
from token import Element, Text


class Browser:
    WIDTH, HEIGHT = 1000, 800
    HSTEP, VSTEP = 13, 18
    SCROLL_STEP = 70

    def __init__(self):
        # attributes
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=self.WIDTH,
            height=self.HEIGHT,
            # bg="mint cream",
            # bg="white",
            # bg="snow2",
            bg="gainsboro",
        )
        # set up canvas
        self.canvas.pack(expand=True, fill=tkinter.BOTH)
        # bind keys
        self.window.bind("<Down>", self.handle_down)
        self.window.bind("<Up>", self.handle_up)
        self.window.bind("<MouseWheel>", self.handle_mouse_wheel)
        self.window.bind("<Button-4>", self.handle_mouse_scrollup)
        self.window.bind("<Button-5>", self.handle_mouse_scrolldown)
        self.window.bind("<Configure>", self.handle_configure)
        self.window.bind("<KeyPress>", self.handle_key_press)
        self.window.bind("<Button-1>", self.handle_click)
        # manage tabs
        self.tabs = []
        self.active_tab = None

    def load(self, url):
        new_tab = Tab()
        new_tab.load(url)
        self.active_tab = len(self.tabs)
        self.tabs.append(new_tab)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        self.tabs[self.active_tab].draw(self.canvas)

    def handle_down(self, e):
        self.tabs[self.active_tab].scrolldown()
        self.draw()

    def handle_up(self, e):
        self.tabs[self.active_tab].scrollup()
        self.draw()

    def handle_click(self, e):
        self.tabs[self.active_tab].click(e.x, e.y)
        self.draw()

    def handle_mouse_wheel(self, e):
        self.tabs[self.active_tab].on_mouse_wheel(e.delta)
        self.draw()

    def handle_mouse_scrollup(self, e):
        self.tabs[self.active_tab].mouse_scrollup()
        self.draw()

    def handle_mouse_scrolldown(self, e):
        self.tabs[self.active_tab].mouse_scrolldown()
        self.draw()

    def handle_configure(self, e):
        self.tabs[self.active_tab].configure(e.width, e.height)
        self.draw()

    def handle_key_press(self, e):
        self.tabs[self.active_tab].configure(e.keysym)
        self.draw()


# Main method
if __name__ == "__main__":
    import sys
    Browser().load(sys.argv[1])
    tkinter.mainloop()
