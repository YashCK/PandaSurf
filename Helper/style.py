from CSSParser import CSSParser
from Helper.tokens import Element

INHERITED_PROPERTIES = {
    "show-contents": "True",
    "in-pre-tag": "False",
    "in-bullet": "False",
    "font-family": "Didot",
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "color": "black",
}


def style(node, rules):
    node.style = {}
    # inherit font properties
    for prop, default_value in INHERITED_PROPERTIES.items():
        if node.parent:
            node.style[prop] = node.parent.style[prop]
        else:
            node.style[prop] = default_value
    # loop over all elements and all rules in order to add the property/value pairs
    # to the element's style information
    for selector, body in rules:
        if not selector.matches(node):
            continue
        for prop, value in body.items():
            computed_value = compute_style(node, prop, value)
            if not computed_value: continue
            node.style[prop] = computed_value
    # parse style attribute to fill in the style filed
    if isinstance(node, Element) and "style" in node.attributes:
        pairs = CSSParser(node.attributes["style"]).body()
        for prop, value in pairs.items():
            computed_value = compute_style(node, prop, value)
            node.style[prop] = computed_value
    # apply the same to children nodes
    for child in node.children:
        style(child, rules)


def compute_style(node, prop, value):
    # browsers resolve percentages to absolute pixel units
    # before they are storied in style or are inherited
    if prop == "font-size":
        if value.endswith("px"):
            return value
        elif value.endswith("%"):
            # percentage for the root html element is relative to default font size
            if node.parent:
                parent_font_size = node.parent.style["font-size"]
            else:
                parent_font_size = INHERITED_PROPERTIES["font-size"]
            node_pct = float(value[:-1]) / 100
            parent_px = float(parent_font_size[:-2])
            return str(node_pct * parent_px) + "px"
        else:
            return None
    else:
        return value


def tree_to_list(tree, array):
    array.append(tree)
    for child in tree.children:
        tree_to_list(child, array)
    return array


def add_parent_pointers(nodes, parent=None):
    for node in nodes:
        node.parent = parent
        add_parent_pointers(node.children, node)