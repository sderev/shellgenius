from __future__ import annotations

import os
import re
import stat
from pathlib import Path

import click

KEY_FILE_PATH = Path.home() / ".config" / "lmt" / "key.env"
EXPORT_KEY_LINE_RE = re.compile(r"^export[ \t]+OPENAI_API_KEY=(.*)$")


def get_api_key_path() -> Path:
    return KEY_FILE_PATH


def _parse_key_file(path: Path) -> str:
    """Parse an API key from a key file.

    Accepted formats:
    * ``OPENAI_API_KEY=sk-...``
    * ``export OPENAI_API_KEY=sk-...``
    * Quoted values for those assignments.

    The file is dedicated to this single key. Blank lines and comments are
    allowed, but any other non-comment content makes the file invalid.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError, OSError):
        return ""

    key = ""

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        match = EXPORT_KEY_LINE_RE.match(line)
        if match:
            value = match.group(1)
        elif line.startswith("OPENAI_API_KEY="):
            value = line[len("OPENAI_API_KEY=") :]
        else:
            return ""

        # Strip optional surrounding quotes.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]

        if key:
            return ""
        key = value.strip()

    return key


def get_api_key() -> str:
    """Return the OpenAI API key.

    Resolution order:
    1. ``OPENAI_API_KEY`` environment variable.
    2. ``~/.config/lmt/key.env`` file.
    """
    env_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if env_key:
        return env_key
    return _parse_key_file(get_api_key_path())


def _write_key(key: str) -> None:
    """Write *key* to the key file with ``0600`` permissions."""
    path = get_api_key_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"OPENAI_API_KEY={key}\n", encoding="utf-8")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def set_key() -> None:
    """Prompt the user for a new API key and write it to the key file."""
    existing = _parse_key_file(get_api_key_path())
    if existing:
        raise click.ClickException(
            "API key already exists.\n"
            f"Use `{click.style('shellgenius key edit', fg='blue')}` to edit it."
        )

    key = click.prompt("Your OpenAI API key", hide_input=True)
    _write_key(key)
    click.secho("Success!", fg="green", nl=False)
    click.echo(" API key saved.")
    click.echo(f"\nStored in {get_api_key_path()}")


def edit_key() -> None:
    """Prompt the user to replace the existing API key."""
    existing = _parse_key_file(get_api_key_path())
    if not existing:
        click.secho("Error: ", fg="red", nl=False, err=True)
        click.echo("No API key found.", err=True)
        click.echo("You will now be prompted to add one.\n", err=True)
        set_key()
        return

    new_key = click.prompt("Your OpenAI API key", hide_input=True)
    if existing == new_key:
        click.echo("No changes were made.")
    else:
        _write_key(new_key)
        click.secho("Success!", fg="green", nl=False)
        click.echo(" API key updated.")
    click.echo(f"\nStored in {get_api_key_path()}")
