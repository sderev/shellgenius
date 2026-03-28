import stat

from click.testing import CliRunner

import shellgenius.api_key as api_key_module
import shellgenius.cli as cli_module

# -- _parse_key_file ----------------------------------------------------------


def test_parse_key_file_with_assignment(tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text("OPENAI_API_KEY=sk-test123\n")
    assert api_key_module._parse_key_file(key_file) == "sk-test123"


def test_parse_key_file_with_export(tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text("export OPENAI_API_KEY=sk-test456\n")
    assert api_key_module._parse_key_file(key_file) == "sk-test456"


def test_parse_key_file_with_bare_key(tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text("sk-barekey789\n")
    assert api_key_module._parse_key_file(key_file) == "sk-barekey789"


def test_parse_key_file_with_quoted_value(tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text('OPENAI_API_KEY="sk-quoted"\n')
    assert api_key_module._parse_key_file(key_file) == "sk-quoted"


def test_parse_key_file_with_single_quoted_value(tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text("OPENAI_API_KEY='sk-single'\n")
    assert api_key_module._parse_key_file(key_file) == "sk-single"


def test_parse_key_file_skips_comments(tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text("# comment\nOPENAI_API_KEY=sk-after-comment\n")
    assert api_key_module._parse_key_file(key_file) == "sk-after-comment"


def test_parse_key_file_ignores_other_assignments_before_key(tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text("export PATH=/usr/bin\nOPENAI_API_KEY=sk-after-path\n")
    assert api_key_module._parse_key_file(key_file) == "sk-after-path"


def test_parse_key_file_rejects_non_key_assignment_as_bare_key(tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text("export PATH=/usr/bin\n")
    assert api_key_module._parse_key_file(key_file) == ""


def test_parse_key_file_rejects_malformed_export_key_line(tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text("export OPENAI_API_KEY\n")
    assert api_key_module._parse_key_file(key_file) == ""


def test_parse_key_file_rejects_bare_key_variable_name(tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text("OPENAI_API_KEY\n")
    assert api_key_module._parse_key_file(key_file) == ""


def test_parse_key_file_rejects_bare_key_when_file_has_other_content(tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text("export PATH=/usr/bin\nsk-barekey789\n")
    assert api_key_module._parse_key_file(key_file) == ""


def test_parse_key_file_empty(tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text("")
    assert api_key_module._parse_key_file(key_file) == ""


def test_parse_key_file_missing(tmp_path):
    key_file = tmp_path / "no-such-file.env"
    assert api_key_module._parse_key_file(key_file) == ""


def test_parse_key_file_returns_empty_on_invalid_utf8(tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_bytes(b"\xff")
    assert api_key_module._parse_key_file(key_file) == ""


# -- get_api_key ---------------------------------------------------------------


def test_get_api_key_prefers_env_var(monkeypatch, tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text("OPENAI_API_KEY=sk-from-file\n")
    monkeypatch.setattr(api_key_module, "KEY_FILE_PATH", key_file)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    assert api_key_module.get_api_key() == "sk-from-env"


def test_get_api_key_falls_back_to_file(monkeypatch, tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text("OPENAI_API_KEY=sk-from-file\n")
    monkeypatch.setattr(api_key_module, "KEY_FILE_PATH", key_file)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert api_key_module.get_api_key() == "sk-from-file"


def test_get_api_key_returns_empty_when_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(api_key_module, "KEY_FILE_PATH", tmp_path / "nope.env")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert api_key_module.get_api_key() == ""


def test_get_api_key_returns_empty_on_invalid_utf8(monkeypatch, tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_bytes(b"\xff")
    monkeypatch.setattr(api_key_module, "KEY_FILE_PATH", key_file)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert api_key_module.get_api_key() == ""


# -- _write_key ----------------------------------------------------------------


def test_write_key_creates_file_with_600_perms(monkeypatch, tmp_path):
    key_file = tmp_path / "config" / "lmt" / "key.env"
    monkeypatch.setattr(api_key_module, "KEY_FILE_PATH", key_file)
    api_key_module._write_key("sk-written")
    assert key_file.read_text() == "OPENAI_API_KEY=sk-written\n"
    mode = key_file.stat().st_mode
    assert mode & 0o777 == stat.S_IRUSR | stat.S_IWUSR  # 0o600


# -- CLI: shellgenius key set --------------------------------------------------


def test_key_set_prompts_and_writes(monkeypatch, tmp_path):
    key_file = tmp_path / "key.env"
    monkeypatch.setattr(api_key_module, "KEY_FILE_PATH", key_file)

    runner = CliRunner()
    result = runner.invoke(cli_module.shellgenius, ["key", "set"], input="sk-new\n")

    assert result.exit_code == 0
    assert "Success!" in result.output
    assert key_file.read_text() == "OPENAI_API_KEY=sk-new\n"


def test_key_set_rejects_if_exists(monkeypatch, tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text("OPENAI_API_KEY=sk-existing\n")
    monkeypatch.setattr(api_key_module, "KEY_FILE_PATH", key_file)

    runner = CliRunner()
    result = runner.invoke(cli_module.shellgenius, ["key", "set"])

    assert result.exit_code != 0
    assert "already exists" in result.output


def test_key_set_does_not_treat_other_assignments_as_existing_key(monkeypatch, tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text("export PATH=/usr/bin\n")
    monkeypatch.setattr(api_key_module, "KEY_FILE_PATH", key_file)

    runner = CliRunner()
    result = runner.invoke(cli_module.shellgenius, ["key", "set"], input="sk-new\n")

    assert result.exit_code == 0
    assert "Success!" in result.output
    assert key_file.read_text() == "OPENAI_API_KEY=sk-new\n"


def test_key_set_ignores_malformed_export_key_line(monkeypatch, tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text("export OPENAI_API_KEY\n")
    monkeypatch.setattr(api_key_module, "KEY_FILE_PATH", key_file)

    runner = CliRunner()
    result = runner.invoke(cli_module.shellgenius, ["key", "set"], input="sk-new\n")

    assert result.exit_code == 0
    assert "Success!" in result.output
    assert key_file.read_text() == "OPENAI_API_KEY=sk-new\n"


def test_key_set_ignores_bare_key_variable_name(monkeypatch, tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text("OPENAI_API_KEY\n")
    monkeypatch.setattr(api_key_module, "KEY_FILE_PATH", key_file)

    runner = CliRunner()
    result = runner.invoke(cli_module.shellgenius, ["key", "set"], input="sk-new\n")

    assert result.exit_code == 0
    assert "Success!" in result.output
    assert key_file.read_text() == "OPENAI_API_KEY=sk-new\n"


# -- CLI: shellgenius key edit -------------------------------------------------


def test_key_edit_updates_key(monkeypatch, tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text("OPENAI_API_KEY=sk-old\n")
    monkeypatch.setattr(api_key_module, "KEY_FILE_PATH", key_file)

    runner = CliRunner()
    result = runner.invoke(cli_module.shellgenius, ["key", "edit"], input="sk-updated\n")

    assert result.exit_code == 0
    assert "updated" in result.output
    assert key_file.read_text() == "OPENAI_API_KEY=sk-updated\n"


def test_key_edit_no_change(monkeypatch, tmp_path):
    key_file = tmp_path / "key.env"
    key_file.write_text("OPENAI_API_KEY=sk-same\n")
    monkeypatch.setattr(api_key_module, "KEY_FILE_PATH", key_file)

    runner = CliRunner()
    result = runner.invoke(cli_module.shellgenius, ["key", "edit"], input="sk-same\n")

    assert result.exit_code == 0
    assert "No changes" in result.output


def test_key_edit_falls_back_to_set_when_empty(monkeypatch, tmp_path):
    key_file = tmp_path / "key.env"
    monkeypatch.setattr(api_key_module, "KEY_FILE_PATH", key_file)

    runner = CliRunner()
    result = runner.invoke(cli_module.shellgenius, ["key", "edit"], input="sk-fresh\n")

    assert result.exit_code == 0
    assert "No API key found" in result.output
    assert "Success!" in result.output


# -- CLI: help lists key command -----------------------------------------------


def test_shellgenius_help_lists_key_command():
    runner = CliRunner()
    result = runner.invoke(cli_module.shellgenius, ["--help"])
    assert result.exit_code == 0
    assert "key" in result.output
