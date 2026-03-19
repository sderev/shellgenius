from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedShellResponse:
    command: str
    explanation: str
    raw_text: str
    fence_language: str | None = None


class ShellGeniusResponseError(ValueError):
    """Raised when the model output does not match the expected contract."""


def parse_shellgenius_response(text: str) -> ParsedShellResponse:
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
    stripped_text = normalized_text.lstrip()

    if not stripped_text.startswith("```"):
        raise ShellGeniusResponseError("Response must start with a fenced code block.")

    opening_line_end = stripped_text.find("\n")
    if opening_line_end == -1:
        raise ShellGeniusResponseError("Opening code fence is incomplete.")

    fence_language = stripped_text[3:opening_line_end].strip() or None
    remaining_text = stripped_text[opening_line_end + 1 :]
    closing_fence_match: re.Match[str] | None = None

    for match in re.finditer(r"(?m)^[ \t]*```[ \t]*$", remaining_text):
        if _starts_with_explanation(remaining_text[match.end() :]):
            closing_fence_match = match
            break

    if closing_fence_match is None:
        raise ShellGeniusResponseError("Closing code fence is missing.")

    command = remaining_text[: closing_fence_match.start()].strip()
    if not command:
        raise ShellGeniusResponseError("Command block is empty.")

    explanation = _normalize_explanation(remaining_text[closing_fence_match.end() :].strip())

    return ParsedShellResponse(
        command=command,
        explanation=explanation,
        raw_text=text,
        fence_language=fence_language,
    )


def _normalize_explanation(explanation: str) -> str:
    if not explanation:
        return ""

    match = re.match(
        r"^(?:#{1,6}\s*)?\*{0,2}Explanation\*{0,2}\s*:?\s*(?P<body>.*)$",
        explanation,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        return explanation

    return match.group("body").lstrip()


def _starts_with_explanation(text: str) -> bool:
    stripped_text = text.lstrip()
    if not stripped_text:
        return True

    if _starts_with_blank_line(text) and not stripped_text.startswith("```"):
        return True

    if re.match(
        r"^(?:#{1,6}\s*)?\*{0,2}Explanation\*{0,2}\s*:?(?:\n|\s|$)",
        stripped_text,
        flags=re.IGNORECASE,
    ):
        return True

    return re.match(r"^(?:[*+-]|\d+\.)\s+", stripped_text) is not None


def _starts_with_blank_line(text: str) -> bool:
    return re.match(r"^\n[ \t]*\n", text) is not None
