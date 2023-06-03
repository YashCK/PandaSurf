import skia

FONTS = {}


def get_font(node, size_delta=0):
    family = node.style["font-family"]
    weight = node.style["font-weight"]
    style = node.style["font-style"]
    # In case of var
    if weight == "var":
        weight = "normal"
    # translate CSS normal to Tk roman
    if style == "normal":
        style = "roman"
    # convert CSS pixels to Tk points
    size = int(float(node.style["font-size"][:-2]) * .75) + size_delta
    return get_cached_font(family, size, weight, style)


def find_inherited_property(node, prop, default_val):
    if node.style[prop] == "inherit":
        new_prop = default_val
        while node.parent:
            node_prop = node.style["color"]
            if node_prop != "inherit":
                new_prop = node_prop
                break
            node = node.parent
        node.style[prop] = new_prop


def get_cached_font(family, size, weight, slant):
    key = (family, weight, slant)
    if key not in FONTS:
        if weight == "bold":
            skia_weight = skia.FontStyle.kBold_Weight
        else:
            skia_weight = skia.FontStyle.kNormal_Weight
        if slant == "italic":
            skia_style = skia.FontStyle.kItalic_Slant
        else:
            skia_style = skia.FontStyle.kUpright_Slant
        skia_width = skia.FontStyle.kNormal_Width
        style_info = skia.FontStyle(skia_weight, skia_width, skia_style)
        font = skia.Typeface(family, style_info)
        FONTS[key] = font
    return skia.Font(FONTS[key], size)


def linespace(font):
    metrics = font.getMetrics()
    return metrics.fDescent - metrics.fAscent
