"""CLI utilities including menus, spinners, styling, and help formatting."""
from __future__ import annotations

import sys
import shutil
import time
import threading
import itertools
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterator, List, Optional

__all__ = [
    # Core classes
    "Spinner", "ProgressBar", "Menu", "MenuItem", "MenuStyle", "HelpFormatter",
    # Styling functions
    "style", "success", "error", "warning", "info", "dim", "bold", "header",
    # Prompt functions
    "prompt_path", "prompt_choice", "prompt_confirm", "prompt_number",
    # Utilities
    "clear_screen", "get_terminal_size", "section", "divider",
    # Pipeline utilities
    "pipeline_stage", "spinner_factory",
    # Constants
    "Style",
]


def _detect_utf8() -> bool:
    """Detect if terminal supports UTF-8 encoding."""
    try:
        return sys.stdout.encoding.lower().startswith('utf')
    except (AttributeError, TypeError):
        return False


def _detect_terminal_width() -> int:
    """Get terminal width with fallback."""
    try:
        if sys.stdout.isatty():
            return shutil.get_terminal_size().columns
    except (AttributeError, ValueError, OSError):
        pass
    return 80


def _detect_jupyter() -> bool:
    """Detect Jupyter or Colab environment."""
    return 'ipykernel' in sys.modules or 'google.colab' in sys.modules


_HAS_UTF8 = _detect_utf8()
_TERMINAL_WIDTH = _detect_terminal_width()
_IS_JUPYTER = _detect_jupyter()


class Style:
    """ANSI escape codes for terminal styling."""
    # Reset
    RESET = "\033[0m"

    # Colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Styles
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Background
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


def _supports_color() -> bool:
    """Check if terminal supports color output."""
    if not hasattr(sys.stdout, "isatty"):
        return False
    if not sys.stdout.isatty():
        return False
    return True


def style(text: str, *styles: str) -> str:
    """Apply ANSI styles to text.

    Supports both Style class attributes and color name strings.

    Args:
        text: Text to style
        *styles: Style codes (Style.RED) or color names ("RED", "GREEN")

    Examples:
        style("Hello", Style.RED, Style.BOLD)
        style("Hello", "RED")
    """
    if not _supports_color():
        return text

    # Handle string color names for simple API
    resolved_styles = []
    color_map = {
        "CYAN": Style.CYAN,
        "GREEN": Style.GREEN,
        "RED": Style.RED,
        "YELLOW": Style.YELLOW,
        "BLUE": Style.BLUE,
        "MAGENTA": Style.MAGENTA,
        "WHITE": Style.WHITE,
        "RESET": Style.RESET,
    }

    for s in styles:
        if isinstance(s, str) and s in color_map:
            resolved_styles.append(color_map[s])
        else:
            resolved_styles.append(s)

    prefix = "".join(resolved_styles)
    return f"{prefix}{text}{Style.RESET}"


def success(text: str) -> str:
    """Format text as success (green)."""
    check = "✓" if _HAS_UTF8 else "[OK]"
    return style(f"{check} {text}", Style.GREEN)


def error(text: str) -> str:
    """Format text as error (red)."""
    cross = "✗" if _HAS_UTF8 else "[X]"
    return style(f"{cross} {text}", Style.RED)


def warning(text: str) -> str:
    """Format text as warning (yellow)."""
    warn = "⚠" if _HAS_UTF8 else "[!]"
    return style(f"{warn} {text}", Style.YELLOW)


def info(text: str) -> str:
    """Format text as info (blue)."""
    info_char = "ℹ" if _HAS_UTF8 else "[i]"
    return style(f"{info_char} {text}", Style.BLUE)


def dim(text: str) -> str:
    """Format text as dimmed."""
    return style(text, Style.DIM)


def bold(text: str) -> str:
    """Format text as bold."""
    return style(text, Style.BOLD)


def header(text: str) -> str:
    """Format text as header (bold cyan)."""
    return style(text, Style.BOLD, Style.CYAN)


def get_terminal_size() -> tuple[int, int]:
    """Get terminal dimensions (columns, rows)."""
    try:
        size = shutil.get_terminal_size()
        return size.columns, size.lines
    except (AttributeError, ValueError, OSError):
        return 80, 24


