class NumericAnimation:
    def __init__(self, old_value, new_value, num_frames):
        self.old_value = float(old_value)
        self.new_value = float(new_value)
        self.num_frames = num_frames

        self.frame_count = 1
        total_change = self.new_value - self.old_value
        self.change_per_frame = total_change / num_frames

    def animate(self):
        # increment frame count
        self.frame_count += 1
        if self.frame_count >= self.num_frames: return
        # compute new value and return it
        current_value = self.old_value + self.change_per_frame * self.frame_count
        return str(current_value)


class TranslateAnimation:
    def __init__(self, old_value, new_value, num_frames):
        (self.old_x, self.old_y) = parse_transform(old_value)
        (new_x, new_y) = parse_transform(new_value)
        self.num_frames = num_frames
        self.frame_count = 1
        self.change_per_frame_x = (new_x - self.old_x) / num_frames
        self.change_per_frame_y = (new_y - self.old_y) / num_frames

    def animate(self):
        self.frame_count += 1
        if self.frame_count >= self.num_frames: return
        new_x = self.old_x + self.change_per_frame_x * self.frame_count
        new_y = self.old_y + self.change_per_frame_y * self.frame_count
        return "translate({}px,{}px)".format(new_x, new_y)


def parse_transform(transform_str):
    if transform_str.find('translate(') < 0:
        return None
    left_paren = transform_str.find('(')
    right_paren = transform_str.find(')')
    (x_px, y_px) = \
        transform_str[left_paren + 1:right_paren].split(",")
    return float(x_px[:-2]), float(y_px[:-2])
