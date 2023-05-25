from block_layout import BlockLayout


# Acts as the root of Block Layout
class DocumentLayout:

    HSTEP = 13
    VSTEP = 18

    def __init__(self, node):
        # initialize tree attributes
        self.node = node
        self.parent = None
        self.previous = None
        self.children = []
        self.display_list = []
        # initialize other attributes
        self.width = None
        self.x = None
        self.y = None
        self.height = None

    # create the child layout objects, and then recursively their layout methods
    def layout(self, window_width, window_height, font_size):
        child = BlockLayout(self.node, self, None)
        self.children.append(child)
        # set attributes such that there is padding around content
        self.width = window_width - 2 * self.HSTEP
        self.x = self.HSTEP
        self.y = self.VSTEP
        child.layout(font_size)
        self.height = child.height + 2 * self.VSTEP

    def paint(self, display_list):
        self.children[0].paint(display_list)
