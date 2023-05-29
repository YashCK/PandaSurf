import tkinter

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
    # manage inherited properties
    # find_inherited_property(node, "color", "black")
    # find_inherited_property(node, "font-family", "Didot")
    # find_inherited_property(node, "font-size", 16)
    # find_inherited_property(node, "font-style", "roman")
    # find_inherited_property(node, "font-weight", "normal")
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
    key = (family, size, weight, slant)
    if key not in FONTS:
        font = tkinter.font.Font(family=family, size=size, weight=weight, slant=slant)
        FONTS[key] = font
    return FONTS[key]
