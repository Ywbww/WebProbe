import sys

import colorama
from colorama import Fore, Style

SEVERITY_ANSI = {
    "CRITICAL": Fore.RED + Style.BRIGHT,
    "HIGH":     Fore.RED,
    "MEDIUM":   Fore.YELLOW,
    "LOW":      Fore.CYAN,
    "INFO":     Fore.WHITE + Style.DIM,
}
RESET = Style.RESET_ALL

SEVERITY_HEX = {
    "CRITICAL": "#C0392B",
    "HIGH":     "#E74C3C",
    "MEDIUM":   "#F39C12",
    "LOW":      "#3498DB",
    "INFO":     "#7F8C8D",
}
HTML_BG   = "#FFFFFF"
HTML_TEXT = "#2C3E50"


def init() -> None:
    colorama.init(autoreset=False)


def should_color(args) -> bool:
    if getattr(args, "force_color", False):
        return True
    if getattr(args, "no_color", False):
        return False
    return sys.stdout.isatty()