def clear_screen() -> None:
    """Clear the terminal screen."""
    print("\033[2J\033[H", end="")


_SPINNER_FRAMES = {
    "default": (
        ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        if _HAS_UTF8 else ["|", "/", "-", "\\"]
    ),
    "dots": (
        ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
        if _HAS_UTF8 else [".", "..", "...", "...."]
    ),
    "blocks": (
        ["▖", "▘", "▝", "▗"]
        if _HAS_UTF8 else ["#", "##", "###", "####"]
    ),
    "braille": (
        ["⠋", "⠙", "⠚", "⠞", "⠖", "⠦", "⠴", "⠲", "⠳", "⠓"]
        if _HAS_UTF8 else ["|", "/", "-", "\\"]
    ),
    "minimal": (
        ["◐", "◓", "◑", "◒"]
        if _HAS_UTF8 else [".", "o", "O", "o"]
    ),
}

# Global spinner state for nested contexts
_SPINNER_LOCK = threading.Lock()
_ACTIVE_SPINNER: Optional["Spinner"] = None
_SPINNER_STACK: List["Spinner"] = []


class Spinner:
    """Animated loading spinner with nested context support.

    Features:
    - Multiple frame styles (default, dots, blocks, braille, minimal)
    - UTF-8/ASCII automatic fallback
    - Nested context support (pauses parent spinner)
    - Elapsed time display for long operations
    - Robust interrupt handling

    Usage:
        with Spinner("Processing data"):
            do_work()

        # Or manually:
        spinner = Spinner("Loading", style="dots")
        spinner.start()
        do_work()
        spinner.succeed("Done!")

        # Nested spinners:
        with Spinner("Outer task"):
            do_work()
            with Spinner("Inner task"):  # Outer pauses automatically
                do_inner_work()
    """

    def __init__(
        self,
        message: str = "Processing",
        style: str = "default",
        interval: float = 0.08,
        stream: Any = None,
        prefix: str = "",
    ):
        self.message = message
        self.prefix = prefix
        self.frames = _SPINNER_FRAMES.get(style, _SPINNER_FRAMES["default"])
        self.interval = interval
        self.stream = stream or (sys.stdout if _IS_JUPYTER else sys.stderr)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._frame_cycle = itertools.cycle(self.frames)
        self._start_time = time.time()
        self._last_render = ""
        self._render_lock = threading.Lock()

    def _get_terminal_width(self) -> int:
        """Get current terminal width (may change during execution)."""
        try:
            if self.stream.isatty():
                return shutil.get_terminal_size().columns
        except (AttributeError, ValueError, OSError):
            pass
        return _TERMINAL_WIDTH

    def _safe_write(self, text: str) -> None:
        """Atomic write that handles terminal resizes and interruptions."""
        with self._render_lock:
            try:
                width = self._get_terminal_width()
                # Clear previous line completely
                clear = "\r" + " " * (width - 1) + "\r"
                self.stream.write(clear)
                self.stream.write(text[:width - 1])
                self.stream.flush()
                self._last_render = text
            except (IOError, BrokenPipeError):
                self._stop_event.set()

    def _animate(self) -> None:
        """Animation loop with interruption hardening."""
        try:
            while not self._stop_event.is_set():
                frame = next(self._frame_cycle)
                elapsed = time.time() - self._start_time
                elapsed_str = f" ({elapsed:.1f}s)" if elapsed > 10 else ""
                output = f"{self.prefix}{style(frame, Style.CYAN)} {self.message}{elapsed_str}"
                self._safe_write(output)
                time.sleep(self.interval)
        except Exception:
            pass  # Silent failure preserves pipeline integrity

    def start(self) -> "Spinner":
        """Start spinner with nested context awareness."""
        global _ACTIVE_SPINNER, _SPINNER_STACK

        with _SPINNER_LOCK:
            if _ACTIVE_SPINNER is not None:
                # Preserve parent spinner state for nested contexts
                _SPINNER_STACK.append(_ACTIVE_SPINNER)
                _ACTIVE_SPINNER._stop_spinner(silent=True)

            _ACTIVE_SPINNER = self
            self._stop_event.clear()
            self._start_time = time.time()
            self._thread = threading.Thread(
                target=self._animate, daemon=True, name="SpinnerThread"
            )
            self._thread.start()
            return self

    def _stop_spinner(self, silent: bool = False) -> None:
        """Internal stop without global state management."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=0.3)
            self._thread = None

        if silent:
            self._safe_write("\r" + " " * (self._get_terminal_width() - 1) + "\r")

    def stop(self, final_message: Optional[str] = None, silent: bool = False) -> None:
        """Stop spinner with cleanup."""
        global _ACTIVE_SPINNER, _SPINNER_STACK

        self._stop_spinner(silent=silent)

        with _SPINNER_LOCK:
            if _ACTIVE_SPINNER is self:
                _ACTIVE_SPINNER = None
                # Restore parent spinner if nested
                if _SPINNER_STACK:
                    parent = _SPINNER_STACK.pop()
                    parent.start()

        if silent:
            return

        if final_message:
            self._safe_write(final_message + "\n")
        else:
            # Show completion with elapsed time
            elapsed = time.time() - self._start_time
            check = "✓" if _HAS_UTF8 else "[OK]"
            self._safe_write(
                f"{self.prefix}{style(check, Style.GREEN)} {self.message} ({elapsed:.2f}s)\n"
            )

    def update(self, message: str) -> None:
        """Dynamically update spinner message."""
        self.message = message

    def succeed(self, message: Optional[str] = None) -> None:
        """Stop with success indicator."""
        check = "✓" if _HAS_UTF8 else "[OK]"
        self.stop(f"{self.prefix}{style(check, Style.GREEN)} {message or self.message}")

    def fail(self, message: Optional[str] = None) -> None:
        """Stop with failure indicator."""
        cross = "✗" if _HAS_UTF8 else "[X]"
        self.stop(f"{self.prefix}{style(cross, Style.RED)} {message or self.message}")

    def __enter__(self) -> "Spinner":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is KeyboardInterrupt:
            interrupt = "^C" if _HAS_UTF8 else "[INT]"
            self.stop(
                f"{self.prefix}{style(interrupt, Style.YELLOW)} Interrupted",
                silent=False
            )
            return False  # Propagate KeyboardInterrupt
        elif exc_type:
            self.fail(f"{exc_type.__name__}: {exc_val}")
            return False
        else:
            self.succeed()
            return False


class ProgressBar:
    """Adaptive progress bar with EMA-based ETA calculation.

    Features:
    - Terminal-width adaptive rendering
    - Exponential moving average for stable ETA
    - Speed tracking in human-readable units
    - Jupyter-compatible fallback
    - Nested loop support via prefix

    Usage:
        with ProgressBar(total=100, description="Processing") as bar:
            for item in items:
                process(item)
                bar.update(1)
    """

    def __init__(
        self,
        total: int,
        description: str = "Progress",
        unit: str = "it",
        width: Optional[int] = None,
        fill_char: str = "█" if _HAS_UTF8 else "#",
        empty_char: str = "░" if _HAS_UTF8 else ".",
        prefix: str = "",
        smoothing: float = 0.7,
        stream: Any = None,
    ):
        self.total = total
        self.description = description
        self.unit = unit
        self.fill_char = fill_char
        self.empty_char = empty_char
        self.prefix = prefix
        self.smoothing = smoothing
        self.stream = stream or sys.stderr

        # Calculate initial width
        term_width = _detect_terminal_width()
        self.width = width or max(30, min(60, term_width - len(description) - 40))

        self.current = 0
        self._start_time = time.time()
        self._last_update = self._start_time
        self._ema_rate = 0.0
        self._samples: List[tuple[float, float]] = []

    def update(self, n: int = 1, force: bool = False) -> None:
        """Update progress with adaptive ETA calculation."""
        now = time.time()
        self.current = min(self.current + n, self.total)

        # Sample rate for moving average (avoid sampling too frequently)
        if now - self._last_update > 0.2 or force:
            elapsed = now - self._last_update
            rate = n / elapsed if elapsed > 0 else 0
            self._samples.append((now, rate))
            # Keep only last 10 samples for stability
            if len(self._samples) > 10:
                self._samples.pop(0)
            self._last_update = now

        self._render()

    def set(self, value: int) -> None:
        """Set progress to specific value."""
        delta = max(0, value - self.current)
        self.current = min(value, self.total)
        if delta > 0:
            self.update(0, force=True)
        else:
            self._render()

    def set_description(self, description: str) -> None:
        """Dynamically update description."""
        self.description = description
        self._render()

    def _calculate_eta(self) -> float:
        """Calculate ETA using exponential moving average."""
        if self.current == 0:
            return float('inf')

        # Calculate current rate from samples
        if len(self._samples) > 1:
            total_items = sum(
                rate * (t2 - t1)
                for (t1, _), (t2, rate) in zip(self._samples[:-1], self._samples[1:])
            )
            total_time = self._samples[-1][0] - self._samples[0][0]
            current_rate = total_items / total_time if total_time > 0 else 0
        else:
            elapsed = time.time() - self._start_time
            current_rate = self.current / elapsed if elapsed > 0 else 0

        # Apply EMA smoothing
        if self._ema_rate == 0:
            self._ema_rate = current_rate
        else:
            self._ema_rate = (
                self.smoothing * current_rate +
                (1 - self.smoothing) * self._ema_rate
            )

        remaining = self.total - self.current
        return remaining / self._ema_rate if self._ema_rate > 0 else float('inf')

    def _format_eta(self, eta: float) -> str:
        """Format ETA in human-readable form."""
        if eta >= 3600 * 24:
            return ""
        elif eta >= 3600:
            return f"ETA {eta/3600:.1f}h"
        elif eta >= 60:
            return f"ETA {eta/60:.1f}m"
        else:
            return f"ETA {eta:.0f}s"

    def _format_speed(self, rate: float) -> str:
        """Format speed in human-readable form."""
        if self.unit == "doc":
            return f"{rate * 60:.1f} docs/min"
        elif rate > 1000:
            return f"{rate/1000:.1f}k {self.unit}/s"
        else:
            return f"{rate:.1f} {self.unit}/s"

    def _render(self) -> None:
        """Render progress bar with adaptive terminal width."""
        if not self.stream.isatty() and not _IS_JUPYTER:
            # Silent mode for logs/pipes - only print on completion
            if self.current == self.total:
                print(
                    f"{self.prefix}{self.description}: "
                    f"100% ({self.total}/{self.total})"
                )
            return

        term_width = _detect_terminal_width()
        percent = self.current / self.total if self.total > 0 else 0

        # Calculate ETA and speed
        eta = self._calculate_eta()
        eta_str = self._format_eta(eta)

        elapsed = time.time() - self._start_time
        rate = self._ema_rate or (self.current / elapsed if elapsed > 0 else 0)
        speed = self._format_speed(rate)

        # Build progress line with adaptive bar width
        base = f"{self.prefix}{self.description}: "
        suffix = f" {percent*100:5.1f}% ({self.current}/{self.total}) {speed} {eta_str}"

        # Calculate available space for bar
        available = max(10, term_width - len(base) - len(suffix) - 2)
        bar_width = min(self.width, available)

        filled = int(bar_width * percent)
        bar = self.fill_char * filled + self.empty_char * (bar_width - filled)

        line = f"\r{base}{style(bar, Style.CYAN)}{suffix}"

        try:
            self.stream.write(line[:term_width - 1])
            self.stream.flush()
        except (IOError, BrokenPipeError):
            pass

    def finish(self) -> None:
        """Complete progress bar with summary."""
        self.current = self.total
        self._render()

        elapsed = time.time() - self._start_time
        rate = self.total / elapsed if elapsed > 0 else 0

        check = "✓" if _HAS_UTF8 else "[OK]"
        print(
            f"\n{self.prefix}{check} Completed {self.total} {self.unit}s "
            f"in {elapsed:.1f}s ({rate:.1f} {self.unit}/s)"
        )

    def __enter__(self) -> "ProgressBar":
        self._render()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is KeyboardInterrupt:
            cross = "✗" if _HAS_UTF8 else "[X]"
            print(f"\n{self.prefix}{cross} Interrupted at {self.current}/{self.total}")
        else:
            self.finish()


@contextmanager
def pipeline_stage(
    stage_name: str,
    total: Optional[int] = None,
    unit: str = "doc"
) -> Iterator[Callable[[int], None]]:
    """Context manager for pipeline stages with integrated progress.

    Automatically uses a progress bar if total is provided, otherwise
    uses a spinner. Provides a progress callback for consistent API.

    Usage:
        with pipeline_stage("Generating injections", total=1000) as progress:
            for doc in docs:
                generate_injections(doc)
                progress(1)

        with pipeline_stage("Loading model") as progress:
            load_model()
            progress()  # No-op for spinner, but maintains API
    """
    prefix = f"  [{len(_SPINNER_STACK) + 1}] "

    if total:
        with ProgressBar(
            total=total,
            description=stage_name,
            unit=unit,
            prefix=prefix
        ) as pb:
            def progress(n: int = 1) -> None:
                pb.update(n)
            yield progress
    else:
        with Spinner(message=stage_name, prefix=prefix, style="dots"):
            def progress(n: int = 1) -> None:
                pass  # No-op for spinner, maintains API consistency
            yield progress


def spinner_factory(spinner_style: str = "default") -> Callable[[str, str], Spinner]:
    """Factory for creating consistently styled spinners.

    Usage:
        create_spinner = spinner_factory("dots")
        with create_spinner("Processing"):
            do_work()
    """
    def create(message: str, prefix: str = "") -> Spinner:
        return Spinner(message=message, style=spinner_style, prefix=prefix)
    return create


@dataclass
class MenuItem:
    """A single menu item."""
    key: str
    label: str
    description: str = ""
    action: Optional[Callable[[], Any]] = None
    submenu: Optional["Menu"] = None


class MenuStyle(Enum):
    """Menu display styles."""
    NUMBERED = "numbered"
    LETTERED = "lettered"
    ARROWS = "arrows"


class Menu:
    """Interactive CLI menu with professional styling.

    Usage:
        menu = Menu("Main Menu", [
            MenuItem("1", "Ingest Data", "Load and normalize seed data"),
            MenuItem("2", "Generate Injections", "Create AI injections"),
            MenuItem("q", "Quit", "Exit the application"),
        ])
        choice = menu.show()
    """

    def __init__(
        self,
        title: str,
        items: List[MenuItem],
        subtitle: str = "",
        menu_style: MenuStyle = MenuStyle.NUMBERED,
        show_back: bool = False,
    ):
        self.title = title
        self.items = items
        self.subtitle = subtitle
        self.menu_style = menu_style
        self.show_back = show_back

    def _strip_ansi(self, text: str) -> str:
        """Remove ANSI escape codes for length calculation."""
        import re
        return re.sub(r'\033\[[0-9;]*m', '', text)

    def render(self) -> str:
        """Render the menu as a string."""
        term_width, _ = get_terminal_size()
        width = min(70, term_width - 4)

        lines = []

        # Title
        lines.append("")
        lines.append(style(f"  {self.title}", Style.BOLD, Style.CYAN))
        if self.subtitle:
            lines.append(style(f"  {self.subtitle}", Style.DIM))
        lines.append("")

        divider_char = "─" if _HAS_UTF8 else "-"
        lines.append(style("  " + divider_char * (width - 4), Style.DIM))
        lines.append("")

        # Menu items
        for item in self.items:
            key_style = style(f"[{item.key}]", Style.BOLD, Style.YELLOW)
            label = item.label
            if item.description:
                desc = style(f"  {item.description}", Style.DIM)
                lines.append(f"    {key_style}  {label}")
                lines.append(f"        {desc}")
            else:
                lines.append(f"    {key_style}  {label}")

        lines.append("")
        lines.append(style("  " + divider_char * (width - 4), Style.DIM))
        lines.append("")

        return "\n".join(lines)

    def show(self, clear: bool = False) -> Optional[MenuItem]:
        """Display the menu and get user selection."""
        if clear:
            clear_screen()

        print(self.render())

        valid_keys = {item.key.lower() for item in self.items}

        while True:
            try:
                prompt = style("  Enter choice: ", Style.BOLD)
                choice = input(prompt).strip().lower()

                if choice in valid_keys:
                    for item in self.items:
                        if item.key.lower() == choice:
                            return item
                else:
                    print(style(f"    Invalid choice '{choice}'. Please try again.", Style.RED))
            except (KeyboardInterrupt, EOFError):
                print()
                return None

    def run(self, clear: bool = True) -> Any:
        """Run the menu loop, executing actions."""
        while True:
            item = self.show(clear=clear)

            if item is None:
                return None

            if item.submenu:
                result = item.submenu.run(clear=clear)
                if result == "back":
                    continue
                return result
            elif item.action:
                return item.action()
            else:
                return item.key


def prompt_path(
    message: str,
    default: Optional[Path] = None,
    must_exist: bool = False,
    is_dir: bool = False,
) -> Optional[Path]:
    """Prompt user for a file/directory path.

    Args:
        message: Prompt message to display
        default: Default value if user presses enter
        must_exist: If True, path must exist
        is_dir: If True, path must be a directory

    Returns:
        Path object or None if cancelled
    """
    default_str = f" [{default}]" if default else ""
    prompt = style(f"  {message}{default_str}: ", Style.BOLD)

    while True:
        try:
            value = input(prompt).strip()

            if not value and default:
                return default

            if not value:
                print(style("    Path is required.", Style.RED))
                continue

            path = Path(value).expanduser().resolve()

            if must_exist and not path.exists():
                print(style(f"    Path does not exist: {path}", Style.RED))
                continue

            if is_dir and path.exists() and not path.is_dir():
                print(style(f"    Path is not a directory: {path}", Style.RED))
                continue

            return path

        except (KeyboardInterrupt, EOFError):
            print()
            return None


def prompt_choice(
    message: str,
    choices: List[str],
    default: Optional[str] = None,
) -> Optional[str]:
    """Prompt user to select from a list of choices.

    Args:
        message: Prompt message
        choices: List of valid choices
        default: Default choice

    Returns:
        Selected choice or None if cancelled
    """
    choices_str = "/".join(choices)
    default_str = f" [{default}]" if default else ""
    prompt = style(f"  {message} ({choices_str}){default_str}: ", Style.BOLD)

    while True:
        try:
            value = input(prompt).strip().lower()

            if not value and default:
                return default

            if value in [c.lower() for c in choices]:
                return value

            print(style(f"    Please choose from: {choices_str}", Style.RED))

        except (KeyboardInterrupt, EOFError):
            print()
            return None


def prompt_confirm(message: str, default: bool = True) -> bool:
    """Prompt user for yes/no confirmation.

    Args:
        message: Prompt message
        default: Default value

    Returns:
        True for yes, False for no
    """
    suffix = "[Y/n]" if default else "[y/N]"
    prompt = style(f"  {message} {suffix}: ", Style.BOLD)

    try:
        value = input(prompt).strip().lower()

        if not value:
            return default

        return value in ("y", "yes", "true", "1")

    except (KeyboardInterrupt, EOFError):
        print()
        return False


def prompt_number(
    message: str,
    default: Optional[int] = None,
    min_val: Optional[int] = None,
    max_val: Optional[int] = None,
) -> Optional[int]:
    """Prompt user for a number.

    Args:
        message: Prompt message
        default: Default value
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Integer or None if cancelled
    """
    default_str = f" [{default}]" if default is not None else ""
    range_str = ""
    if min_val is not None and max_val is not None:
        range_str = f" ({min_val}-{max_val})"
    elif min_val is not None:
        range_str = f" (min: {min_val})"
    elif max_val is not None:
        range_str = f" (max: {max_val})"

    prompt = style(f"  {message}{range_str}{default_str}: ", Style.BOLD)

    while True:
        try:
            value = input(prompt).strip()

            if not value and default is not None:
                return default

            if not value:
                print(style("    A number is required.", Style.RED))
                continue

            try:
                num = int(value)
            except ValueError:
                print(style("    Please enter a valid integer.", Style.RED))
                continue

            if min_val is not None and num < min_val:
                print(style(f"    Value must be at least {min_val}.", Style.RED))
                continue

            if max_val is not None and num > max_val:
                print(style(f"    Value must be at most {max_val}.", Style.RED))
                continue

            return num

        except (KeyboardInterrupt, EOFError):
            print()
            return None


class HelpFormatter:
    """Professional help text formatter for CLI tools.

    Usage:
        help = HelpFormatter(
            name="scholawrite-ingest",
            version="augmented",
            description="Ingest and normalize ScholaWrite seed data.",
            usage="scholawrite-ingest [OPTIONS]",
        )
        help.add_argument("-i", "--input", "PATH", "Input directory", required=True)
        help.add_argument("-o", "--output", "PATH", "Output JSONL file", required=True)
        help.add_option("-v", "--verbose", "Enable verbose output")
        help.add_example("scholawrite-ingest -i data/raw -o data/normalized.jsonl")
        print(help.format())
    """

    def __init__(
        self,
        name: str,
        version: str,
        description: str,
        usage: str = "",
    ):
        self.name = name
        self.version = version
        self.description = description
        self.usage = usage or f"{name} [OPTIONS]"
        self.arguments: List[dict] = []
        self.options: List[dict] = []
        self.examples: List[dict] = []
        self.notes: List[str] = []

    def add_argument(
        self,
        short: str,
        long: str,
        metavar: str,
        description: str,
        required: bool = False,
        default: Optional[str] = None,
    ) -> "HelpFormatter":
        """Add an argument with value."""
        self.arguments.append({
            "short": short,
            "long": long,
            "metavar": metavar,
            "description": description,
            "required": required,
            "default": default,
        })
        return self

    def add_option(
        self,
        short: str,
        long: str,
        description: str,
    ) -> "HelpFormatter":
        """Add a boolean flag option."""
        self.options.append({
            "short": short,
            "long": long,
            "description": description,
        })
        return self

    def add_example(self, example: str, description: str = "") -> "HelpFormatter":
        """Add a usage example."""
        self.examples.append({"command": example, "description": description})
        return self

    def add_note(self, note: str) -> "HelpFormatter":
        """Add a note to the help text."""
        self.notes.append(note)
        return self

    def format(self) -> str:
        """Format the complete help text."""
        lines = []

        # Header
        lines.append("")
        lines.append(
            style(f"  {self.name}", Style.BOLD, Style.CYAN) +
            style(f" v{self.version}", Style.DIM)
        )
        lines.append(f"  {self.description}")
        lines.append("")

        # Usage
        lines.append(style("  USAGE", Style.BOLD, Style.YELLOW))
        lines.append(f"      {self.usage}")
        lines.append("")

        # Arguments
        if self.arguments:
            lines.append(style("  ARGUMENTS", Style.BOLD, Style.YELLOW))
            for arg in self.arguments:
                flags = f"{arg['short']}, {arg['long']} {arg['metavar']}"
                req = style(" (required)", Style.RED) if arg["required"] else ""
                default = (
                    style(f" [default: {arg['default']}]", Style.DIM)
                    if arg["default"] else ""
                )
                lines.append(f"      {style(flags, Style.GREEN)}{req}")
                lines.append(f"          {arg['description']}{default}")
            lines.append("")

        # Options
        if self.options:
            lines.append(style("  OPTIONS", Style.BOLD, Style.YELLOW))
            for opt in self.options:
                flags = f"{opt['short']}, {opt['long']}"
                lines.append(f"      {style(flags, Style.GREEN)}")
                lines.append(f"          {opt['description']}")
            lines.append("")

        # Examples
        if self.examples:
            lines.append(style("  EXAMPLES", Style.BOLD, Style.YELLOW))
            for ex in self.examples:
                if ex["description"]:
                    lines.append(f"      # {ex['description']}")
                lines.append(f"      {style(ex['command'], Style.CYAN)}")
                lines.append("")

        # Notes
        if self.notes:
            lines.append(style("  NOTES", Style.BOLD, Style.YELLOW))
            for note in self.notes:
                lines.append(f"      {note}")
            lines.append("")

        return "\n".join(lines)


def section(title: str) -> None:
    """Print a section divider."""
    width, _ = get_terminal_size()
    line_width = min(70, width - 4)
    divider_char = "─" if _HAS_UTF8 else "-"
    print()
    print(style(f"  {divider_char * line_width}", Style.DIM))
    print(style(f"  {title}", Style.BOLD))
    print(style(f"  {divider_char * line_width}", Style.DIM))
    print()


def divider() -> None:
    """Print a simple divider line."""
    width, _ = get_terminal_size()
    line_width = min(70, width - 4)
    divider_char = "─" if _HAS_UTF8 else "-"
    print(style(f"  {divider_char * line_width}", Style.DIM))
