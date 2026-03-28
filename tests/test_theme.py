import json

from rich.console import Console
from rich.theme import Theme

import shellgenius.theme as theme_module
from shellgenius.theme import (
    AlabasterStyle,
    LmtTheme,
    _make_shell_command_block,
    load_lmt_theme,
    make_console,
    make_markdown,
)


def _style_for_segment(renderable, theme: LmtTheme, text: str) -> str | None:
    console = make_console(theme)

    for segment in console.render(renderable):
        if segment.text == text and segment.style is not None:
            return str(segment.style)

    return None


def _render_text(renderable, theme: LmtTheme, *, width: int = 80) -> str:
    console_kwargs = {"width": width, "record": True, "force_terminal": False}
    if theme.console_styles:
        console_kwargs["theme"] = Theme(theme.console_styles)

    console = Console(**console_kwargs)
    console.print(renderable)
    return console.export_text(clear=False)


def _styled_spans(text) -> list[tuple[str, str | None]]:
    return [
        (
            text.plain[span.start : span.end],
            str(span.style) if span.style is not None else None,
        )
        for span in text.spans
    ]


# -- load_lmt_theme -----------------------------------------------------------


def test_load_lmt_theme_returns_values_from_config(tmp_path, monkeypatch):
    config_dir = tmp_path / ".config" / "lmt"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(
        json.dumps({"code_block_theme": "monokai", "inline_code_theme": "blue on black"})
    )
    monkeypatch.setattr(theme_module.Path, "home", staticmethod(lambda: tmp_path))

    theme = load_lmt_theme()

    assert theme.code_block_theme == "monokai"
    assert theme.inline_code_theme == "blue on black"
    assert theme.rich_styles == {}


def test_load_lmt_theme_returns_empty_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(theme_module.Path, "home", staticmethod(lambda: tmp_path))

    theme = load_lmt_theme()

    assert theme == LmtTheme()


def test_load_lmt_theme_returns_empty_on_invalid_json(tmp_path, monkeypatch):
    config_dir = tmp_path / ".config" / "lmt"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text("{not valid json")
    monkeypatch.setattr(theme_module.Path, "home", staticmethod(lambda: tmp_path))

    theme = load_lmt_theme()

    assert theme == LmtTheme()


def test_load_lmt_theme_returns_empty_on_invalid_utf8(tmp_path, monkeypatch):
    config_dir = tmp_path / ".config" / "lmt"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_bytes(b"\xff")
    monkeypatch.setattr(theme_module.Path, "home", staticmethod(lambda: tmp_path))

    theme = load_lmt_theme()

    assert theme == LmtTheme()


def test_load_lmt_theme_returns_empty_on_wrong_top_level_type(tmp_path, monkeypatch):
    config_dir = tmp_path / ".config" / "lmt"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(json.dumps([]))
    monkeypatch.setattr(theme_module.Path, "home", staticmethod(lambda: tmp_path))

    theme = load_lmt_theme()

    assert theme == LmtTheme()


def test_load_lmt_theme_tolerates_missing_keys(tmp_path, monkeypatch):
    config_dir = tmp_path / ".config" / "lmt"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(json.dumps({"code_block_theme": "zenburn"}))
    monkeypatch.setattr(theme_module.Path, "home", staticmethod(lambda: tmp_path))

    theme = load_lmt_theme()

    assert theme.code_block_theme == "zenburn"
    assert theme.inline_code_theme is None
    assert theme.rich_styles == {}


def test_load_lmt_theme_ignores_unrelated_keys(tmp_path, monkeypatch):
    config_dir = tmp_path / ".config" / "lmt"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(json.dumps({"unrelated_key": "value"}))
    monkeypatch.setattr(theme_module.Path, "home", staticmethod(lambda: tmp_path))

    theme = load_lmt_theme()

    assert theme == LmtTheme()


def test_load_lmt_theme_ignores_invalid_theme_values(tmp_path, monkeypatch):
    config_dir = tmp_path / ".config" / "lmt"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(
        json.dumps({"code_block_theme": [], "inline_code_theme": "not a style"})
    )
    monkeypatch.setattr(theme_module.Path, "home", staticmethod(lambda: tmp_path))

    theme = load_lmt_theme()

    assert theme == LmtTheme()


