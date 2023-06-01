import ctypes
import sdl2
import skia

from Helper.draw import draw_line, draw_text, draw_rect, DrawRect
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
                </html>                                               \
                                                                      \
                                                                      "

    def __init__(self):
        # set up window
        self.window = sdl2.SDL_CreateWindow(b"Browser",
                                            sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
                                            self.WIDTH, self.HEIGHT, sdl2.SDL_WINDOW_SHOWN)
        # set up surface to draw to
        self.root_surface = skia.Surface.MakeRaster(
            skia.ImageInfo.Make(
                self.WIDTH, self.HEIGHT,
                ct=skia.kRGBA_8888_ColorType,
                at=skia.kUnpremul_AlphaType
            )
        )
        # manage tabs
        self.tabs = []
        self.active_tab = None
        self.focus = None
        self.address_bar = ""
        self.bookmarks = []
        # copy the data to an SDL surface
        if sdl2.SDL_BYTEORDER == sdl2.SDL_BIG_ENDIAN:
            self.RED_MASK = 0xff000000
            self.GREEN_MASK = 0x00ff0000
            self.BLUE_MASK = 0x0000ff00
            self.ALPHA_MASK = 0x000000ff
        else:
            self.RED_MASK = 0x000000ff
            self.GREEN_MASK = 0x0000ff00
            self.BLUE_MASK = 0x00ff0000
            self.ALPHA_MASK = 0xff000000

    def load(self, url):
        new_tab = Tab(self.bookmarks)
        new_tab.load(url)
        self.active_tab = len(self.tabs)
        self.tabs.append(new_tab)
        self.draw()

    def draw(self):
        # clear the canvas
        canvas = self.root_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        # draw the current tab onto canvas
        self.tabs[self.active_tab].draw(canvas)
        # draw over letters that stick out
        draw_rect(canvas, 0, 0, self.WIDTH, self.CHROME_PX, fill="white")
        button_font = skia.Font(skia.Typeface('Helvetica'), 20)
        self.draw_tabs(canvas, button_font)
        self.draw_address_bar(canvas, button_font)
        self.draw_navigation_buttons(canvas)
        self.draw_bookmark_button(canvas)
        self.draw_scrollbar(canvas)
        # make image interface to the Skia surface, but don't copy anything yet
        skia_image = self.root_surface.makeImageSnapshot()
        skia_bytes = skia_image.tobytes()
        depth = 32  # Bits per pixel
        pitch = 4 * self.WIDTH  # Bytes per row
        # wrap data in a sdl surface
        sdl_surface = sdl2.SDL_CreateRGBSurfaceFrom(
            skia_bytes, self.WIDTH, self.HEIGHT, depth, pitch,
            self.RED_MASK, self.GREEN_MASK,
            self.BLUE_MASK, self.ALPHA_MASK)
        # draw all pixel data on the window itself
        rect = sdl2.SDL_Rect(0, 0, self.WIDTH, self.HEIGHT)
        window_surface = sdl2.SDL_GetWindowSurface(self.window)
        # copy all the pixels
        sdl2.SDL_BlitSurface(sdl_surface, rect, window_surface, rect)
        sdl2.SDL_UpdateWindowSurface(self.window)

    def draw_tabs(self, canvas, button_font):
        # tabs
        tabfont = skia.Font(skia.Typeface('Helvetica'), 20)
        for i, tab in enumerate(self.tabs):
            # 40 pixels tall, 80 pixels wide
            name = "Tab {}".format(i)
            x1, x2 = 40 + 80 * i, 120 + 80 * i
            # draw borders
            draw_line(canvas, x1, 0, x1, 40)
            draw_line(canvas, x2, 0, x2, 40)
            draw_text(canvas, x1 + 10, 10, name, tabfont)
            # identify active tab
            if i == self.active_tab:
                draw_line(canvas, 0, 40, x1, 40)
                draw_line(canvas, x2, 40, self.WIDTH, 40)
        # add button
        draw_rect(canvas, 10, 10, 30, 30)
        draw_text(canvas, 15, 10, "+", button_font)

    def draw_address_bar(self, canvas, button_font):
        draw_rect(canvas, 70, 50, self.WIDTH - 45, 0.8 * 90)
        if self.focus == "address bar":
            self.display_text_in_bar(canvas, self.address_bar, button_font, create_line=True)
        else:
            url = self.tabs[self.active_tab].url
            self.display_text_in_bar(canvas, url, button_font)

    def display_text_in_bar(self, canvas, text, button_font, create_line=False):
        w = button_font.measureText(text)
        if w < (self.WIDTH - 45 - 90):
            draw_text(canvas, 75, 53, text, button_font)
        else:
            add_w = self.WIDTH - 45 - 90
            last_portion = text
            while w > add_w and last_portion != "":
                last_portion = last_portion[1:]
                w = button_font.measureText(last_portion)
            draw_text(canvas, 75, 53, last_portion, button_font)
        if create_line:
            draw_line(canvas, 75 + w, 52, 75 + w, 70 + 1)

    def draw_navigation_buttons(self, canvas):
        # draw back button
        draw_rect(canvas, 10, 50, 35, 0.9 * 80)
        path = skia.Path().moveTo(0.8 * 15 + 3, 0.8 * 70 + 5).lineTo(0.8 * 30 + 3, 0.8 * 55 + 8).lineTo(0.8 * 30 + 3,
                                                                                                        0.8 * 85 + 1)
        back_color = skia.ColorBLACK if len(self.tabs[self.active_tab].history) > 1 else skia.ColorGRAY
        back_paint = skia.Paint(Color=back_color, Style=skia.Paint.kFill_Style)
        canvas.drawPath(path, back_paint)
        # draw forward button
        draw_rect(canvas, 40, 50, 65, 0.9 * 80)
        path = skia.Path().moveTo(0.8 * 15 + 48, 0.8 * 70 + 5).lineTo(0.8 * 30 + 23, 0.8 * 55 + 8).lineTo(0.8 * 30 + 23,
                                                                                                          0.8 * 85 + 1)
        forward_color = skia.ColorBLACK if len(self.tabs[self.active_tab].future) > 0 else skia.ColorGRAY
        forward_paint = skia.Paint(Color=forward_color, Style=skia.Paint.kFill_Style)
        canvas.drawPath(path, forward_paint)

    def draw_bookmark_button(self, canvas):
        bookmark_color = 'yellow' if self.tabs[self.active_tab].url in self.bookmarks else 'white'
        draw_rect(canvas, self.WIDTH - 35, 50, self.WIDTH - 10, 0.9 * 80)
        draw_rect(canvas, self.WIDTH - 30, 55, self.WIDTH - 15, 0.9 * 80 - 5)
        draw_rect(canvas, self.WIDTH - 29, 56, self.WIDTH - 15, 0.9 * 80 - 5, fill=bookmark_color)

    def draw_scrollbar(self, canvas):
        tab = self.tabs[self.active_tab]
        max_y = tab.document.height - self.HEIGHT
        if self.HEIGHT < max_y:
            amount_scrolled = (self.HEIGHT + tab.scroll) / max_y - self.HEIGHT / max_y
            x2, y2 = self.WIDTH - 1, amount_scrolled * 0.9 * self.HEIGHT + self.HEIGHT / 10
            rect = DrawRect(self.WIDTH - self.HSTEP + 6, amount_scrolled * 0.9 * self.HEIGHT, x2, y2, "purple")
            rect.execute(0, canvas)

    def handle_down(self):
        self.tabs[self.active_tab].scrolldown()
        self.draw()

    def handle_up(self):
        self.tabs[self.active_tab].scrollup()
        self.draw()

    def handle_click(self, e):
        if e.y < self.CHROME_PX:
            self.focus = None
            if 40 + 80 * len(self.tabs) > e.x >= 40 > e.y >= 0:
                # find which tab was clicked on
                self.active_tab = int((e.x - 40) / 80)
            elif 10 <= e.x < 30 and 10 <= e.y < 30:
                # open new tab
                self.load(self.HOME_PAGE)
            elif 10 <= e.x < 35 and 50 <= e.y < 0.9 * 80:
                # go back in history
                self.tabs[self.active_tab].go_back()
            elif 40 <= e.x < 65 and 50 <= e.y < 0.9 * 80:
                # forward in history
                self.tabs[self.active_tab].go_forward()
            elif 40 <= e.x < self.WIDTH - 45 and 50 <= e.y < 0.8 * 90:
                self.focus = "address bar"
                self.address_bar = ""
            elif self.WIDTH - 45 <= e.x < self.WIDTH and 55 <= e.y < 0.8 * 90 - 5:
                url = self.tabs[self.active_tab].url
                if url in self.bookmarks:
                    self.bookmarks.remove(url)
                else:
                    self.bookmarks.append(url)
        else:
            self.focus = "content"
            # clicked on page content
            self.tabs[self.active_tab].click(e.x, e.y - self.CHROME_PX)
        self.draw()

    def handle_mouse_wheel(self, scroll_x, scroll_y):
        self.tabs[self.active_tab].on_mouse_wheel(scroll_y)
        self.draw()

    def handle_configure(self, w, h):
        self.WIDTH = w
        self.HEIGHT = h
        self.tabs[self.active_tab].configure(w, h)
        self.draw()

    def middle_click(self, x, y):
        self.focus = None
        if y < self.CHROME_PX:
            if 40 + 80 * len(self.tabs) > x >= 40 > y >= 0:
                # find which tab was clicked on
                self.active_tab = int((x - 40) / 80)
            elif 10 <= x < 30 and 10 <= y < 30:
                # open new tab
                self.load(self.HOME_PAGE)
            elif 10 <= x < 35 and 50 <= y < 0.9 * 80:
                # go back in history
                self.tabs[self.active_tab].go_back()
            elif 40 <= x < self.WIDTH - 10 and 50 <= y < 0.8 * 90:
                self.focus = "address bar"
                self.address_bar = ""
        else:
            # clicked on page content
            self.load(self.HOME_PAGE)
            self.tabs[self.active_tab].click(x, y - self.CHROME_PX)
        self.draw()

    def handle_press(self, press):
        if press == sdl2.SDLK_BACKSPACE and self.focus == "address bar":
            self.address_bar = self.address_bar[:-1]
            self.draw()
        elif press == sdl2.SDLK_PLUS or press == sdl2.SDLK_MINUS:
            self.tabs[self.active_tab].key_press_handler(press)
            self.draw()

    def handle_key(self, char):
        # ignore cases where no character is typed
        if not (0x20 <= ord(char) < 0x7f): return
        if self.focus == "address bar":
            self.address_bar += char
            self.draw()
        elif self.focus == "content":
            self.tabs[self.active_tab].keypress(char)
            self.draw()
        else:
            self.tabs[self.active_tab].key_press_handler(char)
            self.draw()

    def handle_enter(self):
        if self.focus == "address bar":
            self.tabs[self.active_tab].load(self.address_bar)
            self.focus = None
            self.draw()
        elif self.focus == "content":
            tab = self.tabs[self.active_tab]
            tab_focus = tab.focus
            while tab_focus:
                if tab_focus.tag == "form" and "action" in tab_focus.attributes:
                    return tab.submit_form(tab_focus)
                tab_focus = tab_focus.parent

    def handle_quit(self):
        sdl2.SDL_DestroyWindow(self.window)


