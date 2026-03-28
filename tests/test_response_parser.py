import pytest

from shellgenius.response_parser import (
    ShellGeniusResponseError,
    parse_shellgenius_response,
    validate_executable_shell_response,
)


def test_parse_shellgenius_response_extracts_command_and_explanation():
    response = parse_shellgenius_response(
        "```zsh\nls -la\n```\n\n### Explanation:\n* Lists files.\n* Shows hidden files."
    )

    assert response.command == "ls -la"
    assert response.explanation == "* Lists files.\n* Shows hidden files."
    assert response.raw_text.startswith("```zsh")
    assert response.fence_language == "zsh"


def test_parse_shellgenius_response_accepts_fence_without_language():
    response = parse_shellgenius_response("```\npwd\n```")

    assert response.command == "pwd"
    assert response.explanation == ""
    assert response.fence_language is None


def test_parse_shellgenius_response_preserves_multiline_commands():
    response = parse_shellgenius_response(
        "```sh\nfind . -type f \\\n  | sort\n```\nExplanation:\n* Finds files."
    )

    assert response.command == "find . -type f \\\n  | sort"
    assert response.explanation == "* Finds files."


def test_parse_shellgenius_response_accepts_plain_text_explanation_after_blank_line():
    response = parse_shellgenius_response("```bash\necho hi\n```\n\nThis prints hi.")

    assert response.command == "echo hi"
    assert response.explanation == "This prints hi."


def test_parse_shellgenius_response_keeps_embedded_fence_lines_in_command():
    response = parse_shellgenius_response(
        "```bash\ncat <<'EOF' > snippet.md\n```\nhello\n```\nEOF\n```\nExplanation:\n* Writes a markdown snippet."
    )

    assert response.command == "cat <<'EOF' > snippet.md\n```\nhello\n```\nEOF"
    assert response.explanation == "* Writes a markdown snippet."


def test_parse_shellgenius_response_keeps_explanation_fenced_blocks_out_of_command():
    response = parse_shellgenius_response(
        "```bash\nprintf 'ok'\n```\n\nExplanation:\n* Prints ok.\n* Example output:\n```text\nok\n```"
    )

    assert response.command == "printf 'ok'"
    assert response.explanation == "* Prints ok.\n* Example output:\n```text\nok\n```"


def test_validate_executable_shell_response_accepts_shell_fences_case_insensitively():
    response = parse_shellgenius_response("```BASH\npwd\n```")

    validate_executable_shell_response(response)


def test_validate_executable_shell_response_rejects_non_shell_fence():
    response = parse_shellgenius_response("```python\nprint('ok')\n```")

    with pytest.raises(ShellGeniusResponseError):
        validate_executable_shell_response(response)


@pytest.mark.parametrize(
    "response_text",
    [
        "ls -la\n\n* Lists files.",
        "```bash\nls -la",
        "```bash\n\n```",
        "Before the code block\n```bash\nls -la\n```",
    ],
)
def test_parse_shellgenius_response_rejects_malformed_output(response_text):
    with pytest.raises(ShellGeniusResponseError):
        parse_shellgenius_response(response_text)
