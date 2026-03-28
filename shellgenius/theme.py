from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pygments.styles import get_style_by_name
from pygments.util import ClassNotFound
from rich.console import Console
from rich.errors import StyleSyntaxError
from rich.markdown import Markdown
from rich.style import Style
from rich.theme import Theme

# ---------------------------------------------------------------------------
# Config loading & validation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LmtTheme:
    code_block_theme: str | None = None
    inline_code_theme: str | None = None


def _validated_theme_value(config: object, key: str) -> str | None:
    if not isinstance(config, dict):
        return None

    value = config.get(key)
    return value if isinstance(value, str) else None


def _validated_code_block_theme(value: str | None) -> str | None:
    if value is None:
        return None

    try:
        get_style_by_name(value)
    except ClassNotFound:
        return None
    return value


def _validated_inline_code_theme(value: str | None) -> str | None:
    if value is None:
        return None

    try:
        Style.parse(value)
    except StyleSyntaxError:
        return None
    return value


def load_lmt_theme() -> LmtTheme:
    config_path = Path.home() / ".config" / "lmt" / "config.json"
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError, OSError):
        return LmtTheme()
    return LmtTheme(
        code_block_theme=_validated_code_block_theme(
            _validated_theme_value(data, "code_block_theme")
        ),
        inline_code_theme=_validated_inline_code_theme(
            _validated_theme_value(data, "inline_code_theme")
        ),
    )


def make_console(theme: LmtTheme) -> Console:
    if theme.inline_code_theme:
        return Console(theme=Theme({"markdown.code": theme.inline_code_theme}))
    return Console()


def make_markdown(text: str, theme: LmtTheme) -> Markdown:
    if theme.code_block_theme:
        return Markdown(text, code_theme=theme.code_block_theme)
    return Markdown(text)
