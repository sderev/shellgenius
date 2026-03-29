from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from pygments import lex
from pygments.lexers import BashLexer
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
from rich.console import Console, Group
from rich.errors import StyleSyntaxError
from rich.markdown import Markdown
from rich.padding import Padding
from rich.style import Style
from rich.syntax import PygmentsSyntaxTheme
from rich.text import Text
from rich.theme import Theme

from .response_parser import (
    ParsedShellResponse,
    ShellGeniusResponseError,
    parse_shellgenius_response,
)

# ---------------------------------------------------------------------------
# Built-in custom code-block themes
# ---------------------------------------------------------------------------


class AlabasterStyle(_PygmentsStyle):
    """Light Pygments style derived from sderev/alabaster.vim.

    Color palette: https://github.com/sderev/alabaster.vim
    """

    name = "alabaster"
    background_color = "#f8f8f8"

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


class AlabasterShellGeniusStyle(_PygmentsStyle):
    """Demo-friendly light style with more visible shell-command coloring."""

    name = "alabaster-shellgenius"
    background_color = "#ececec"

    styles = {
        Token: "#000000",
        Token.Text: "#000000",
        Comment: "#aa3731",
        Comment.Preproc: "#aa3731",
        String: "#448c27",
        Number: "#7a3e9d",
        Keyword: "#7a3e9d",
        Keyword.Type: "#000000",
        Name: "#325cc0",
        Name.Function: "#325cc0",
        Name.Class: "#325cc0",
        Name.Decorator: "#325cc0",
        Name.Tag: "#007acc",
        Name.Attribute: "#325cc0",
        Name.Builtin: "#325cc0",
        Name.Variable: "#7a3e9d",
        Operator: "#000000",
        Punctuation: "#777777",
        Generic.Heading: "#325cc0",
        Generic.Subheading: "#325cc0",
        Generic.Deleted: "#aa3731",
        Generic.Inserted: "#448c27",
        Generic.Error: "#aa3731",
        Generic.Emph: "italic",
        Generic.Strong: "bold",
        Error: "#aa3731",
    }


_CUSTOM_CODE_THEMES: dict[str, type[_PygmentsStyle]] = {
    "alabaster": AlabasterStyle,
    "alabaster-shellgenius": AlabasterShellGeniusStyle,
}

_SHELLGENIUS_THEME_STYLES: dict[str, dict[str, str]] = {
    "default": {},
    "alabaster": {
        "markdown.h1": "bold #325cc0",
        "markdown.h2": "bold #7a3e9d",
        "markdown.h3": "bold #448c27",
        "markdown.item.bullet": "#ffbc5d",
        "markdown.link": "#325cc0",
        "markdown.link_url": "underline #325cc0",
        "markdown.hr": "#c7c7c7",
        "status.spinner": "#325cc0",
    },
    "alabaster-shellgenius": {
        "markdown.h1": "bold #005faf",
        "markdown.h2": "bold #5f00d7",
        "markdown.h3": "bold #008700",
        "markdown.item.bullet": "#d70000",
        "markdown.link": "#005faf",
        "markdown.link_url": "underline #005faf",
        "markdown.hr": "#c5cbd3",
        "status.spinner": "#008700",
    },
}

_SHELLGENIUS_COMMAND_BLOCK_STYLES: dict[str, str] = {
    "alabaster": f"on {AlabasterStyle.background_color}",
    "alabaster-shellgenius": f"on {AlabasterShellGeniusStyle.background_color}",
}


# ---------------------------------------------------------------------------
# Config loading & validation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LmtTheme:
    code_block_theme: str | None = None
    inline_code_theme: str | None = None
    rich_styles: dict[str, str] = field(default_factory=dict)
    shellgenius_theme: str | None = None
    shellgenius_code_block_theme: str | None = None
    shellgenius_command_block_style: str | None = None

    @property
    def resolved_code_block_theme(self) -> str | None:
        return self.shellgenius_code_block_theme or self.code_block_theme

    @property
    def uses_shellgenius_command_renderer(self) -> bool:
        return self.shellgenius_command_block_style is not None

    @property
    def console_styles(self) -> dict[str, str]:
        styles = dict(self.rich_styles)
        if self.inline_code_theme and "markdown.code" not in styles:
            styles["markdown.code"] = self.inline_code_theme
        return styles


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


def _validated_shellgenius_theme(value: str | None) -> str | None:
    if value == "default":
        return value

    return _validated_code_block_theme(value)


def _validated_style_overrides(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}

    overrides: dict[str, str] = {}
    for style_name, style_value in value.items():
        if not isinstance(style_name, str) or not isinstance(style_value, str):
            continue
        if _validated_inline_code_theme(style_value) is None:
            continue
        overrides[style_name] = style_value
    return overrides


