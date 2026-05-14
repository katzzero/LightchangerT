# Shared color definitions for LightchangerT
from collections import namedtuple

Color = namedtuple("Color", ["r", "g", "b"])

COLOR_MAP = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
    "pink": (255, 192, 203),
    "light_blue": (0, 191, 255),
    "light_green": (144, 238, 144),
    "light_red": (255, 100, 100),
    "dark_blue": (0, 0, 139),
    "dark_green": (0, 100, 0),
}

BRAND_COLORS = {
    "sony": "blue",
    "microsoft": "green",
    "nintendo": "red",
    "steam": "light_blue",
    "nvidia": "light_green",
    "default": "white",
}