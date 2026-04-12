import os
import subprocess
import sys
import time
import types
from types import SimpleNamespace

import httpx
import pytest
from click.testing import CliRunner
from openai import RateLimitError

import shellgenius._entrypoint as entrypoint_module
import shellgenius.cli as cli_module
from shellgenius.theme import LmtTheme


class DummyLive:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def update(self, _renderable):
        return None


def response_text():
    return "```bash\nprintf 'ok'\n```\n\nExplanation:\n* Prints ok."


def response_text_with_plain_text_explanation():
    return "```bash\nprintf 'ok'\n```\n\nThis prints ok."


def response_text_with_language(language):
    return f"```{language}\nprintf 'ok'\n```\n\nExplanation:\n* Prints ok."


def response_text_with_embedded_fence():
    return (
        "```bash\ncat <<'EOF' > snippet.md\n```\nhello\n```\nEOF\n```\n\nExplanation:\n"
        "* Writes a markdown snippet."
    )


def response_text_with_explanation_fenced_block():
    return (
        "```bash\nprintf 'ok'\n```\n\nExplanation:\n"
        "* Prints ok.\n"
        "* Example output:\n"
        "```text\nok\n```"
    )


def test_shellgenius_non_tty_defaults_to_command_only_output(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: calls.append(kwargs) or (response_text(), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"])

    assert result.exit_code == 0
    assert calls == [{"model": cli_module.DEFAULT_MODEL, "stream": False}]
    assert result.output == "printf 'ok'\n"


def test_shellgenius_non_tty_rejects_unexecutable_shell_fence(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text_with_language("powershell"), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"])

    assert result.exit_code == 1
    assert "Cannot run `powershell` fences on this platform." in result.output


def test_shellgenius_interactive_tty_uses_live_streaming(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: calls.append(kwargs) or (response_text(), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"], input="n\n")

    assert result.exit_code == 0
    assert calls[0]["stream"] is True
    assert calls[0]["model"] == cli_module.DEFAULT_MODEL


def test_shellgenius_redirected_stderr_still_streams_and_prompts(monkeypatch):
    runner = CliRunner()
    calls = []
    executed = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, False))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(cli_module.shutil, "which", lambda shell_name: f"/mock/{shell_name}")
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: calls.append(kwargs) or (response_text(), 0, object()),
    )
    monkeypatch.setattr(
        cli_module.subprocess,
        "run",
        lambda *args, **kwargs: executed.append((args, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"], input="y\n")

    assert result.exit_code == 0
    assert len(calls) == 1
    assert calls[0]["model"] == cli_module.DEFAULT_MODEL
    assert calls[0]["stream"] is True
    assert callable(calls[0]["chunk_callback"])
    assert executed == [((["/mock/bash", "-c", "printf 'ok'"],), {"check": True})]


def test_shellgenius_command_only_prints_only_the_command(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text(), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["--cmd", "print", "ok"])

    assert result.exit_code == 0
    assert result.output == "printf 'ok'\n"


def test_shellgenius_command_only_accepts_plain_text_explanation(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text_with_plain_text_explanation(), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["--cmd", "print", "ok"])

    assert result.exit_code == 0
    assert result.output == "printf 'ok'\n"


def test_shellgenius_command_only_rejects_missing_shell_executable(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(cli_module.shutil, "which", lambda _shell_name: None)
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text_with_language("zsh"), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["--cmd", "print", "ok"])

    assert result.exit_code == 1
    assert "Cannot execute: `zsh` is not installed." in result.output


def test_shellgenius_rejects_non_shell_fence_for_command_only(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: ("```python\nprint('ok')\n```", 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["--cmd", "print", "ok"])

    assert result.exit_code == 1
    assert (
        "Command fence must use `bash`, `sh`, `zsh`, `shell`, `powershell`, or no language."
        in result.output
    )


def test_shellgenius_command_only_keeps_embedded_fence_lines(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text_with_embedded_fence(), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["--cmd", "write", "snippet"])

    assert result.exit_code == 0
    assert result.output == "cat <<'EOF' > snippet.md\n```\nhello\n```\nEOF\n"


def test_shellgenius_command_only_ignores_explanation_fenced_blocks(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text_with_explanation_fenced_block(), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["--cmd", "print", "ok"])

    assert result.exit_code == 0
    assert result.output == "printf 'ok'\n"


def test_shellgenius_uses_selected_model(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: calls.append(kwargs) or (response_text(), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["--model", "gpt-4.1", "print", "ok"])

    assert result.exit_code == 0
    assert calls == [{"model": "gpt-4.1", "stream": False}]


def test_shellgenius_piped_stdin_with_tty_stdout_can_confirm(monkeypatch):
    """``printf 'y\\n' | shellgenius …`` should execute when stdout is a TTY."""
    runner = CliRunner()
    executed = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(False, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(cli_module.shutil, "which", lambda shell_name: f"/mock/{shell_name}")
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text(), 0, object()),
    )
    monkeypatch.setattr(
        cli_module.subprocess,
        "run",
        lambda *args, **kwargs: executed.append((args, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"], input="y\n")

    assert result.exit_code == 0
    assert "Execute this command?" in result.output
    assert executed == [((["/mock/bash", "-c", "printf 'ok'"],), {"check": True})]


def test_stdin_has_prompt_input_accepts_delayed_pipe_without_blocking():
    read_fd, write_fd = os.pipe()

    try:
        with os.fdopen(read_fd, "r", encoding="utf-8") as reader:
            writer = os.fdopen(write_fd, "w", encoding="utf-8")
            try:
                start = time.monotonic()
                assert cli_module.stdin_has_prompt_input(reader) is True
                assert time.monotonic() - start < 0.5
            finally:
                writer.close()
    finally:
        try:
            os.close(write_fd)
        except OSError:
            pass


def test_stdin_has_prompt_input_rejects_pipe_at_eof():
    read_fd, write_fd = os.pipe()

    os.close(write_fd)
    with os.fdopen(read_fd, "r", encoding="utf-8") as reader:
        assert cli_module.stdin_has_prompt_input(reader) is False


def test_windows_stream_can_prompt_accepts_open_pipe(monkeypatch):
    fake_ctypes = types.SimpleNamespace(
        windll=types.SimpleNamespace(
            kernel32=types.SimpleNamespace(PeekNamedPipe=lambda *_args: 1)
        ),
        byref=lambda value: value,
        get_last_error=lambda: 0,
        wintypes=types.SimpleNamespace(DWORD=lambda: 0, HANDLE=lambda value: value),
    )
    fake_msvcrt = types.SimpleNamespace(get_osfhandle=lambda fd: fd)

    monkeypatch.setitem(sys.modules, "ctypes", fake_ctypes)
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)

    assert cli_module._windows_stream_can_prompt(7) is True


def test_windows_stream_can_prompt_rejects_non_pipe_errors(monkeypatch):
    fake_ctypes = types.SimpleNamespace(
        windll=types.SimpleNamespace(
            kernel32=types.SimpleNamespace(PeekNamedPipe=lambda *_args: 0)
        ),
        byref=lambda value: value,
        get_last_error=lambda: 6,
        wintypes=types.SimpleNamespace(DWORD=lambda: 0, HANDLE=lambda value: value),
    )
    fake_msvcrt = types.SimpleNamespace(get_osfhandle=lambda fd: fd)

    monkeypatch.setitem(sys.modules, "ctypes", fake_ctypes)
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)

    assert cli_module._windows_stream_can_prompt(7) is False


def test_shellgenius_eof_stdin_with_tty_stdout_skips_prompt(monkeypatch):
    runner = CliRunner()
    executed = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(False, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text(), 0, object()),
    )
    monkeypatch.setattr(
        cli_module.subprocess,
        "run",
        lambda *args, **kwargs: executed.append((args, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"])

    assert result.exit_code == 0
    assert "Execute this command?" not in result.output
    assert executed == []


def test_shellgenius_piped_stdin_with_tty_stdout_can_decline(monkeypatch):
    """Piped stdin answering 'n' should not execute."""
    runner = CliRunner()
    executed = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(False, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text(), 0, object()),
    )
    monkeypatch.setattr(
        cli_module.subprocess,
        "run",
        lambda *args, **kwargs: executed.append((args, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"], input="n\n")

    assert result.exit_code == 0
    assert "Execute this command?" in result.output
    assert "Not executed." in result.output
    assert executed == []


def test_shellgenius_execute_keeps_embedded_fence_lines(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(cli_module.shutil, "which", lambda shell_name: f"/mock/{shell_name}")
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text_with_embedded_fence(), 0, object()),
    )
    monkeypatch.setattr(
        cli_module.subprocess,
        "run",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["write", "snippet"], input="y\n")

    assert result.exit_code == 0
    assert calls == [
        (
            (
                [
                    "/mock/bash",
                    "-c",
                    "cat <<'EOF' > snippet.md\n```\nhello\n```\nEOF",
                ],
            ),
            {"check": True},
        )
    ]


def test_shellgenius_execute_ignores_explanation_fenced_blocks(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(cli_module.shutil, "which", lambda shell_name: f"/mock/{shell_name}")
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text_with_explanation_fenced_block(), 0, object()),
    )
    monkeypatch.setattr(
        cli_module.subprocess,
        "run",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"], input="y\n")

    assert result.exit_code == 0
    assert calls == [((["/mock/bash", "-c", "printf 'ok'"],), {"check": True})]


def test_shellgenius_executes_with_zsh_when_requested(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(cli_module.shutil, "which", lambda shell_name: f"/mock/{shell_name}")
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text_with_language("zsh"), 0, object()),
    )
    monkeypatch.setattr(
        cli_module.subprocess,
        "run",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"], input="y\n")

    assert result.exit_code == 0
    assert calls == [((["/mock/zsh", "-c", "printf 'ok'"],), {"check": True})]


def test_shellgenius_executes_shell_fence_with_sh(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(cli_module.shutil, "which", lambda shell_name: f"/mock/{shell_name}")
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text_with_language("shell"), 0, object()),
    )
    monkeypatch.setattr(
        cli_module.subprocess,
        "run",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"], input="y\n")

    assert result.exit_code == 0
    assert calls == [((["/mock/sh", "-c", "printf 'ok'"],), {"check": True})]


def test_shellgenius_rejects_non_shell_fence_for_execute(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text_with_language("powershell"), 0, object()),
    )
    monkeypatch.setattr(
        cli_module.subprocess,
        "run",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"], input="y\n")

    assert result.exit_code == 1
    assert "Cannot run `powershell` fences on this platform." in result.output
    assert calls == []


def test_shellgenius_rejects_bash_fence_on_windows(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(cli_module.platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text(), 0, object()),
    )
    monkeypatch.setattr(
        cli_module.subprocess,
        "run",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"], input="y\n")

    assert result.exit_code == 1
    assert "Cannot run `bash` fences on Windows." in result.output
    assert calls == []


def test_shellgenius_executes_with_powershell_on_windows(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(cli_module.platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text_with_language("powershell"), 0, object()),
    )
    monkeypatch.setattr(
        cli_module.subprocess,
        "run",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"], input="y\n")

    assert result.exit_code == 0
    assert calls == [
        (
            (["powershell.exe", "-NoProfile", "-Command", "printf 'ok'"],),
            {"check": True},
        )
    ]


def test_shellgenius_reports_parse_error_for_command_only(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: ("Here is your command: ls", 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["--cmd", "list", "files"])

    assert result.exit_code == 1
    assert "Response must start with a fenced code block." in result.output


def test_shellgenius_interactive_tty_prompts_to_execute_by_default(monkeypatch):
    runner = CliRunner()
    executed = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(cli_module.shutil, "which", lambda shell_name: f"/mock/{shell_name}")
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text(), 0, object()),
    )
    monkeypatch.setattr(
        cli_module.subprocess,
        "run",
        lambda *args, **kwargs: executed.append((args, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"], input="y\n")

    assert result.exit_code == 0
    assert "Execute this command?" in result.output
    assert executed == [((["/mock/bash", "-c", "printf 'ok'"],), {"check": True})]


def test_shellgenius_interactive_tty_declines_execution(monkeypatch):
    runner = CliRunner()
    executed = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text(), 0, object()),
    )
    monkeypatch.setattr(
        cli_module.subprocess,
        "run",
        lambda *args, **kwargs: executed.append((args, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"], input="n\n")

    assert result.exit_code == 0
    assert "Execute this command?" in result.output
    assert "Not executed." in result.output
    assert executed == []


def test_shellgenius_non_tty_does_not_execute_or_prompt(monkeypatch):
    runner = CliRunner()
    executed = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text(), 0, object()),
    )
    monkeypatch.setattr(
        cli_module.subprocess,
        "run",
        lambda *args, **kwargs: executed.append((args, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"])

    assert result.exit_code == 0
    assert "Execute this command?" not in result.output
    assert executed == []


def test_shellgenius_raw_shows_full_response_in_non_tty(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text(), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["--raw", "print", "ok"])

    assert result.exit_code == 0
    assert result.output == response_text() + "\n"


def test_shellgenius_raw_disables_streaming_in_tty(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: calls.append(kwargs) or (response_text(), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["--raw", "print", "ok"], input="n\n")

    assert result.exit_code == 0
    assert calls == [{"model": cli_module.DEFAULT_MODEL, "stream": False}]
    assert response_text() + "\n\nExecute this command?" in result.output
    assert "Execute this command?" in result.output
    assert "Not executed." in result.output


def test_shellgenius_non_tty_rich_falls_back_to_plain_text(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: calls.append(kwargs) or (response_text(), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["--rich", "print", "ok"])

    assert result.exit_code == 0
    assert calls == [{"model": cli_module.DEFAULT_MODEL, "stream": False}]
    assert result.output == response_text().rstrip("\n") + "\n"


def test_shellgenius_non_tty_rich_skips_pipe_mode_validation(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text_with_language("powershell"), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["--rich", "print", "ok"])

    assert result.exit_code == 0
    assert "```powershell" in result.output


def test_shellgenius_rejects_raw_and_rich_together(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))

    result = runner.invoke(cli_module.shellgenius, ["--raw", "--rich", "print", "ok"])

    assert result.exit_code == 2
    assert "You cannot use `--raw` and `--rich` at the same time." in result.output


def test_shellgenius_c_short_flag_is_removed():
    runner = CliRunner()

    result = runner.invoke(cli_module.shellgenius, ["-c", "print", "ok"])

    assert result.exit_code != 0
    assert "No such option: -c" in result.output


@pytest.mark.parametrize("flag", ["--plain", "-p", "--command-only"])
def test_shellgenius_retrocompat_output_aliases_are_removed(flag):
    runner = CliRunner()

    result = runner.invoke(cli_module.shellgenius, [flag, "print", "ok"])

    assert result.exit_code != 0
    assert f"No such option: {flag}" in result.output


def test_entrypoint_main_delegates_to_cli_entrypoint(monkeypatch):
    calls = []

    monkeypatch.setattr(
        entrypoint_module.importlib,
        "import_module",
        lambda name: calls.append(name) or SimpleNamespace(shellgenius=lambda: 7),
    )

    assert entrypoint_module.main() == 7
    assert calls == ["shellgenius.cli"]


def test_entrypoint_main_exits_130_on_keyboard_interrupt_during_cli_import(monkeypatch):
    def raise_interrupt(_name):
        raise KeyboardInterrupt()

    monkeypatch.setattr(entrypoint_module.importlib, "import_module", raise_interrupt)

    with pytest.raises(SystemExit) as error:
        entrypoint_module.main()

    assert error.value.code == 130


# -- blank line before Rich output ---------------------------------------------


def test_render_response_rich_path_prints_leading_blank_line(monkeypatch, capsys):
    class FakeConsole:
        def print(self, _md):
            pass

    monkeypatch.setattr(cli_module, "make_console", lambda _theme: FakeConsole())

    cli_module.render_response(
        "hello",
        tty_state=cli_module.TTYState(True, True, True),
        raw=False,
        rich_flag=False,
        command_only=False,
        theme=LmtTheme(),
    )

    captured = capsys.readouterr()
    assert captured.out.startswith("\n")


def test_render_response_raw_path_has_no_leading_blank_line(capsys):
    import shellgenius.cli as mod

    mod.render_response(
        response_text(),
        tty_state=cli_module.TTYState(True, True, True),
        raw=True,
        rich_flag=False,
        command_only=False,
        theme=LmtTheme(),
    )

    captured = capsys.readouterr()
    assert not captured.out.startswith("\n")


def test_render_response_command_only_has_no_leading_blank_line(capsys):
    import shellgenius.cli as mod

    mod.render_response(
        response_text(),
        tty_state=cli_module.TTYState(False, False, False),
        raw=False,
        rich_flag=False,
        command_only=True,
        theme=LmtTheme(),
    )

    captured = capsys.readouterr()
    assert not captured.out.startswith("\n")


def test_live_streaming_path_prints_leading_blank_line(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text(), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"], input="n\n")

    assert result.exit_code == 0
    assert result.output.startswith("\n")


def test_live_streaming_fallback_rich_path_keeps_single_leading_blank_line(monkeypatch):
    runner = CliRunner()

    class FakeConsole:
        def print(self, rendered):
            print(rendered, end="")

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(cli_module, "make_console", lambda _theme: FakeConsole())
    monkeypatch.setattr(cli_module, "make_renderable", lambda text, _theme: text)
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text(), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"], input="n\n")

    assert result.exit_code == 0
    assert result.output.startswith("\n```bash\n")
    assert not result.output.startswith("\n\n")


def test_live_streaming_callback_uses_renderable(monkeypatch):
    updates = []
    renderable_calls = []

    class FakeLive:
        def update(self, renderable):
            updates.append(renderable)

    theme = LmtTheme(
        code_block_theme="alabaster",
        shellgenius_theme="alabaster",
        shellgenius_code_block_theme="alabaster",
        shellgenius_command_block_style="on #f8f8f8",
    )

    def spy_renderable(text, received_theme):
        renderable_calls.append((text, received_theme))
        return f"rendered:{text}"

    monkeypatch.setattr(cli_module, "make_renderable", spy_renderable)

    callback = cli_module.LiveMarkdownCallback(FakeLive(), theme)
    callback(response_text())

    assert renderable_calls == [(response_text(), theme)]
    assert updates == [f"rendered:{response_text()}"]


# -- lmterminal theme integration ---------------------------------------------


def test_render_response_rich_path_uses_theme(monkeypatch):
    console_calls = []
    renderable_calls = []

    class FakeConsole:
        def print(self, _renderable):
            pass

    theme = LmtTheme(code_block_theme="zenburn", inline_code_theme="red on white")

    def spy_console(t):
        console_calls.append(t)
        return FakeConsole()

    def spy_renderable(text, t):
        renderable_calls.append((text, t))
        return text

    monkeypatch.setattr(cli_module, "make_console", spy_console)
    monkeypatch.setattr(cli_module, "make_renderable", spy_renderable)

    cli_module.render_response(
        "hello",
        tty_state=cli_module.TTYState(True, True, True),
        raw=False,
        rich_flag=False,
        command_only=False,
        theme=theme,
    )

    assert console_calls == [theme]
    assert renderable_calls == [("hello", theme)]


def test_render_response_uses_shellgenius_renderable_when_theme_requests_it(monkeypatch):
    console_calls = []
    renderable_calls = []

    class FakeConsole:
        def print(self, _renderable):
            pass

    theme = LmtTheme(
        code_block_theme="alabaster",
        shellgenius_theme="alabaster",
        shellgenius_code_block_theme="alabaster",
        shellgenius_command_block_style="on #f8f8f8",
    )

    def spy_console(t):
        console_calls.append(t)
        return FakeConsole()

    def spy_renderable(text, t):
        renderable_calls.append((text, t))
        return text

    monkeypatch.setattr(cli_module, "make_console", spy_console)
    monkeypatch.setattr(cli_module, "make_renderable", spy_renderable)

    cli_module.render_response(
        "hello",
        tty_state=cli_module.TTYState(True, True, True),
        raw=False,
        rich_flag=False,
        command_only=False,
        theme=theme,
    )

    assert console_calls == [theme]
    assert renderable_calls == [("hello", theme)]


# -- missing coverage ----------------------------------------------------------


def test_shellgenius_no_stream_disables_streaming_in_tty(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: calls.append(kwargs) or (response_text(), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["--no-stream", "print", "ok"], input="n\n")

    assert result.exit_code == 0
    assert calls == [{"model": cli_module.DEFAULT_MODEL, "stream": False}]


def test_shellgenius_rate_limit_error_prints_guidance(monkeypatch):
    runner = CliRunner()

    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(429, request=request)

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)

    def raise_rate_limit(*args, **kwargs):
        raise RateLimitError("rate limited", response=response, body={"error": {}})

    monkeypatch.setattr(cli_module, "chatgpt_request", raise_rate_limit)

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"])

    assert result.exit_code == 1
    assert "rate limited" in result.output
    assert "usage limit" in result.output


def test_shellgenius_missing_shell_executable_fails(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(cli_module.shutil, "which", lambda _name: None)
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text(), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"], input="y\n")

    assert result.exit_code == 1
    assert "is not installed" in result.output


def test_shellgenius_called_process_error_during_execution(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(cli_module.shutil, "which", lambda shell_name: f"/mock/{shell_name}")

    def raise_called_process_error(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "bash")

    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text(), 0, object()),
    )
    monkeypatch.setattr(cli_module.subprocess, "run", raise_called_process_error)

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"], input="y\n")

    assert result.exit_code == 1
    assert "Command failed" in result.output


def test_shellgenius_no_args_shows_help():
    runner = CliRunner()

    result = runner.invoke(cli_module.shellgenius, [])

    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "Generate a shell command" in result.output
    assert "--model" in result.output
    assert "shellgenius prompt" not in result.output


def test_shellgenius_executes_no_fence_language_with_sh(monkeypatch):
    """No-language fence falls back to ``sh`` on Unix."""
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(cli_module.shutil, "which", lambda shell_name: f"/mock/{shell_name}")
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: ("```\nprintf 'ok'\n```\n\n* Prints ok.", 0, object()),
    )
    monkeypatch.setattr(
        cli_module.subprocess,
        "run",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"], input="y\n")

    assert result.exit_code == 0
    assert calls == [((["/mock/sh", "-c", "printf 'ok'"],), {"check": True})]


# -- model aliases and `models` command ----------------------------------------


def test_shellgenius_models_lists_all_valid_models():
    runner = CliRunner()

    result = runner.invoke(cli_module.shellgenius, ["models"])

    assert result.exit_code == 0
    for model in cli_module.VALID_MODELS:
        assert model in result.output


def test_shellgenius_models_shows_aliases():
    runner = CliRunner()

    result = runner.invoke(cli_module.shellgenius, ["models"])

    assert result.exit_code == 0
    assert "Alias: 4.1\n" in result.output
    assert "Alias: 5.4-mini\n" in result.output


def test_shellgenius_alias_resolves_to_canonical(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: calls.append(kwargs) or (response_text(), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["--model", "4.1", "print", "ok"])

    assert result.exit_code == 0
    assert calls == [{"model": "gpt-4.1", "stream": False}]


def test_shellgenius_alias_resolves_case_insensitively(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: calls.append(kwargs) or (response_text(), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["--model", "GPT-4.1", "print", "ok"])

    assert result.exit_code == 0
    assert calls == [{"model": "gpt-4.1", "stream": False}]


def test_shellgenius_invalid_model_fails_with_hint():
    runner = CliRunner()

    result = runner.invoke(cli_module.shellgenius, ["--model", "invalid", "print", "ok"])

    assert result.exit_code != 0
    assert "Invalid value for '--model' / '-m': Invalid model name." in result.output
    assert "Use shellgenius models to list supported models and aliases." in result.output


def test_shellgenius_invalid_model_styles_message_and_command():
    runner = CliRunner()

    result = runner.invoke(
        cli_module.shellgenius,
        ["--model", "invalid", "print", "ok"],
        color=True,
    )

    assert result.exit_code != 0
    assert "\x1b[31mInvalid model name.\x1b[0m" in result.output
    assert "\x1b[31mUse \x1b[0m\x1b[34mshellgenius models\x1b[0m" in result.output


def test_shellgenius_routes_leaf_option_value_sequences_to_subcommand_parser(monkeypatch):
    runner = CliRunner()
    chatgpt_calls = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: chatgpt_calls.append((args, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["models", "-m", "gpt-5"])

    assert result.exit_code == 2
    assert "No such option: -m" in result.output
    assert chatgpt_calls == []


@pytest.mark.parametrize(
    "args",
    [
        ["models", "for", "me"],
    ],
)
def test_shellgenius_keeps_malformed_leaf_subcommands_on_subcommand_path(monkeypatch, args):
    runner = CliRunner()
    prompts = []
    chatgpt_calls = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "format_prompt",
        lambda *call_args, **call_kwargs: prompts.append((call_args, call_kwargs)),
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *call_args, **call_kwargs: chatgpt_calls.append((call_args, call_kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, args)

    assert result.exit_code == 2
    assert "Got unexpected extra argument" in result.output
    assert prompts == []
    assert chatgpt_calls == []


def test_shellgenius_models_help_shows_subcommand_help():
    runner = CliRunner()

    result = runner.invoke(cli_module.shellgenius, ["models", "--help"])

    assert result.exit_code == 0
    assert "List supported models" in result.output


# -- `--tokens` flag -----------------------------------------------------------


@pytest.mark.parametrize(
    "extra_args",
    [
        [],
        ["--model", "gpt-5.4"],
    ],
)
def test_shellgenius_tokens_prints_count_and_cost_without_api_call(monkeypatch, extra_args):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: calls.append(kwargs) or (response_text(), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["--tokens", *extra_args, "print", "ok"])

    assert result.exit_code == 0
    assert calls == []
    assert "Prompt tokens:" in result.output
    assert "Estimated cost for" in result.output
    assert "$" in result.output


def test_shellgenius_tokens_has_no_short_flag():
    runner = CliRunner()

    result = runner.invoke(cli_module.shellgenius, ["-t", "print", "ok"])

    assert result.exit_code != 0
    assert "No such option: -t" in result.output


def test_shellgenius_tokens_cost_unavailable_for_unknown_price(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(cli_module, "estimate_prompt_cost", lambda _msgs, _model: None)

    result = runner.invoke(cli_module.shellgenius, ["--tokens", "print", "ok"])

    assert result.exit_code == 0
    assert "Prompt tokens:" in result.output
    assert "Cost unavailable" in result.output


# -- help includes models ------------------------------------------------------


def test_shellgenius_help_lists_models_command():
    runner = CliRunner()

    result = runner.invoke(cli_module.shellgenius, ["--help"])

    assert result.exit_code == 0
    assert "[COMMAND_DESCRIPTION]" in result.output
    assert "--model" in result.output
    assert "models" in result.output
    assert "key" in result.output
    assert "shellgenius prompt --help" in result.output


# -- key subcommand routing ----------------------------------------------------


@pytest.mark.parametrize(
    ("args", "description"),
    [
        (["key", "rotation"], "key rotation"),
    ],
)
def test_shellgenius_routes_ambiguous_top_level_commands_to_prompt(
    monkeypatch,
    args,
    description,
):
    runner = CliRunner()
    prompts = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "format_prompt",
        lambda command_description, os_name: (
            prompts.append((command_description, os_name))
            or [{"role": "user", "content": command_description}]
        ),
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: (response_text(), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, args)

    assert result.exit_code == 0
    assert prompts == [(description, "Linux")]
    assert result.output == "printf 'ok'\n"


@pytest.mark.parametrize(
    "args",
    [
        ["key", "set", "permissions"],
        ["key", "set", "sk-test"],
    ],
)
def test_shellgenius_keeps_malformed_key_subcommands_on_subcommand_path(monkeypatch, args):
    runner = CliRunner()
    prompts = []
    chatgpt_calls = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "format_prompt",
        lambda *call_args, **call_kwargs: prompts.append((call_args, call_kwargs)),
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *call_args, **call_kwargs: chatgpt_calls.append((call_args, call_kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, args)

    assert result.exit_code == 2
    assert "Got unexpected extra argument" in result.output
    assert prompts == []
    assert chatgpt_calls == []
