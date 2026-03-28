import json

import shellgenius.theme as theme_module
from shellgenius.theme import (
    AlabasterStyle,
    LmtTheme,
    load_lmt_theme,
    make_console,
    make_markdown,
)

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


# -- make_console --------------------------------------------------------------


def test_make_console_applies_inline_code_theme():
    theme = LmtTheme(inline_code_theme="green on black")

    console = make_console(theme)

    assert str(console.get_style("markdown.code")) == "green on black"


def test_make_console_returns_default_console_without_theme():
    themed = make_console(LmtTheme(inline_code_theme="green on black"))
    plain = make_console(LmtTheme())

    assert str(themed.get_style("markdown.code")) != str(plain.get_style("markdown.code"))


# -- make_markdown -------------------------------------------------------------


def test_make_markdown_applies_code_block_theme():
    theme = LmtTheme(code_block_theme="zenburn")

    md = make_markdown("```python\nprint(1)\n```", theme)

    assert md.code_theme == "zenburn"


def test_make_markdown_uses_default_without_theme():
    theme = LmtTheme()

    md = make_markdown("hello", theme)

    assert md.code_theme == "monokai"  # Rich default


# -- AlabasterStyle / custom themes -------------------------------------------


def test_alabaster_style_has_light_background():
    assert AlabasterStyle.background_color == "#f0f0f0"


def test_load_lmt_theme_accepts_alabaster(tmp_path, monkeypatch):
    config_dir = tmp_path / ".config" / "lmt"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(json.dumps({"code_block_theme": "alabaster"}))
    monkeypatch.setattr(theme_module.Path, "home", staticmethod(lambda: tmp_path))

    theme = load_lmt_theme()

    assert theme.code_block_theme == "alabaster"


def test_make_markdown_applies_alabaster_theme():
    from rich.syntax import PygmentsSyntaxTheme

    theme = LmtTheme(code_block_theme="alabaster")

    md = make_markdown("```python\nprint(1)\n```", theme)

    assert isinstance(md.code_theme, PygmentsSyntaxTheme)


def test_make_markdown_alabaster_does_not_use_default():
    theme = LmtTheme(code_block_theme="alabaster")

    md = make_markdown("hello", theme)

    assert md.code_theme != "monokai"
