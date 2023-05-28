from token import Element


class TagSelector:
    def __init__(self, tag):
        self.tag = tag
        self.priority = 1

    def matches(self, node):
        # return whether the selector matches an element
        return isinstance(node, Element) and self.tag == node.tag


class DescendantSelector:
    def __init__(self, base_selectors):
        self.base_selectors = base_selectors
        self.priority = sum(selector.priority for selector in base_selectors)

    def matches(self, node):
        descendant = self.base_selectors[-1]
        if not descendant.matches(node): return False
        pos = len(self.base_selectors) - 1
        while node.parent and pos >= 0:
            if self.base_selectors[pos].matches(node.parent): return True
            node = node.parent
            pos -= 1
        return False
        # for base_selector in self.base_selectors:
        #     if not base_selector.matches(node):
        #         return False
        #     node = node.parent
        # return True

        # for base_selector in reversed(self.base_selectors):
        #     if not base_selector.matches(node):
        #         return False
        #     node = node.parent
        # return True


class ClassSelector:
    def __init__(self, cls):
        self.cls = cls
        self.priority = 10

    def matches(self, node):
        if isinstance(node, Element) and "class" in node.attributes.keys():
            return self.cls == node.attributes["class"]
