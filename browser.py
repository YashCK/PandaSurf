import os
import tkinter
import tkinter.font

from header import Header
from layout import Layout
from request import RequestHandler


class Browser:
    def __init__(self):
        # set attributes
        self.window = tkinter.Tk()
        self.width = 800
        self.height = 600
        self.hstep = 13
        self.vstep = 18
        self.scroll_step = 70
        self.scroll = 0
        self.canvas = tkinter.Canvas(
            self.window,
            width=self.width,
            height=self.height
        )
        self.rq = RequestHandler()
        self.display_list = []
        self.current_content = ""
        # set up canvas
        self.canvas.pack(expand=True, fill=tkinter.BOTH)
        # bind keys
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<MouseWheel>", self.on_mouse_wheel)
        self.window.bind("<Button-4>", self.mouse_scrollup)
        self.window.bind("<Button-5>", self.mouse_scrolldown)
        self.window.bind("<Configure>", self.configure)
        self.window.bind("<KeyPress>", self.key_press_handler)
        # set up font
        self.font = tkinter.font.Font(
            family="Times",
            size=16,
            weight="normal",
            slant="roman",
        )
        self.font_size = 16

    def load(self, url: str = None):
        try:
            if url is None:
                url = "file://" + os.getcwd() + '/panda_surf_df.txt'
            user_agent_header = Header("User-Agent", "This is the PandaSurf Browser.")
            accept_encoding_header = Header("Accept-Encoding", "gzip")
            header_list = [user_agent_header, accept_encoding_header]
            headers, body = self.rq.request(url, header_list)
            tokens = self.rq.lex(body)
            self.current_content = tokens
            self.display_list = Layout(tokens, self.hstep, self.vstep, self.font, self.width).display_list
            self.draw()
        except FileNotFoundError:
            print("The path to the file you entered does not exist.")
        except ValueError:
            print("The path entered was likely not in the correct format.")

    def draw(self, redraw=False):
        self.canvas.delete("all")
        for x, y, c, f in self.display_list:
            # If the characters are outside the viewing screen, skip the iteration
            if y > self.scroll + self.height:  # below viewing window
                continue
            if y + self.vstep < self.scroll:  # above viewing window
                continue
            # Otherwise add the character to the canvas
            self.font = f
            if redraw:
                self.font.configure(size=self.font_size)
            self.canvas.create_text(x, y - self.scroll, text=c, font=self.font, anchor='nw')

    def redraw(self, adjust_text_size=False):
        self.display_list = Layout(self.current_content, self.hstep, self.vstep, self.font,
                                   self.width).display_list
        self.draw(adjust_text_size)

    def key_press_handler(self, e):
        match e.keysym:
            case 'plus':
                self.font_size += 1
                self.hstep += 1
                self.vstep += 1
                self.redraw(True)
            case 'minus':
                if self.font_size > 1:
                    self.font_size -= 1
                    self.hstep -= 1
                    self.vstep -= 1
                    self.redraw(True)

    def configure(self, e):
        self.width = e.width
        self.height = e.height
        self.redraw()

    def on_mouse_wheel(self, e):
        if sys.platform.startswith('win'):
            if e.delta > 0:
                self.mouse_scrolldown(e)
            else:
                self.mouse_scrollup(e)
        elif sys.platform.startswith('darwin'):
            if e.delta < 0:
                self.mouse_scrolldown(e)
            else:
                self.mouse_scrollup(e)

    def mouse_scrolldown(self, e):
        self.scroll += self.scroll_step / 3
        self.draw()

    def mouse_scrollup(self, e):
        if self.scroll > 0:
            if self.scroll - self.scroll_step < 0:
                self.scroll = 0
            else:
                self.scroll -= self.scroll_step / 3
            self.draw()

    def scrolldown(self, e):
        self.scroll += self.scroll_step
        self.draw()

    def scrollup(self, e):
        if self.scroll > 0:
            if self.scroll - self.scroll_step < 0:
                self.scroll = 0
            else:
                self.scroll -= self.scroll_step
            self.draw()


# Main method
if __name__ == "__main__":
    import sys

    Browser().load(sys.argv[1])
    tkinter.mainloop()
