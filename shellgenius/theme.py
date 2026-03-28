from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pygments.style import Style as _PygmentsStyle
from pygments.styles import get_style_by_name
from pygments.token import (
    Comment,
    Error,
    Generic,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Token,
)
from pygments.util import ClassNotFound
from rich.console import Console
from rich.errors import StyleSyntaxError
from rich.markdown import Markdown
from rich.style import Style
from rich.syntax import PygmentsSyntaxTheme
from rich.theme import Theme

# ---------------------------------------------------------------------------
# Built-in custom code-block themes
# ---------------------------------------------------------------------------


class AlabasterStyle(_PygmentsStyle):
    """Light Pygments style derived from sderev/alabaster.vim.

    Color palette: https://github.com/sderev/alabaster.vim
    """

    name = "alabaster"
    background_color = "#f0f0f0"

    styles = {
        Token: "#000000",
        Comment: "#aa3731",
        Comment.Preproc: "#aa3731",
        String: "#448C27",
        Number: "#7a3e9d",
        Keyword: "#7a3e9d",
        Keyword.Type: "#000000",
        Name.Function: "#325cc0",
        Name.Class: "#325cc0",
        Name.Decorator: "#325cc0",
        Name.Tag: "#007acc",
        Name.Attribute: "#325cc0",
        Name.Builtin: "#000000",
        Operator: "#000000",
        Punctuation: "#777777",
        Generic.Heading: "#325cc0",
        Generic.Subheading: "#325cc0",
        Generic.Deleted: "#aa3731",
        Generic.Inserted: "#448C27",
        Generic.Error: "#aa3731",
        Generic.Emph: "italic",
        Generic.Strong: "bold",
        Error: "#aa3731",
    }


_CUSTOM_CODE_THEMES: dict[str, type[_PygmentsStyle]] = {
    "alabaster": AlabasterStyle,
}


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

    if value in _CUSTOM_CODE_THEMES:
        return value

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


def _resolve_code_theme(name: str) -> str | PygmentsSyntaxTheme:
    """Return a value suitable for ``Markdown(code_theme=...)``."""
    custom = _CUSTOM_CODE_THEMES.get(name)
    if custom is not None:
        return PygmentsSyntaxTheme(custom)
    return name


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
        return Markdown(text, code_theme=_resolve_code_theme(theme.code_block_theme))
    return Markdown(text)
