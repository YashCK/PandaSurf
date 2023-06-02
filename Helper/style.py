from CSSParser import CSSParser
from Helper.animation import NumericAnimation
from Helper.tokens import Element

REFRESH_RATE_SEC = 0.016  # 16ms
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
ANIMATED_PROPERTIES = {
    "opacity": NumericAnimation,
}


def style(node, rules, tab):
    old_style = node.style
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
        if not selector.matches(node): continue
        for prop, value in body.items():
            node.style[prop] = value
    # parse style attribute to fill in the style field
    if isinstance(node, Element) and "style" in node.attributes:
        pairs = CSSParser(node.attributes["style"]).body()
        for prop, value in pairs.items():
            node.style[prop] = value
    # font size
    if node.style["font-size"].endswith("%"):
        if node.parent:
            parent_font_size = node.parent.style["font-size"]
        else:
            parent_font_size = INHERITED_PROPERTIES["font-size"]
        node_pct = float(node.style["font-size"][:-1]) / 100
        parent_px = float(parent_font_size[:-2])
        node.style["font-size"] = str(node_pct * parent_px) + "px"
    # animate every time a style value changes
    if old_style:
        transitions = diff_styles(old_style, node.style)
        for prop, (old_value, new_value, num_frames) in transitions.items():
            if prop in ANIMATED_PROPERTIES:
                tab.set_needs_render()
                AnimationClass = ANIMATED_PROPERTIES[prop]
                animation = AnimationClass(old_value, new_value, num_frames)
                node.animations[prop] = animation
                node.style[prop] = animation.animate()
    # apply the same to children nodes
    for child in node.children:
        style(child, rules, tab)


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


def parse_transition(value):
    # return a dictionary mapping property names to transition durations (frames)
    properties = {}
    if not value: return properties
    for item in value.split(","):
        prop, duration = item.split(" ", 1)
        frames = float(duration[:-1]) / REFRESH_RATE_SEC
        properties[prop] = frames
    return properties


def diff_styles(old_style, new_style):
    # look for the properties (part of transition property)
    old_transitions = parse_transition(old_style.get("transition"))
    new_transitions = parse_transition(new_style.get("transition"))
    # loop through the properties mentioned in transition and see which ones changed
    transitions = {}
    for prop in old_transitions:
        if prop not in new_transitions: continue
        num_frames = new_transitions[prop]
        if prop not in old_style: continue
        if prop not in new_style: continue
        old_value = old_style[prop]
        new_value = new_style[prop]
        if old_value == new_value: continue
        transitions[prop] = (old_value, new_value, num_frames)
    return transitions
