import ctypes
import threading

import OpenGL.GL
import sdl2
import skia

from Helper.draw import draw_line, draw_text, draw_rect, DrawRect, DrawCompositedLayer, SaveLayer, absolute_bounds, \
    CompositedLayer
from Helper.measure_time import MeasureTime
from Helper.style import tree_to_list, add_parent_pointers
from Helper.task import Task
from tab import Tab

REFRESH_RATE_SEC = 0.016  # 16ms


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

    def __init__(self, single_threaded):
        # set up window
        self.window = sdl2.SDL_CreateWindow(b"Browser",
                                            sdl2.SDL_WINDOWPOS_CENTERED,
                                            sdl2.SDL_WINDOWPOS_CENTERED,
                                            self.WIDTH, self.HEIGHT,
                                            sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_OPENGL)
        self.gl_context = sdl2.SDL_GL_CreateContext(self.window)
        print(("OpenGL initialized: vendor={}," + "renderer={}").format(
            OpenGL.GL.glGetString(OpenGL.GL.GL_VENDOR),
            OpenGL.GL.glGetString(OpenGL.GL.GL_RENDERER)))
        self.skia_context = skia.GrDirectContext.MakeGL()
        # set up surface to draw to
        self.root_surface = \
            skia.Surface.MakeFromBackendRenderTarget(
                self.skia_context,
                skia.GrBackendRenderTarget(
                    self.WIDTH, self.HEIGHT, 0, 0,
                    skia.GrGLFramebufferInfo(0, OpenGL.GL.GL_RGBA8)),
                skia.kBottomLeft_GrSurfaceOrigin,
                skia.kRGBA_8888_ColorType,
                skia.ColorSpace.MakeSRGB())
        assert self.root_surface is not None
        # surfaces
        self.chrome_surface = skia.Surface.MakeRenderTarget(
            self.skia_context, skia.Budgeted.kNo,
            skia.ImageInfo.MakeN32Premul(self.WIDTH, self.CHROME_PX))
        assert self.chrome_surface is not None
        self.tab_surface = None
        self.scroll_surface = self.create_scroll_surface()
        # manage tabs
        self.tabs = []
        self.active_tab = None
        self.focus = None
        self.address_bar = ""
        self.bookmarks = []
        self.LAST_SCROLL = False
        # necessary to do redo work
        self.single_threaded = single_threaded
        self.needs_raster_and_draw = False
        self.animation_timer = None
        self.needs_animation_frame = True
        self.composited_updates = {}
        self.composited_layers = []
        self.display_list = []
        self.draw_list = None
        self.needs_composite = False
        self.needs_raster = False
        self.needs_draw = False
        self.measure_composite_raster_and_draw = MeasureTime("composite-raster-and-draw")
        # information for commit
        self.lock = threading.Lock()
        self.url = None
        self.scroll = 0
        self.active_tab_height = 0
        self.active_tab_display_list = None
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
        self.lock.acquire(blocking=True)
        self.load_internal(url)
        self.lock.release()

    def load_internal(self, url):
        new_tab = Tab(self, self.bookmarks)
        self.set_active_tab(len(self.tabs))
        self.tabs.append(new_tab)
        self.schedule_load(url)

    def raster_scroll(self):
        if not self.scroll_surface:
            self.scroll_surface = self.create_scroll_surface()
        canvas = self.scroll_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        self.draw_scrollbar(canvas)

    def raster_tab(self):
        for composited_layer in self.composited_layers:
            composited_layer.raster()

    def raster_chrome(self):
        # draw the browser chrome to the chrome_surface
        canvas = self.chrome_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        # draw chrome elements
        draw_rect(canvas, 0, 0, self.WIDTH, self.CHROME_PX, fill_color="white")
        button_font = skia.Font(skia.Typeface('Helvetica'), 20)
        self.draw_tabs(canvas, button_font)
        self.draw_address_bar(canvas, button_font)
        self.draw_navigation_buttons(canvas)
        self.draw_bookmark_button(canvas)

    def draw(self):
        # set up canvas
        canvas = self.root_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        canvas.save()
        canvas.translate(0, self.CHROME_PX - self.scroll)
        for item in self.draw_list:
            item.execute(canvas)
        canvas.restore()
        # copy from chrome surface to the root surface
        chrome_rect = skia.Rect.MakeLTRB(0, 0, self.WIDTH, self.CHROME_PX)
        canvas.save()
        canvas.clipRect(chrome_rect)
        self.chrome_surface.draw(canvas, 0, 0)
        canvas.restore()
        # copy from scroll surface to the root surface
        scroll_rect = skia.Rect.MakeLTRB(self.WIDTH - self.HSTEP + 6, self.CHROME_PX, self.WIDTH, self.HEIGHT)
        canvas.save()
        canvas.clipRect(scroll_rect)
        self.scroll_surface.draw(canvas, 0, self.CHROME_PX)
        canvas.restore()
        # flush the skia surface and swap windows
        self.root_surface.flushAndSubmit()
        sdl2.SDL_GL_SwapWindow(self.window)

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
            if self.url:
                self.display_text_in_bar(canvas, self.url, button_font)

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
        tab = self.tabs[self.active_tab]
        # draw back button
        draw_rect(canvas, 10, 50, 35, 0.9 * 80)
        path = skia.Path().moveTo(0.8 * 15 + 3, 0.8 * 70 + 5).lineTo(0.8 * 30 + 3, 0.8 * 55 + 8).lineTo(0.8 * 30 + 3,
                                                                                                        0.8 * 85 + 1)
        back_color = skia.ColorBLACK if len(tab.history) > 1 else skia.ColorGRAY
        back_paint = skia.Paint(Color=back_color, Style=skia.Paint.kFill_Style)
        canvas.drawPath(path, back_paint)
        # draw forward button
        draw_rect(canvas, 40, 50, 65, 0.9 * 80)
        path = skia.Path().moveTo(0.8 * 15 + 48, 0.8 * 70 + 5).lineTo(0.8 * 30 + 23, 0.8 * 55 + 8).lineTo(0.8 * 30 + 23,
                                                                                                          0.8 * 85 + 1)
        forward_color = skia.ColorBLACK if len(tab.future) > 0 else skia.ColorGRAY
        forward_paint = skia.Paint(Color=forward_color, Style=skia.Paint.kFill_Style)
        canvas.drawPath(path, forward_paint)

    def draw_bookmark_button(self, canvas):
        bookmark_color = 'yellow' if self.tabs[self.active_tab].url in self.bookmarks else 'white'
        draw_rect(canvas, self.WIDTH - 35, 50, self.WIDTH - 10, 0.9 * 80)
        draw_rect(canvas, self.WIDTH - 30, 55, self.WIDTH - 15, 0.9 * 80 - 5)
        draw_rect(canvas, self.WIDTH - 29, 56, self.WIDTH - 15, 0.9 * 80 - 5, fill_color=bookmark_color)

    def draw_scrollbar(self, canvas):
        # max_y = tab.document.height - self.HEIGHT
        max_y = self.active_tab_height - (self.HEIGHT - self.CHROME_PX)
        if self.HEIGHT < max_y:
            amount_scrolled = (self.HEIGHT + self.scroll) / max_y - self.HEIGHT / max_y
            x2, y2 = self.WIDTH - 1, amount_scrolled * 0.9 * (self.HEIGHT - self.CHROME_PX) + self.HEIGHT / 10
            rect = DrawRect(self.WIDTH - self.HSTEP + 6, amount_scrolled * 0.9 * (self.HEIGHT - self.CHROME_PX),
                            x2, y2, "purple")
            rect.execute(canvas)

    def handle_down(self):
        self.lock.acquire(blocking=True)
        if not self.active_tab_height:
            self.lock.release()
            return
        scroll = self.clamp_scroll(self.scroll + self.SCROLL_STEP, self.active_tab_height, True)
        self.scroll = scroll
        self.set_needs_draw()
        self.needs_animation_frame = True
        self.lock.release()

    def handle_up(self):
        self.lock.acquire(blocking=True)
        if not self.active_tab_height:
            self.lock.release()
            return
        scroll = self.clamp_scroll(self.scroll - self.SCROLL_STEP, self.active_tab_height, False)
        self.scroll = scroll
        self.set_needs_draw()
        self.needs_animation_frame = True
        self.lock.release()

    def handle_click(self, e):
        self.lock.acquire(blocking=True)
        if e.y < self.CHROME_PX:
            self.focus = None
            if 40 + 80 * len(self.tabs) > e.x >= 40 > e.y >= 0:
                # find which tab was clicked on
                self.set_active_tab(int((e.x - 40) / 80))
                tab = self.tabs[self.active_tab]
                task = Task(tab.set_needs_render)
                tab.task_runner.schedule_task(task)
            elif 10 <= e.x < 30 and 10 <= e.y < 30:
                # open new tab
                self.load_internal(self.HOME_PAGE)
            elif 10 <= e.x < 35 and 50 <= e.y < 0.9 * 80:
                # go back in history
                tab = self.tabs[self.active_tab]
                task = Task(tab.go_back)
                tab.task_runner.schedule_task(task)
                self.clear_data()
            elif 40 <= e.x < 65 and 50 <= e.y < 0.9 * 80:
                # forward in history
                tab = self.tabs[self.active_tab]
                task = Task(tab.go_forward)
                tab.task_runner.schedule_task(task)
                self.clear_data()
            elif 40 <= e.x < self.WIDTH - 45 and 50 <= e.y < 0.8 * 90:
                self.focus = "address bar"
                self.address_bar = ""
            elif self.WIDTH - 45 <= e.x < self.WIDTH and 55 <= e.y < 0.8 * 90 - 5:
                url = self.tabs[self.active_tab].url
                if url in self.bookmarks:
                    self.bookmarks.remove(url)
                else:
                    self.bookmarks.append(url)
            self.set_needs_raster()
        else:
            # clicked on page content
            self.focus = "content"
            tab = self.tabs[self.active_tab]
            task = Task(tab.click, e.x, e.y - self.CHROME_PX)
            tab.task_runner.schedule_task(task)
        self.lock.release()

    def handle_mouse_wheel(self, scroll_x, scroll_y):
        if scroll_y < 0 or scroll_y == 0 and self.LAST_SCROLL:
            self.handle_down()
            self.LAST_SCROLL = True
        else:
            self.handle_up()
            self.LAST_SCROLL = False

    def handle_configure(self, w, h):
        self.lock.acquire(blocking=True)
        self.WIDTH = w
        self.HEIGHT = h
        current_tab = self.tabs[self.active_tab]
        task = Task(current_tab.configure)
        current_tab.task_runner.schedule_task(task)
        # change surfaces
        self.tab_surface = None
        self.scroll_surface = None
        self.raster_tab()
        self.raster_chrome()
        self.set_needs_raster()
        self.set_needs_draw()
        self.lock.release()

    def handle_press(self, press):
        self.lock.acquire(blocking=True)
        if press == sdl2.SDLK_BACKSPACE and self.focus == "address bar":
            self.address_bar = self.address_bar[:-1]
            self.set_needs_raster()
        self.lock.release()

    def handle_key(self, char):
        self.lock.acquire(blocking=True)
        # ignore cases where no character is typed
        if not (0x20 <= ord(char) < 0x7f): return
        if self.focus == "address bar":
            self.address_bar += char
            self.set_needs_raster()
        elif self.focus == "content":
            current_tab = self.tabs[self.active_tab]
            task = Task(current_tab.keypress, char)
            current_tab.task_runner.schedule_task(task)
        elif char == '-' or char == '+':
            self.change_text_size(char)
        self.lock.release()

    def change_text_size(self, char):
        current_tab = self.tabs[self.active_tab]
        task = Task(current_tab.key_press_handler, char)
        current_tab.task_runner.schedule_task(task)
        self.set_needs_raster()
        self.set_needs_draw()

    def handle_enter(self):
        self.lock.acquire(blocking=True)
        if self.focus == "address bar":
            self.schedule_load(self.address_bar)
            self.url = self.address_bar
            self.focus = None
            self.set_needs_raster()
            self.needs_animation_frame = True
        elif self.focus == "content":
            tab = self.tabs[self.active_tab]
            tab_focus = tab.focus
            while tab_focus:
                if tab_focus.tag == "form" and "action" in tab_focus.attributes:
                    return tab.submit_form(tab_focus)
                tab_focus = tab_focus.parent
        self.lock.release()

    def handle_quit(self):
        print(self.measure_composite_raster_and_draw.text())
        self.tabs[self.active_tab].task_runner.set_needs_quit()
        sdl2.SDL_DestroyWindow(self.window)
        sdl2.SDL_GL_DeleteContext(self.gl_context)
        sdl2.SDL_DestroyWindow(self.window)

    def create_scroll_surface(self):
        surface = skia.Surface.MakeRenderTarget(
            self.skia_context, skia.Budgeted.kNo,
            skia.ImageInfo.MakeN32Premul(self.WIDTH, self.HEIGHT - self.CHROME_PX))
        assert surface is not None
        return surface

    def clone_latest(self, visual_effect, current_effect):
        node = visual_effect.node
        if node not in self.composited_updates:
            return visual_effect.clone(current_effect)
        save_layer = self.composited_updates[node]
        if type(visual_effect) is SaveLayer:
            return save_layer.clone(current_effect)
        return visual_effect.clone(current_effect)

    def composite_raster_and_draw(self):
        self.lock.acquire(blocking=True)
        if not self.needs_composite and \
                len(self.composited_updates) == 0 \
                and not self.needs_raster and not self.needs_draw:
            self.lock.release()
            return
        self.measure_composite_raster_and_draw.start_timing()
        if self.needs_composite:
            self.composite()
        if self.needs_raster:
            self.raster_chrome()
            self.raster_tab()
        if self.needs_draw:
            self.paint_draw_list()
            self.draw()
        self.measure_composite_raster_and_draw.stop_timing()
        self.needs_composite = False
        self.needs_raster = False
        self.needs_draw = False
        self.lock.release()

    def set_needs_animation_frame(self, tab):
        self.lock.acquire(blocking=True)
        if tab == self.tabs[self.active_tab]:
            self.needs_animation_frame = True
        self.lock.release()

    def schedule_animation_frame(self):
        def callback():
            self.lock.acquire(blocking=True)
            scroll = self.scroll
            current_tab = self.tabs[self.active_tab]
            self.needs_animation_frame = False
            self.lock.release()
            task = Task(current_tab.run_animation_frame, scroll)
            current_tab.task_runner.schedule_task(task)

        self.lock.acquire(blocking=True)
        if self.needs_animation_frame and not self.animation_timer:
            if not self.single_threaded:
                self.animation_timer = threading.Timer(REFRESH_RATE_SEC, callback)
                self.animation_timer.start()
        self.lock.release()

    def schedule_load(self, url, body=None):
        current_tab = self.tabs[self.active_tab]
        current_tab.task_runner.clear_pending_tasks()
        task = Task(current_tab.load, url, body)
        current_tab.task_runner.schedule_task(task)

    def commit(self, tab, data):
        self.lock.acquire(blocking=True)
        if tab == self.tabs[self.active_tab]:
            self.url = data.url
            if data.scroll is not None:
                self.scroll = data.scroll
            self.active_tab_height = data.height
            if data.display_list:
                self.active_tab_display_list = data.display_list
            self.animation_timer = None
            self.composited_updates = data.composited_updates
            if not self.composited_updates:
                self.composited_updates = {}
                self.set_needs_composite()
            else:
                self.set_needs_draw()
        self.lock.release()

    def set_active_tab(self, index):
        # schedule a new animation frame:
        self.active_tab = index
        self.clear_data()
        self.needs_animation_frame = True

    def render(self):
        if self.single_threaded:
            tab = self.tabs[self.active_tab]
            tab.task_runner.run_tasks()
            tab.run_animation_frame(self.scroll)

    def clamp_scroll(self, scroll, tab_height, down):
        if down:
            return max(0, min(scroll, tab_height - (self.HEIGHT - self.CHROME_PX)))
        else:
            return max(0, scroll)

    def set_needs_raster(self):
        self.needs_raster = True
        self.needs_draw = True

    def set_needs_composite(self):
        self.needs_composite = True
        self.needs_raster = True
        self.needs_draw = True

    def set_needs_draw(self):
        self.needs_draw = True

    def composite(self):
        self.composited_layers = []
        add_parent_pointers(self.active_tab_display_list)
        # list all the paint_commands
        all_commands = []
        for cmd in self.active_tab_display_list:
            all_commands = tree_to_list(cmd, all_commands)
        non_composited_commands = [cmd for cmd in all_commands
                                   if not cmd.needs_compositing and
                                   (not cmd.parent or cmd.parent.needs_compositing)]
        for cmd in non_composited_commands:
            did_break = False
            for layer in reversed(self.composited_layers):
                if layer.can_merge(cmd):
                    layer.add(cmd)
                    did_break = True
                    break
                elif skia.Rect.Intersects(layer.absolute_bounds(), absolute_bounds(cmd)):
                    layer = CompositedLayer(self.skia_context, cmd)
                    self.composited_layers.append(layer)
                    did_break = True
                    break
            if not did_break:
                layer = CompositedLayer(self.skia_context, cmd)
                self.composited_layers.append(layer)
        self.active_tab_height = 0
        for layer in self.composited_layers:
            self.active_tab_height = max(self.active_tab_height, layer.absolute_bounds().bottom())

    def paint_draw_list(self):
        self.draw_list = []
        for composited_layer in self.composited_layers:
            # for each composited layer, create a DrawCompositedLayer command
            current_effect = DrawCompositedLayer(composited_layer)
            if not composited_layer.display_items: continue
            # wrap the DrawCompositedLayer in each visual effect that applies to that composited layer
            parent = composited_layer.display_items[0].parent
            while parent:
                current_effect = parent.clone_latest([current_effect])
                parent = parent.parent
            self.draw_list.append(current_effect)

    def clear_data(self):
        self.scroll = 0
        self.url = None
        self.display_list = []
        self.composited_layers = []


