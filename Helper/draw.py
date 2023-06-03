import skia

from Helper.animation import parse_transform


class DisplayItem:
    def __init__(self, rect, children=[], node=None):
        self.rect = rect
        self.children = children
        self.node = node
        self.needs_compositing = any([
            child.needs_compositing for child in self.children
        ])

    def is_paint_command(self):
        return False

    def map(self, rect):
        return rect

    def add_composited_bounds(self, rect):
        rect.join(self.rect)
        for cmd in self.children:
            cmd.add_composited_bounds(rect)


class DrawText(DisplayItem):
    def __init__(self, x1, y1, text, font, color):
        self.left = x1
        self.top = y1
        self.right = x1 + font.measureText(text)
        self.bottom = y1 - font.getMetrics().fAscent + font.getMetrics().fDescent
        self.font = font
        self.text = text
        self.color = color
        super().__init__(skia.Rect.MakeLTRB(x1, y1, self.right, self.bottom))

    def execute(self, canvas):
        draw_text(canvas, self.left, self.top, self.text, self.font, self.color)

    def is_paint_command(self):
        return True


class DrawRect(DisplayItem):
    def __init__(self, x1, y1, x2, y2, color):
        super().__init__(skia.Rect.MakeLTRB(x1, y1, x2, y2))
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color

    def execute(self, canvas):
        draw_rect(canvas,
                  self.left, self.top,
                  self.right, self.bottom,
                  fill_color=self.color, width=0)

    def is_paint_command(self):
        return True


class DrawLine(DisplayItem):
    def __init__(self, x1, y1, x2, y2):
        super().__init__(skia.Rect.MakeLTRB(x1, y1, x2, y2))
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def execute(self, canvas):
        draw_line(canvas, self.x1, self.y1, self.x2, self.y2)

    def is_paint_command(self):
        return True


class DrawRRect(DisplayItem):
    def __init__(self, rect, radius, color):
        super().__init__(rect)
        self.rrect = skia.RRect.MakeRectXY(rect, radius, radius)
        self.color = color

    def execute(self, canvas):
        sk_color = parse_color(self.color)
        canvas.drawRRect(self.rrect, paint=skia.Paint(Color=sk_color))

    def is_paint_command(self):
        return True


class ClipRRect(DisplayItem):
    def __init__(self, rect, radius, children, should_clip=True):
        super().__init__(rect, children)
        self.should_clip = should_clip
        self.radius = radius
        self.rrect = skia.RRect.MakeRectXY(rect, radius, radius)

    def execute(self, canvas):
        if self.should_clip:
            canvas.save()
            canvas.clipRRect(self.rrect)
        for cmd in self.children:
            cmd.execute(canvas)
        if self.should_clip:
            canvas.restore()

    def clone(self, children):
        return ClipRRect(self.rect, self.radius, children, self.should_clip)


class SaveLayer(DisplayItem):
    def __init__(self, sk_paint, node, children, should_save=True):
        super().__init__(skia.Rect.MakeEmpty(), children, node)
        self.should_save = should_save
        self.sk_paint = sk_paint
        if should_save:
            self.needs_compositing = True

    def execute(self, canvas):
        if self.should_save:
            canvas.saveLayer(paint=self.sk_paint)
        for cmd in self.children:
            cmd.execute(canvas)
        if self.should_save:
            canvas.restore()

    def clone(self, children):
        # create a new SaveLayer with the same parameters but new children
        return SaveLayer(self.sk_paint, self.node, children, self.should_save)


class CompositedLayer:
    def __init__(self, skia_context, display_item):
        self.skia_context = skia_context
        self.surface = None
        self.display_items = [display_item]
        self.parent = display_item.parent

    def can_merge(self, display_item):
        return display_item.parent == self.display_items[0].parent

    def add(self, display_item):
        assert self.can_merge(display_item)
        self.display_items.append(display_item)

    def composited_bounds(self):
        rect = skia.Rect.MakeEmpty()
        for item in self.display_items:
            item.add_composited_bounds(rect)
        return rect

    def absolute_bounds(self):
        rect = skia.Rect.MakeEmpty()
        for item in self.display_items:
            rect.join(absolute_bounds(item))
        return rect

    def raster(self):
        bounds = self.composited_bounds()
        if bounds.isEmpty(): return
        irect = bounds.roundOut()
        # create surface of the right size
        if not self.surface:
            self.surface = skia.Surface.MakeRenderTarget(
                self.skia_context, skia.Budgeted.kNo,
                skia.ImageInfo.MakeN32Premul(
                    irect.width(), irect.height()))
            if not self.surface:
                self.surface = skia.Surface(irect.width(), irect.height())
            assert self.surface
        canvas = self.surface.getCanvas()
        # offset by the top and left of the composited bounds
        canvas.clear(skia.ColorTRANSPARENT)
        canvas.save()
        canvas.translate(-bounds.left(), -bounds.top())
        for item in self.display_items:
            item.execute(canvas)
        canvas.restore()
        draw_rect(canvas, 0, 0, irect.width() - 1, irect.height() - 1, border_color="red")