def test_load_lmt_theme_loads_shellgenius_preset(tmp_path, monkeypatch):
    config_dir = tmp_path / ".config" / "lmt"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(json.dumps({"shellgenius": {"theme": "alabaster"}}))
    monkeypatch.setattr(theme_module.Path, "home", staticmethod(lambda: tmp_path))

    theme = load_lmt_theme()

    assert theme.code_block_theme is None
    assert theme.shellgenius_theme == "alabaster"
    assert theme.resolved_code_block_theme == "alabaster"
    assert theme.uses_shellgenius_command_renderer is True
    assert theme.rich_styles["markdown.h1"] == "bold #325cc0"
    assert theme.rich_styles["markdown.item.bullet"] == "#ffbc5d"
    assert theme.rich_styles["markdown.link_url"] == "underline #325cc0"


def test_load_lmt_theme_shellgenius_theme_accepts_standard_pygments_theme(tmp_path, monkeypatch):
    config_dir = tmp_path / ".config" / "lmt"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(json.dumps({"shellgenius": {"theme": "zenburn"}}))
    monkeypatch.setattr(theme_module.Path, "home", staticmethod(lambda: tmp_path))

    theme = load_lmt_theme()

    assert theme.code_block_theme is None
    assert theme.shellgenius_theme == "zenburn"
    assert theme.resolved_code_block_theme == "zenburn"
    assert theme.uses_shellgenius_command_renderer is False
    assert theme.rich_styles == {}


def test_load_lmt_theme_preserves_shared_code_block_theme_with_shellgenius_preset(
    tmp_path, monkeypatch
):
    config_dir = tmp_path / ".config" / "lmt"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(
        json.dumps(
            {
                "code_block_theme": "zenburn",
                "shellgenius": {"theme": "alabaster"},
            }
        )
    )
    monkeypatch.setattr(theme_module.Path, "home", staticmethod(lambda: tmp_path))

    theme = load_lmt_theme()

    assert theme.code_block_theme == "zenburn"
    assert theme.shellgenius_theme == "alabaster"
    assert theme.resolved_code_block_theme == "alabaster"
    assert theme.uses_shellgenius_command_renderer is True


def test_load_lmt_theme_ignores_invalid_shellgenius_preset(tmp_path, monkeypatch):
    config_dir = tmp_path / ".config" / "lmt"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(
        json.dumps(
            {
                "code_block_theme": "zenburn",
                "shellgenius": {"theme": "definitely-not-real"},
            }
        )
    )
    monkeypatch.setattr(theme_module.Path, "home", staticmethod(lambda: tmp_path))

    theme = load_lmt_theme()

    assert theme.code_block_theme == "zenburn"
    assert theme.shellgenius_theme is None
    assert theme.resolved_code_block_theme == "zenburn"
    assert theme.uses_shellgenius_command_renderer is False
    assert theme.rich_styles == {}


def test_load_lmt_theme_merges_style_overrides_over_preset(tmp_path, monkeypatch):
    config_dir = tmp_path / ".config" / "lmt"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(
        json.dumps(
            {
                "code_block_theme": "alabaster",
                "shellgenius": {
                    "theme": "alabaster",
                    "styles": {
                        "markdown.h1": "bold magenta",
                        "markdown.code_block": "on #f0f0f0",
                    },
                },
            }
        )
    )
    monkeypatch.setattr(theme_module.Path, "home", staticmethod(lambda: tmp_path))

    theme = load_lmt_theme()

    assert theme.code_block_theme == "alabaster"
    assert theme.shellgenius_theme == "alabaster"
    assert theme.resolved_code_block_theme == "alabaster"
    assert theme.uses_shellgenius_command_renderer is True
    assert theme.rich_styles["markdown.h1"] == "bold magenta"
    assert theme.rich_styles["markdown.h2"] == "bold #7a3e9d"
    assert theme.rich_styles["markdown.code_block"] == "on #f0f0f0"


def test_load_lmt_theme_ignores_invalid_style_overrides_individually(tmp_path, monkeypatch):
    config_dir = tmp_path / ".config" / "lmt"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(
        json.dumps(
            {
                "shellgenius": {
                    "styles": {
                        "markdown.h1": "bold blue",
                        "markdown.h2": "not a style",
                        "markdown.hr": 123,
                    }
                }
            }
        )
    )
    monkeypatch.setattr(theme_module.Path, "home", staticmethod(lambda: tmp_path))

    theme = load_lmt_theme()

    assert theme.rich_styles == {"markdown.h1": "bold blue"}


