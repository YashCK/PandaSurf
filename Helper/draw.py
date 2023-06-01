import skia


class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.top = y1
        self.left = x1
        self.text = text
        self.font = font
        self.right = x1 + font.measureText(text)
        self.bottom = y1 - font.getMetrics().fAscent + font.getMetrics().fDescent
        self.color = color
        self.rect = skia.Rect.MakeLTRB(x1, y1, self.right, self.bottom)

    def execute(self, scroll, canvas):
        draw_text(canvas, self.left, self.top - scroll, self.text, self.font, self.color)


class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color
        self.rect = skia.Rect.MakeLTRB(x1, y1, x2, y2)

    def execute(self, scroll, canvas):
        draw_rect(canvas,
                  self.left, self.top - scroll,
                  self.right, self.bottom - scroll,
                  fill=self.color, width=0)


class DrawLine:
    def __init__(self, x1, y1, x2, y2):
        self.rect = skia.Rect.MakeLTRB(x1, y1, x2, y2)
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def execute(self, canvas):
        draw_line(canvas, self.x1, self.y1, self.x2, self.y2)


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


def draw_rect(canvas, l, t, r, b, fill=None, width=1):
    paint = skia.Paint()
    if fill:
        paint.setStrokeWidth(width)
        paint.setColor(parse_color(fill))
    else:
        paint.setStyle(skia.Paint.kStroke_Style)
        paint.setStrokeWidth(1)
        paint.setColor(skia.ColorBLACK)
    rect = skia.Rect.MakeLTRB(l, t, r, b)
    canvas.drawRect(rect, paint)