class DrawCompositedLayer(DisplayItem):
    def __init__(self, composited_layer):
        self.composited_layer = composited_layer
        super().__init__(self.composited_layer.composited_bounds())

    def execute(self, canvas):
        # draw surface into parent surface with the correct offset
        layer = self.composited_layer
        if not layer.surface: return
        bounds = layer.composited_bounds()
        layer.surface.draw(canvas, bounds.left(), bounds.top())


class Transform(DisplayItem):
    def __init__(self, translation, rect, node, children):
        super().__init__(rect, children, node)
        self.translation = translation

    def execute(self, canvas):
        if self.translation:
            (x, y) = self.translation
            canvas.save()
            canvas.translate(x, y)
        for cmd in self.children:
            cmd.execute(canvas)
        if self.translation:
            canvas.restore()

    def map(self, rect):
        return map_translation(rect, self.translation)

    def clone(self, children):
        return Transform(self.translation, self.rect, self.node, children)


def parse_color(color):
    if color == "white":
        return skia.ColorWHITE
    elif color == "red":
        return skia.ColorRED
    elif color == "blue":
        return skia.ColorBLUE
    elif color == "lightblue":
        return skia.ColorSetARGB(0xFF, 0xAD, 0xD8, 0xE6)
    elif color == "dark gray":
        return skia.ColorDKGRAY
    elif color == "gray":
        return skia.ColorGRAY
    elif color == "light gray" or color == "light grey":
        return skia.ColorLTGRAY
    elif color == "green":
        return skia.ColorGRAY
    elif color == "lightgreen":
        return skia.ColorSetARGB(0xFF, 0x90, 0xEE, 0x90)
    elif color == "yellow":
        return skia.ColorYELLOW
    elif color == "purple":
        return skia.ColorSetARGB(0xFF, 0x80, 0x00, 0x80)
    elif color == "orange":
        return skia.ColorSetARGB(0xFF, 0xFF, 0xA5, 0x00)
    else:
        return skia.ColorBLACK


def draw_line(canvas, x1, y1, x2, y2):
    path = skia.Path().moveTo(x1, y1).lineTo(x2, y2)
    paint = skia.Paint(Color=skia.ColorBLACK)
    paint.setStyle(skia.Paint.kStroke_Style)
    paint.setStrokeWidth(1)
    canvas.drawPath(path, paint)


def draw_text(canvas, x, y, text, font, color=None):
    sk_color = parse_color(color)
    paint = skia.Paint(AntiAlias=True, Color=sk_color)
    canvas.drawString(
        text, float(x), y - font.getMetrics().fAscent,
        font, paint)


def draw_rect(canvas, l, t, r, b, fill_color=None, border_color="black", width=1):
    paint = skia.Paint()
    if fill_color:
        paint.setStrokeWidth(width);
        paint.setColor(parse_color(fill_color))
    else:
        paint.setStyle(skia.Paint.kStroke_Style)
    paint.setStrokeWidth(width)
    paint.setColor(parse_color(border_color))
    rect = skia.Rect.MakeLTRB(l, t, r, b)
    canvas.drawRect(rect, paint)


def parse_blend_mode(blend_mode_str):
    if blend_mode_str == "multiply":
        return skia.BlendMode.kMultiply
    elif blend_mode_str == "difference":
        return skia.BlendMode.kDifference
    else:
        return skia.BlendMode.kSrcOver


def paint_visual_effects(node, cmds, rect):
    opacity = float(node.style.get("opacity", "1.0"))
    blend_mode = parse_blend_mode(node.style.get("mix-blend-mode"))
    translation = parse_transform(node.style.get("transform", ""))
    # create a new layer, draw a mask behind it, and blend with the element contents
    border_radius = float(node.style.get("border-radius", "0px")[:-2])
    if node.style.get("overflow", "visible") == "clip":
        clip_radius = border_radius
    else:
        clip_radius = 0
    # turn off the parameters if an effect isn’t applied:
    needs_clip = node.style.get("overflow", "visible") == "clip"
    needs_blend_isolation = blend_mode != skia.BlendMode.kSrcOver or needs_clip or opacity != 1.0
    # return surfaces
    # use ClipRRect to get rid of the destination-in blended surface
    save_layer = \
        SaveLayer(skia.Paint(BlendMode=blend_mode, Alphaf=opacity), node, [
            ClipRRect(rect, clip_radius, cmds, should_clip=needs_clip),
        ], should_save=needs_blend_isolation)
    transform = Transform(translation, rect, node, [save_layer])
    # record saved layer on the Element
    node.save_layer = save_layer
    return [transform]


def map_translation(rect, translation):
    if not translation:
        return rect
    else:
        (x, y) = translation
        matrix = skia.Matrix()
        matrix.setTranslate(x, y)
        return matrix.mapRect(rect)


def absolute_bounds_for_obj(obj):
    rect = skia.Rect.MakeXYWH(
        obj.x, obj.y, obj.width, obj.height)
    cur = obj.node
    while cur:
        rect = map_translation(rect, parse_transform(cur.style.get("transform", "")))
        cur = cur.parent
    return rect


def absolute_bounds(display_item):
    rect = skia.Rect.MakeEmpty()
    display_item.add_composited_bounds(rect)
    effect = display_item.parent
    while effect:
        rect = effect.map(rect)
        effect = effect.parent
    return rect