def test_load_lmt_theme_keeps_legacy_top_level_alabaster_shellgenius_behavior(
    tmp_path, monkeypatch
):
    config_dir = tmp_path / ".config" / "lmt"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(
        json.dumps({"code_block_theme": "alabaster-shellgenius"})
    )
    monkeypatch.setattr(theme_module.Path, "home", staticmethod(lambda: tmp_path))

    theme = load_lmt_theme()

    assert theme.code_block_theme == "alabaster-shellgenius"
    assert theme.shellgenius_theme == "alabaster-shellgenius"
    assert theme.resolved_code_block_theme == "alabaster-shellgenius"
    assert theme.uses_shellgenius_command_renderer is True


# -- make_console -------------------------------------------------------------


def test_make_console_applies_rich_style_overrides():
    theme = LmtTheme(rich_styles={"markdown.h1": "bold green"})

    console = make_console(theme)

    assert str(console.get_style("markdown.h1")) == "bold green"


def test_make_console_maps_inline_code_theme_to_markdown_code():
    console = make_console(LmtTheme(inline_code_theme="green on black"))

    assert str(console.get_style("markdown.code")) == "green on black"


def test_make_console_prefers_markdown_code_override_to_inline_code_theme():
    console = make_console(
        LmtTheme(
            inline_code_theme="green on black",
            rich_styles={"markdown.code": "bold blue on #f0f0f0"},
        )
    )

    assert str(console.get_style("markdown.code")) == "bold blue on #f0f0f0"


def test_make_console_returns_default_console_without_styles():
    themed = make_console(LmtTheme(rich_styles={"markdown.h1": "bold green"}))
    plain = make_console(LmtTheme())

    assert str(themed.get_style("markdown.h1")) != str(plain.get_style("markdown.h1"))


# -- make_markdown ------------------------------------------------------------


def test_make_markdown_applies_code_block_theme():
    theme = LmtTheme(code_block_theme="zenburn")

    md = make_markdown("```python\nprint(1)\n```", theme)

    assert md.code_theme == "zenburn"


def test_make_markdown_prefers_shellgenius_code_block_theme():
    theme = LmtTheme(code_block_theme="alabaster", shellgenius_code_block_theme="zenburn")

    md = make_markdown("```python\nprint(1)\n```", theme)

    assert md.code_theme == "zenburn"


def test_make_markdown_applies_inline_code_theme():
    theme = LmtTheme(inline_code_theme="green on black")

    assert (
        _style_for_segment(make_markdown("Use `printf`.", theme), theme, "printf")
        == "green on black"
    )


def test_make_markdown_prefers_markdown_code_override():
    theme = LmtTheme(
        inline_code_theme="green on black",
        rich_styles={"markdown.code": "bold blue on #f0f0f0"},
    )

    assert (
        _style_for_segment(make_markdown("Use `printf`.", theme), theme, "printf")
        == "bold blue on #f0f0f0"
    )


def test_make_markdown_applies_bullet_color_override():
    theme = LmtTheme(rich_styles={"markdown.item.bullet": "#ffbc5d"})

    assert _style_for_segment(make_markdown("* test", theme), theme, " • ") == "#ffbc5d"


def test_make_markdown_uses_default_without_theme():
    theme = LmtTheme()

    md = make_markdown("hello", theme)

    assert md.code_theme == "monokai"  # Rich default
    assert md.inline_code_theme == "monokai"


# -- AlabasterStyle / custom themes ------------------------------------------


def test_alabaster_style_uses_builtin_background():
    assert AlabasterStyle.background_color == "#f8f8f8"


def test_load_lmt_theme_accepts_alabaster(tmp_path, monkeypatch):
    config_dir = tmp_path / ".config" / "lmt"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(json.dumps({"code_block_theme": "alabaster"}))
    monkeypatch.setattr(theme_module.Path, "home", staticmethod(lambda: tmp_path))

    theme = load_lmt_theme()

    assert theme.code_block_theme == "alabaster"


