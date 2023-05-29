import tkinter
import tkinter.font

from Layouts.font_manager import get_cached_font
from tab import Tab


class Browser:
    WIDTH, HEIGHT = 1000, 800
    HSTEP, VSTEP = 13, 18
    SCROLL_STEP = 70
    CHROME_PX = 80

    HOME_PAGE = "data:text/html,<!DOCTYPE html> \
                <html> \
                <head> \
                <title>Home Page</title> \
                </head> \
                <body> \
                <h1 class=\"title\" style=\"font-size: 50px; font-weight: bold\"> Welcome to PandaSurf</h1> \
                <br> <br> \
                <h1 class=\"title\" style=\"font-size: 50px; font-weight: bold\"> " \
                "Type in the address bar to browse the web :) </h1> \
                <br> <br>\
                </body> \
                </html>"

    def __init__(self):
        # attributes
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=self.WIDTH,
            height=self.HEIGHT,
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
        self.tabs[self.active_tab].draw(self.canvas)
        # draw over letters that stick out
        self.canvas.create_rectangle(0, 0, self.WIDTH, self.CHROME_PX, fill="white", outline="black")
        # draw tab boxes
        tabfont = get_cached_font("Helvetica", 20, "normal", "roman")
        for i, tab in enumerate(self.tabs):
            # 40 pixels tall, 80 pixels wide
            name = "Tab {}".format(i)
            x1, x2 = 40 + 80 * i, 120 + 80 * i
            # draw borders
            self.canvas.create_line(x1, 0, x1, 40, fill="black")
            self.canvas.create_line(x2, 0, x2, 40, fill="black")
            self.canvas.create_text(x1 + 10, 10, anchor="nw", text=name, font=tabfont, fill="black")
            # identify active tab
            if i == self.active_tab:
                self.canvas.create_line(0, 40, x1, 40, fill="black")
                self.canvas.create_line(x2, 40, self.WIDTH, 40, fill="black")
        # draw button that creates new tabs
        button_font = get_cached_font("Helvetica", 21, "normal", "roman")
        self.canvas.create_rectangle(10, 10, 30, 30, outline="black", width=1)
        self.canvas.create_text(15, 7, anchor="nw", text="+", font=button_font, fill="black")
        # draw address bar
        self.canvas.create_rectangle(40, 50, self.WIDTH - 10, 0.8*90, outline="black", width=1)
        url = self.tabs[self.active_tab].url
        self.canvas.create_text(55, 50, anchor='nw', text=url, font=button_font, fill="black")
        # draw back button
        self.canvas.create_rectangle(10, 50, 35, 0.9*self.CHROME_PX, outline="black", width=1)
        self.canvas.create_polygon(0.8*15 + 3, 0.8*70 + 5, 0.8*30 + 3, 0.8*55 + 8, 0.8*30 + 3, 0.8*85 + 1, fill='black')

    def handle_down(self, e):
        self.tabs[self.active_tab].scrolldown()
        self.draw()

    def handle_up(self, e):
        self.tabs[self.active_tab].scrollup()
        self.draw()

    def handle_click(self, e):
        if e.y < self.CHROME_PX:
            if 40 + 80 * len(self.tabs) > e.x >= 40 > e.y >= 0:
                # find which tab was clicked on
                self.active_tab = int((e.x - 40) / 80)
            elif 10 <= e.x < 30 and 10 <= e.y < 30:
                # open new tab
                self.load(self.HOME_PAGE)
            elif 10 <= e.x < 35 and 50 <= e.y < 90:
                # go back in history
                self.tabs[self.active_tab].go_back()
        else:
            # clicked on page content
            self.tabs[self.active_tab].click(e.x, e.y - self.CHROME_PX)
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
        self.WIDTH = e.width
        self.HEIGHT = e.height
        self.tabs[self.active_tab].configure(e.width, e.height)
        self.draw()

    def handle_key_press(self, e):
        self.tabs[self.active_tab].key_press_handler(e.keysym)
        self.draw()


# Main method
if __name__ == "__main__":
    import sys

    Browser().load(sys.argv[1])
    tkinter.mainloop()
