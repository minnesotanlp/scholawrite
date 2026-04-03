"""ASCII banner display for CLI tools."""
from __future__ import annotations

import shutil

__all__ = ["print_banner", "BANNER_LARGE", "BANNER_SMALL", "VERSION"]

VERSION = "augmented"

# Large banner - SCHOLAWRITE only (no version in the art)
BANNER_LARGE = r"""
███████╗ ██████╗██╗  ██╗ ██████╗ ██╗      █████╗ ██╗    ██╗██████╗ ██╗████████╗███████╗
██╔════╝██╔════╝██║  ██║██╔═══██╗██║     ██╔══██╗██║    ██║██╔══██╗██║╚══██╔══╝██╔════╝
███████╗██║     ███████║██║   ██║██║     ███████║██║ █╗ ██║██████╔╝██║   ██║   █████╗
╚════██║██║     ██╔══██║██║   ██║██║     ██╔══██║██║███╗██║██╔══██╗██║   ██║   ██╔══╝
███████║╚██████╗██║  ██║╚██████╔╝███████╗██║  ██║╚███╔███╔╝██║  ██║██║   ██║   ███████╗
╚══════╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝   ╚═╝   ╚══════╝
"""

# Small banner for narrow terminals
BANNER_SMALL = r"""
░█▀▀░█▀▀░█░█░█▀█░█░░░█▀█░█░█░█▀▄░▀█▀░▀█▀░█▀▀
░▀▀█░█░░░█▀█░█░█░█░░░█▀█░█▄█░█▀▄░░█░░░█░░█▀▀
░▀▀▀░▀▀▀░▀░▀░▀▀▀░▀▀▀░▀░▀░▀░▀░▀░▀░▀▀▀░░▀░░▀▀▀
"""

# Small stylized version text
VERSION_SMALL = r"""  ┌───────────────┐
  │   augmented   │
  └───────────────┘"""

# Minimum terminal width for large banner (large banner is ~90 chars)
LARGE_BANNER_MIN_WIDTH = 95


def get_terminal_width() -> int:
    """Get the current terminal width, with fallback."""
    try:
        return shutil.get_terminal_size().columns
    except (AttributeError, ValueError, OSError):
        return 80  # Conservative default


def _style(text: str, code: str) -> str:
    """Apply ANSI style code to text."""
    return f"\033[{code}m{text}\033[0m"


def _cyan(text: str) -> str:
    """Apply cyan color."""
    return _style(text, "36")


def _dim(text: str) -> str:
    """Apply dim style."""
    return _style(text, "2")


def _bold(text: str) -> str:
    """Apply bold style."""
    return _style(text, "1")


def print_banner(subtitle: str = "") -> None:
    """Print the ScholaWrite ASCII banner with optional subtitle.

    Automatically selects the large or small banner based on terminal width.
    Version is displayed in a smaller format below the main banner.

    Args:
        subtitle: Optional description to display below the banner.
    """
    width = get_terminal_width()

    print()  # Leading newline for spacing

    if width >= LARGE_BANNER_MIN_WIDTH:
        # Large banner with styled version below
        for line in BANNER_LARGE.strip().split('\n'):
            print(_cyan(line))

        # Version line - right-aligned under the banner
        version_text = f"v{VERSION}"
        padding = " " * 75  # Approximate right alignment
        print(_dim(f"{padding}{version_text}"))
        print()

        if subtitle:
            # Centered subtitle
            print(_bold(f"  {subtitle}"))
            print()
    else:
        # Small banner
        for line in BANNER_SMALL.strip().split('\n'):
            print(_cyan(line))

        # Version on same line style
        print(_dim(f"                                          v{VERSION}"))
        print()

        if subtitle:
            print(_bold(f"  {subtitle}"))
            print()


def print_banner_minimal() -> None:
    """Print a minimal one-line banner for tight spaces."""
    print(_cyan("━━━ ") + _bold("SCHOLAWRITE") + _dim(f" v{VERSION}") + _cyan(" ━━━"))
    print()
