import os
import tkinter
import tkinter.font

from header import Header
from request import RequestHandler


class Browser:
    def __init__(self):
        # set attributes
        self.window = tkinter.Tk()
        self.width = 800
        self.height = 600
        self.hstep = 13
        self.vstep = 18
        self.scroll_step = 50
        self.font_size = 16
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

    def load(self, url: str = None):
        try:
            if url is None:
                url = "file://" + os.getcwd() + '/panda_surf_df.txt'
            user_agent_header = Header("User-Agent", "This is the PandaSurf Browser.")
            accept_encoding_header = Header("Accept-Encoding", "gzip")
            header_list = [user_agent_header, accept_encoding_header]
            headers, body = self.rq.request(url, header_list)
            text = self.rq.lex(body)
            self.current_content = text
            self.display_list = self.layout(text)
            self.draw()
        except FileNotFoundError:
            print("The path to the file you entered does not exist.")
        except ValueError:
            print("The path entered was likely not in the correct format.")

    def draw(self):
        self.canvas.delete("all")
        font = tkinter.font.Font(size=self.font_size)
        for x, y, c in self.display_list:
            # If the characters are outside the viewing screen, skip the iteration
            if y > self.scroll + self.height:  # below viewing window
                continue
            if y + self.vstep < self.scroll:  # above viewing window
                continue
            # Otherwise add the character to the canvas
            self.canvas.create_text(x, y - self.scroll, text=c, font=font)

    # compute and store the position of each character
    def layout(self, text: str) -> list[(int, int, str)]:
        display_list = []
        cursor_x, cursor_y = self.hstep, self.vstep
        for c in text:
            # create line break for \n characters
            if c == "\n":
                cursor_y += 1.25 * self.vstep
                cursor_x = self.hstep
                continue
            # append position and character to the display list
            display_list.append((cursor_x, cursor_y, c))
            cursor_x += self.hstep
            if cursor_x >= self.width - self.hstep:
                cursor_y += self.vstep
                cursor_x = self.hstep
        return display_list

    def key_press_handler(self, e):
        match e.keysym:
            case 'plus':
                self.font_size += 1
                self.hstep += 1
                self.vstep += 1
                self.display_list = self.layout(self.current_content)
                self.draw()
            case 'minus':
                if self.font_size > 1:
                    self.font_size -= 1
                    self.hstep -= 1
                    self.vstep -= 1
                    self.display_list = self.layout(self.current_content)
                    self.draw()

    def configure(self, e):
        self.width = e.width
        self.height = e.height
        self.display_list = self.layout(self.current_content)
        self.draw()

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
