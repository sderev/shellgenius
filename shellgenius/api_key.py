from __future__ import annotations

import os
import stat
from pathlib import Path

import click

KEY_FILE_PATH = Path.home() / ".config" / "lmt" / "key.env"


def get_api_key_path() -> Path:
    return KEY_FILE_PATH


def _parse_key_file(path: Path) -> str:
    """Parse an API key from a key file.

    Accepted formats:
    * ``OPENAI_API_KEY=sk-...``
    * ``export OPENAI_API_KEY=sk-...``
    * A single bare key on its own line.
    """
    try:
        text = path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, UnicodeDecodeError, OSError):
        return ""

    if not text:
        return ""

    bare_key = ""
    saw_other_content = False

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # export OPENAI_API_KEY=...
        if line.startswith("export "):
            line = line[len("export ") :].strip()
            if "=" not in line:
                saw_other_content = True
                continue

        # OPENAI_API_KEY=...
        if line.startswith("OPENAI_API_KEY="):
            value = line[len("OPENAI_API_KEY=") :]
            # Strip optional surrounding quotes.
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            return value.strip()

        if line == "OPENAI_API_KEY":
            saw_other_content = True
            continue

        if "=" in line:
            saw_other_content = True
            continue

        if bare_key or saw_other_content:
            saw_other_content = True
            continue

        # Single bare key on its own non-comment line.
        bare_key = line

    if bare_key and not saw_other_content:
        return bare_key

    return ""


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