def _merge_theme(base: LmtTheme, overlay: LmtTheme) -> LmtTheme:
    return LmtTheme(
        code_block_theme=overlay.code_block_theme or base.code_block_theme,
        inline_code_theme=overlay.inline_code_theme or base.inline_code_theme,
        rich_styles={**base.rich_styles, **overlay.rich_styles},
        shellgenius_theme=overlay.shellgenius_theme or base.shellgenius_theme,
        shellgenius_code_block_theme=(
            overlay.shellgenius_code_block_theme or base.shellgenius_code_block_theme
        ),
        shellgenius_command_block_style=(
            overlay.shellgenius_command_block_style or base.shellgenius_command_block_style
        ),
    )


def _theme_from_preset(name: str | None) -> LmtTheme:
    validated_name = _validated_shellgenius_theme(name)
    if validated_name is None:
        return LmtTheme()

    return LmtTheme(
        shellgenius_theme=validated_name,
        shellgenius_code_block_theme=None if validated_name == "default" else validated_name,
        rich_styles=dict(_SHELLGENIUS_THEME_STYLES.get(validated_name, {})),
        shellgenius_command_block_style=_SHELLGENIUS_COMMAND_BLOCK_STYLES.get(validated_name),
    )


def _legacy_shellgenius_theme(code_block_theme: str | None) -> LmtTheme:
    if code_block_theme != "alabaster-shellgenius":
        return LmtTheme()

    return _theme_from_preset(code_block_theme)


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
    if not isinstance(data, dict):
        return LmtTheme()

    theme = LmtTheme(
        code_block_theme=_validated_code_block_theme(
            _validated_theme_value(data, "code_block_theme")
        ),
        inline_code_theme=_validated_inline_code_theme(
            _validated_theme_value(data, "inline_code_theme")
        ),
    )

    shellgenius_config = data.get("shellgenius")
    if not isinstance(shellgenius_config, dict):
        return _merge_theme(theme, _legacy_shellgenius_theme(theme.code_block_theme))

    shellgenius_theme = _theme_from_preset(_validated_theme_value(shellgenius_config, "theme"))
    if shellgenius_theme.shellgenius_theme is None:
        shellgenius_theme = _legacy_shellgenius_theme(theme.code_block_theme)

    theme = _merge_theme(theme, shellgenius_theme)
    return _merge_theme(
        theme,
        LmtTheme(
            rich_styles=_validated_style_overrides(shellgenius_config.get("styles")),
        ),
    )


def make_console(theme: LmtTheme) -> Console:
    if theme.console_styles:
        return Console(theme=Theme(theme.console_styles))
    return Console()


def make_markdown(text: str, theme: LmtTheme) -> Markdown:
    kwargs = {}

    code_block_theme = theme.resolved_code_block_theme
    if code_block_theme:
        kwargs["code_theme"] = _resolve_code_theme(code_block_theme)

    return Markdown(text, **kwargs)


def make_renderable(text: str, theme: LmtTheme):
    parsed_response = _parse_shell_response_for_demo(text, theme)
    if parsed_response is None:
        return make_markdown(text, theme)

    renderables = [
        Padding(
            _make_shell_command_block(parsed_response.command),
            (1, 1),
            style=_command_block_style(theme),
        )
    ]
    if parsed_response.explanation:
        renderables.append(Text())
        renderables.append(make_markdown(f"Explanation:\n{parsed_response.explanation}", theme))
    return Group(*renderables)


def _parse_shell_response_for_demo(text: str, theme: LmtTheme) -> ParsedShellResponse | None:
    if not theme.uses_shellgenius_command_renderer:
        return None

    try:
        return parse_shellgenius_response(text)
    except ShellGeniusResponseError:
        return None


def _make_shell_command_block(command: str) -> Text:
    text = Text(no_wrap=False)
    parameter_expansion_depth = 0

    for token, value in lex(command, BashLexer()):
        if not value:
            continue

        if token in Token.Text.Whitespace:
            text.append(value)
            continue

        style = _style_for_shell_token(
            token,
            value,
            in_parameter_expansion=parameter_expansion_depth > 0,
        )
        text.append(value, style=style)

        if token in String.Interpol:
            if value == "${":
                parameter_expansion_depth += 1
            elif value == "}":
                parameter_expansion_depth = max(0, parameter_expansion_depth - 1)

    text.rstrip()
    return text


def _command_block_style(theme: LmtTheme) -> str:
    override = theme.rich_styles.get("markdown.code_block")
    if override:
        return override

    return (
        theme.shellgenius_command_block_style or f"on {AlabasterShellGeniusStyle.background_color}"
    )


def _style_for_shell_token(token, value: str, *, in_parameter_expansion: bool) -> str:
    if token in Comment:
        return "#aa3731"
    if token in String.Interpol:
        return "#000000"
    if token in String:
        return "#448c27"
    if token in Number:
        return "#7a3e9d"
    if token in Name.Function:
        return "#325cc0"
    if token in Name.Variable:
        if in_parameter_expansion or value.startswith("$"):
            return "#000000"
        return "#325cc0"
    if token in Punctuation:
        return "#777777"
    return "#000000"
