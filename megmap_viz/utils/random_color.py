from typing import List
import colorsys
import random

# The golden ratio conjugate
golden_ratio_conjugate = 0.618033988749895


def generate_unique_color(
    existing_colors: List[str], h: float = random.random()
):
    while True:
        # Generate color based on the golden ratio
        h += golden_ratio_conjugate
        h %= 1

        # Set fixed saturation and value/brightness
        s = 0.5  # Consider adjusting saturation and value for more color variety
        v = 0.95  # High value: colors will be more intense

        # Convert HSV to RGB
        r, g, b = hsv_to_rgb(h, s, v)

        # Convert RGB to hexadecimal string
        hex_color = "#{:02x}{:02x}{:02x}".format(
            int(r * 255), int(g * 255), int(b * 255)
        )

        # Check if the generated color is already in the existing_colors list
        if hex_color not in existing_colors:
            existing_colors.append(hex_color)
            return hex_color


# Convert HSV to RGB
def hsv_to_rgb(h, s, v):
    return colorsys.hsv_to_rgb(h, s, v)