# Main method
if __name__ == "__main__":
    import sys

    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS)
    browser = Browser()
    browser.load(sys.argv[1])
    # implement mainloop
    event = sdl2.SDL_Event()
    while True:
        # check inputs
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == sdl2.SDL_QUIT:
                browser.handle_quit()
                sdl2.SDL_Quit()
                sys.exit()
            elif event.type == sdl2.SDL_MOUSEBUTTONDOWN:
                if event.button.button == sdl2.SDL_BUTTON_MIDDLE:
                    browser.middle_click(event.button.x, event.button.y)
            elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                browser.handle_click(event.button)
            elif event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_RETURN:
                    browser.handle_enter()
                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    browser.handle_down()
                elif event.key.keysym.sym == sdl2.SDLK_UP:
                    browser.handle_up()
                elif event.key.keysym.sym == sdl2.SDLK_BACKSPACE and browser.focus == "address bar":
                    browser.address_bar = browser.address_bar[:-1]
                    browser.draw()
                elif event.key.keysym.sym == sdl2.SDLK_MINUS or event.key.keysym.sym == 45:
                    browser.tabs[browser.active_tab].key_press_handler('-')
                    browser.draw()
                elif event.key.keysym.sym == sdl2.SDLK_PLUS or event.key.keysym.sym == 61:
                    browser.tabs[browser.active_tab].key_press_handler('+')
                    browser.draw()
            elif event.type == sdl2.SDL_TEXTINPUT:
                browser.handle_key(event.text.text.decode('utf8'))
            elif event.type == sdl2.SDL_MOUSEWHEEL:
                scrollX = event.wheel.x  # horizontal scroll amount
                scrollY = event.wheel.y  # vertical scroll amount
                browser.handle_mouse_wheel(scrollX, scrollY)
            elif event.type == sdl2.SDL_WINDOWEVENT:
                if event.window.event == sdl2.SDL_WINDOWEVENT_RESIZED:
                    browser.handle_configure(event.window.data1, event.window.data2)