def raster(display_list, canvas):
    for cmd in display_list:
        cmd.execute(canvas)


# Main method
if __name__ == "__main__":
    import sys

    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS)
    browser = Browser(True)
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
                    browser.handle_press(event.key.keysym.sym)
                    # browser.address_bar = browser.address_bar[:-1]
                    # browser.set_needs_raster()
                elif event.key.keysym.sym == sdl2.SDLK_MINUS or event.key.keysym.sym == 45:
                    browser.change_text_size('-')
                elif event.key.keysym.sym == sdl2.SDLK_PLUS or event.key.keysym.sym == 61:
                    browser.change_text_size('+')
            elif event.type == sdl2.SDL_TEXTINPUT:
                browser.handle_key(event.text.text.decode('utf8'))
            elif event.type == sdl2.SDL_MOUSEWHEEL:
                scrollX = event.wheel.x  # horizontal scroll amount
                scrollY = event.wheel.y  # vertical scroll amount
                browser.handle_mouse_wheel(scrollX, scrollY)
            elif event.type == sdl2.SDL_WINDOWEVENT:
                if event.window.event == sdl2.SDL_WINDOWEVENT_RESIZED:
                    browser.handle_configure(event.window.data1, event.window.data2)
            # in case of single thread
            active_tab = browser.tabs[browser.active_tab]
            if browser.single_threaded:
                if active_tab.task_runner.needs_quit:
                    break
                if browser.needs_animation_frame:
                    browser.needs_animation_frame = False
                    browser.render()
            # schedule a new rendering task every 16 milliseconds
            browser.composite_raster_and_draw()
            browser.schedule_animation_frame()
