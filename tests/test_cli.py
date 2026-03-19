from contextlib import nullcontext

import shellgenius.cli as cli_module
from click.testing import CliRunner


class DummyLive:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def update(self, _renderable):
        return None


def test_shellgenius_executes_parsed_command(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(cli_module, "live", DummyLive())
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (
            "```sh\nprintf 'ok'\n```\n\nExplanation:\n* Prints ok.",
            0,
            object(),
        ),
    )
    monkeypatch.setattr(
        cli_module.subprocess,
        "run",
        lambda cmd, shell, check: calls.append((cmd, shell, check)) or nullcontext(),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"], input="y\n")

    assert result.exit_code == 0
    assert calls == [("printf 'ok'", True, True)]


def test_shellgenius_reports_missing_command_when_response_is_malformed(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(cli_module, "live", DummyLive())
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: ("Here is your command: ls", 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["list", "files"], input="y\n")

    assert result.exit_code == 0
    assert "No command found" in result.output
