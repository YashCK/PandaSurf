import os
import tkinter

from header import Header
from request import RequestHandler

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100


class Browser:
    def __init__(self):
        # set attributes
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
        )
        self.rq = RequestHandler()
        self.display_list = []
        self.scroll = 0
        # set up canvas
        self.canvas.pack()
        # bind DOWN key
        self.window.bind("<Down>", self.scrolldown)

    def load(self, url: str = None):
        try:
            if url is None:
                url = "file://" + os.getcwd() + '/panda_surf_df.txt'
            user_agent_header = Header("User-Agent", "This is the PandaSurf Browser.")
            accept_encoding_header = Header("Accept-Encoding", "gzip")
            header_list = [user_agent_header, accept_encoding_header]
            headers, body = self.rq.request(url, header_list)
            text = self.rq.lex(body)
            self.display_list = layout(text)
            self.draw()
        except FileNotFoundError:
            print("The path to the file you entered does not exist.")
        except ValueError:
            print("The path entered was likely not in the correct format.")

    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            # If the characters are outside the viewing screen, skip the iteration
            if y > self.scroll + HEIGHT: # below viewing window
                continue
            if y + VSTEP < self.scroll: # above viewing window
                continue
            # Otherwise add the character to the canvas
            self.canvas.create_text(x, y - self.scroll, text=c)

    def scrolldown(self, e):
        self.scroll += SCROLL_STEP
        self.draw()


# compute and store the position of each character
def layout(text: str) -> list[(int, int, str)]:
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        if cursor_x >= WIDTH - HSTEP:
            cursor_y += VSTEP
            cursor_x = HSTEP
    return display_list


# Main method
if __name__ == "__main__":
    import sys
    Browser().load(sys.argv[1])
    tkinter.mainloop()
