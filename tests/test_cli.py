import shellgenius.cli as cli_module
from click.testing import CliRunner


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


def test_shellgenius_non_tty_defaults_to_plain_buffered_output(monkeypatch):
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
    assert result.output == response_text() + "\n"


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

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"])

    assert result.exit_code == 0
    assert calls[0]["stream"] is True
    assert calls[0]["model"] == cli_module.DEFAULT_MODEL


def test_shellgenius_renders_completed_only_stream_after_live_block(monkeypatch):
    runner = CliRunner()
    calls = []
    render_calls = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: calls.append(kwargs) or (response_text(), 0, object()),
    )
    monkeypatch.setattr(
        cli_module,
        "render_response",
        lambda generated_text, **kwargs: render_calls.append((generated_text, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"])

    assert result.exit_code == 0
    assert calls[0]["stream"] is True
    assert callable(calls[0]["chunk_callback"])
    assert render_calls == [
        (
            response_text(),
            {
                "tty_state": cli_module.TTYState(True, True, True),
                "plain": False,
                "command_only": False,
            },
        )
    ]


def test_shellgenius_ignores_empty_live_chunks_and_renders_completed_text(monkeypatch):
    runner = CliRunner()
    render_calls = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(cli_module, "Live", DummyLive)

    def fake_chatgpt_request(*args, **kwargs):
        kwargs["chunk_callback"]("")
        return response_text(), 0, object()

    monkeypatch.setattr(cli_module, "chatgpt_request", fake_chatgpt_request)
    monkeypatch.setattr(
        cli_module,
        "render_response",
        lambda generated_text, **kwargs: render_calls.append((generated_text, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"])

    assert result.exit_code == 0
    assert render_calls == [
        (
            response_text(),
            {
                "tty_state": cli_module.TTYState(True, True, True),
                "plain": False,
                "command_only": False,
            },
        )
    ]


def test_shellgenius_redirected_stderr_still_streams_and_prompts(monkeypatch):
    runner = CliRunner()
    calls = []
    executed = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, False)
    )
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

    result = runner.invoke(cli_module.shellgenius, ["--execute", "print", "ok"], input="y\n")

    assert result.exit_code == 0
    assert len(calls) == 1
    assert calls[0]["model"] == cli_module.DEFAULT_MODEL
    assert calls[0]["stream"] is True
    assert callable(calls[0]["chunk_callback"])
    assert executed == [((["/mock/bash", "-c", "printf 'ok'"],), {"check": True})]


def test_shellgenius_plain_disables_streaming_in_tty(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(cli_module, "get_tty_state", lambda: cli_module.TTYState(True, True, True))
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: calls.append(kwargs) or (response_text(), 0, object()),
    )

    result = runner.invoke(cli_module.shellgenius, ["--plain", "print", "ok"])

    assert result.exit_code == 0
    assert calls == [{"model": cli_module.DEFAULT_MODEL, "stream": False}]
    assert result.output == response_text() + "\n"


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

    result = runner.invoke(cli_module.shellgenius, ["--command-only", "print", "ok"])

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

    result = runner.invoke(cli_module.shellgenius, ["--command-only", "print", "ok"])

    assert result.exit_code == 0
    assert result.output == "printf 'ok'\n"


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

    result = runner.invoke(cli_module.shellgenius, ["--command-only", "print", "ok"])

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

    result = runner.invoke(cli_module.shellgenius, ["--command-only", "write", "snippet"])

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

    result = runner.invoke(cli_module.shellgenius, ["--command-only", "print", "ok"])

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

    result = runner.invoke(cli_module.shellgenius, ["--model", "gpt-test", "print", "ok"])

    assert result.exit_code == 0
    assert calls == [{"model": "gpt-test", "stream": False}]


def test_shellgenius_does_not_execute_without_execute_flag(monkeypatch):
    runner = CliRunner()
    calls = []

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
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["print", "ok"])

    assert result.exit_code == 0
    assert calls == []


def test_shellgenius_executes_without_prompt_when_yes_is_set(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(cli_module.shutil, "which", lambda shell_name: f"/mock/{shell_name}")
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

    result = runner.invoke(cli_module.shellgenius, ["--execute", "--yes", "print", "ok"])

    assert result.exit_code == 0
    assert calls == [((["/mock/bash", "-c", "printf 'ok'"],), {"check": True})]


def test_shellgenius_execute_keeps_embedded_fence_lines(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
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

    result = runner.invoke(cli_module.shellgenius, ["--execute", "--yes", "write", "snippet"])

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

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
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

    result = runner.invoke(cli_module.shellgenius, ["--execute", "--yes", "print", "ok"])

    assert result.exit_code == 0
    assert calls == [((["/mock/bash", "-c", "printf 'ok'"],), {"check": True})]


def test_shellgenius_executes_with_zsh_when_requested(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
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

    result = runner.invoke(cli_module.shellgenius, ["--execute", "--yes", "print", "ok"])

    assert result.exit_code == 0
    assert calls == [((["/mock/zsh", "-c", "printf 'ok'"],), {"check": True})]


def test_shellgenius_executes_shell_fence_with_sh(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
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

    result = runner.invoke(cli_module.shellgenius, ["--execute", "--yes", "print", "ok"])

    assert result.exit_code == 0
    assert calls == [((["/mock/sh", "-c", "printf 'ok'"],), {"check": True})]


def test_shellgenius_rejects_non_shell_fence_for_execute(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
    monkeypatch.setattr(
        cli_module,
        "chatgpt_request",
        lambda *args, **kwargs: ("```python\nprint('ok')\n```", 0, object()),
    )
    monkeypatch.setattr(
        cli_module.subprocess,
        "run",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    result = runner.invoke(cli_module.shellgenius, ["--execute", "--yes", "print", "ok"])

    assert result.exit_code == 1
    assert (
        "Command fence must use `bash`, `sh`, `zsh`, `shell`, `powershell`, or no language."
        in result.output
    )
    assert calls == []


def test_shellgenius_executes_with_powershell_on_windows(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
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

    result = runner.invoke(cli_module.shellgenius, ["--execute", "--yes", "print", "ok"])

    assert result.exit_code == 0
    assert calls == [
        (
            (["powershell.exe", "-NoProfile", "-Command", "printf 'ok'"],),
            {"check": True},
        )
    ]


def test_shellgenius_rejects_powershell_fence_on_unix(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
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

    result = runner.invoke(cli_module.shellgenius, ["--execute", "--yes", "print", "ok"])

    assert result.exit_code == 1
    assert "`--execute` cannot run `powershell` fences on this platform." in result.output
    assert calls == []


def test_shellgenius_rejects_bash_fence_on_windows(monkeypatch):
    runner = CliRunner()
    calls = []

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )
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

    result = runner.invoke(cli_module.shellgenius, ["--execute", "--yes", "print", "ok"])

    assert result.exit_code == 1
    assert "`--execute` cannot run `bash` fences on Windows." in result.output
    assert calls == []


def test_shellgenius_rejects_non_interactive_execute_without_yes(monkeypatch):
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

    result = runner.invoke(cli_module.shellgenius, ["--execute", "print", "ok"])

    assert result.exit_code == 2
    assert "`--execute` requires `--yes`" in result.output
    assert calls == []


def test_shellgenius_rejects_yes_without_execute(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        cli_module, "get_tty_state", lambda: cli_module.TTYState(False, False, False)
    )

    result = runner.invoke(cli_module.shellgenius, ["--yes", "print", "ok"])

    assert result.exit_code == 2
    assert "`--yes` can only be used together with `--execute`." in result.output


def test_shellgenius_rejects_command_only_with_execute(monkeypatch):
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

    result = runner.invoke(cli_module.shellgenius, ["--command-only", "--execute", "print", "ok"])

    assert result.exit_code == 2
    assert "`--command-only` cannot be used together with `--execute`." in result.output
    assert calls == []


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

    result = runner.invoke(cli_module.shellgenius, ["--command-only", "list", "files"])

    assert result.exit_code == 1
    assert "Response must start with a fenced code block." in result.output
