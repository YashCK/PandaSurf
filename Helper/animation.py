class NumericAnimation:
    # animates numeric propertieslike opacity
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