def test_load_lmt_theme_accepts_alabaster_shellgenius(tmp_path, monkeypatch):
    config_dir = tmp_path / ".config" / "lmt"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(
        json.dumps({"code_block_theme": "alabaster-shellgenius"})
    )
    monkeypatch.setattr(theme_module.Path, "home", staticmethod(lambda: tmp_path))

    theme = load_lmt_theme()

    assert theme.code_block_theme == "alabaster-shellgenius"
    assert theme.uses_shellgenius_command_renderer is True


def test_make_markdown_applies_alabaster_theme():
    from rich.syntax import PygmentsSyntaxTheme

    theme = LmtTheme(code_block_theme="alabaster")

    md = make_markdown("```python\nprint(1)\n```", theme)

    assert isinstance(md.code_theme, PygmentsSyntaxTheme)


def test_make_markdown_alabaster_does_not_use_default():
    theme = LmtTheme(code_block_theme="alabaster")

    md = make_markdown("hello", theme)

    assert md.code_theme != "monokai"


def test_make_markdown_applies_alabaster_shellgenius_theme():
    from rich.syntax import PygmentsSyntaxTheme

    theme = LmtTheme(shellgenius_code_block_theme="alabaster-shellgenius")

    md = make_markdown("```bash\nffmpeg -i input.mp4\n```", theme)

    assert isinstance(md.code_theme, PygmentsSyntaxTheme)


def test_make_shell_command_block_drops_lexer_trailing_newline():
    assert _make_shell_command_block("printf 'ok'").plain == "printf 'ok'"


def test_make_shell_command_block_uses_minimal_alabaster_shell_styling():
    styled = _styled_spans(
        _make_shell_command_block('ffmpeg -i video.mp4 -vf "fps=1/5" frame_%04d.jpg')
    )

    assert styled == [
        ("ffmpeg", "#000000"),
        ("-i", "#000000"),
        ("video.mp4", "#000000"),
        ("-vf", "#000000"),
        ('"fps=1/5"', "#448c27"),
        ("frame_%04d.jpg", "#000000"),
    ]
    assert all("bold" not in style for _, style in styled if style is not None)


def test_make_shell_command_block_keeps_parameter_expansions_plain():
    assert _styled_spans(_make_shell_command_block("export PATH=$PATH ${USER}")) == [
        ("export", "#000000"),
        ("PATH", "#325cc0"),
        ("=", "#000000"),
        ("$PATH", "#000000"),
        ("${", "#000000"),
        ("USER", "#000000"),
        ("}", "#000000"),
    ]


def test_make_shell_command_block_uses_plain_red_comments():
    styled = _styled_spans(_make_shell_command_block("printf ok # note"))

    assert styled[-1] == ("# note", "#aa3731")
    assert all("bold" not in style for _, style in styled if style is not None)


def test_make_renderable_uses_shellgenius_command_block_style():
    renderable = make_renderable(
        '```bash\nffmpeg -i "input.mp4"\n```\n\nExplanation:\n* test\n',
        LmtTheme(
            code_block_theme="alabaster",
            shellgenius_theme="alabaster",
            shellgenius_code_block_theme="alabaster",
            shellgenius_command_block_style=f"on {AlabasterStyle.background_color}",
        ),
    )

    assert renderable.renderables[0].style == "on #f8f8f8"


def test_make_renderable_prefers_markdown_code_block_override():
    renderable = make_renderable(
        '```bash\nffmpeg -i "input.mp4"\n```\n\nExplanation:\n* test\n',
        LmtTheme(
            code_block_theme="alabaster",
            shellgenius_theme="alabaster",
            shellgenius_code_block_theme="alabaster",
            shellgenius_command_block_style=f"on {AlabasterStyle.background_color}",
            rich_styles={"markdown.code_block": "on #f0f0f0"},
        ),
    )

    assert renderable.renderables[0].style == "on #f0f0f0"


def test_make_renderable_separates_the_command_block_from_explanation():
    theme = LmtTheme(
        code_block_theme="alabaster",
        shellgenius_theme="alabaster",
        shellgenius_code_block_theme="alabaster",
        shellgenius_command_block_style=f"on {AlabasterStyle.background_color}",
    )

    output = _render_text(
        make_renderable(
            "```bash\nprintf 'ok'\n```\n\nExplanation:\n* test\n",
            theme,
        ),
        theme,
    )

    assert [line.rstrip() for line in output.splitlines()[:7]] == [
        "",
        " printf 'ok'",
        "",
        "",
        "Explanation:",
        "",
        " • test",
    ]
