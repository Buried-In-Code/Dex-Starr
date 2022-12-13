__all__ = ["CONSOLE", "create_menu"]

from typing import List, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt
from rich.theme import Theme

CONSOLE = Console(
    theme=Theme(
        {
            "prompt": "green",
            "prompt.border": "dim green",
            "prompt.choices": "white",
            "prompt.default": "dim white",
            "title": "magenta",
            "title.border": "dim magenta",
            "subtitle": "blue",
            "subtitle.border": "dim blue",
            "syntax.border": "dim cyan",
            "logging.level.debug": "dim white",
            "logging.level.info": "white",
            "logging.level.warning": "yellow",
            "logging.level.error": "bold red",
            "logging.level.critical": "bold magenta",
        }
    )
)


def create_menu(options: List[str], prompt: str, default: Optional[str] = None) -> Optional[int]:
    if not options:
        return 0
    panel_text = []
    for index, item in enumerate(options):
        panel_text.append(f"[prompt]{index + 1}:[/] [prompt.choices]{item}[/]")
    if default:
        panel_text.append(f"[prompt]0:[/] [prompt.default]{default}[/]")
    CONSOLE.print(Panel.fit("\n".join(panel_text), box=box.SQUARE, border_style="prompt.border"))
    selected = IntPrompt.ask(prompt=prompt, default=0 if default else None, console=CONSOLE)
    if (
        selected is None
        or selected < 0
        or selected > len(options)
        or (selected == 0 and not default)
    ):
        CONSOLE.print(f"Invalid Option: `{selected}`", style="prompt.invalid")
        return create_menu(options=options, prompt=prompt, default=default)
    return selected
