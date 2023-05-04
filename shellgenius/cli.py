"""
cli.py: Command Line Interface for ShellGenius

This module provides a command-line interface (CLI) for the ShellGenius application, which utilizes
the gpt-3.5-turbo AI model to generate shell commands based on a given textual description. The
generated commands are displayed with explanations, and the user can choose to execute them directly
from the interface.

The module defines the `shellgenius()` function, which is the main entry point for the CLI command,
and a `rich_markdown_callback()` function for updating the live markdown display with chunks of text
received from the AI API.

Functions:
    * shellgenius(command_description: Tuple[str, ...]) -> None
        Generate and optionally execute a shell command based on the given command description
        using the gpt-3.5-turbo AI model.
        
    * rich_markdown_callback(chunk: str) -> None
        Update the live markdown display with the received chunk of text from the gpt-3.5-turbo AI
        API.
"""
import re
import subprocess
import click
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from .gpt_integration import format_prompt, chatgpt_request


live_markdown_text = ""
live_markdown = Markdown(live_markdown_text)
live = Live(live_markdown, console=Console())


def rich_markdown_callback(chunk: str) -> None:
    """
    Update the live markdown display with the received chunk of text from the API.

    Args:
        chunk (str): A chunk of text received from the API.
    """
    global live_markdown, live_markdown_text
    live_markdown_text += chunk
    live_markdown = Markdown(live_markdown_text)
    live.update(live_markdown)


@click.command()
@click.argument("command_description", type=str, nargs=-1)
def shellgenius(command_description):
    """
    Generate and optionally execute a shell command based on the given command description.

    Example:
        $ shellgenius create a new file called example.txt
        Generated command: touch example.txt
        Explanation:
        - touch command is used to create a new file if it doesn't exist
        - example.txt is the name of the new file
        Do you want to execute this command? [Y/n]: y
    """
    if not command_description:
        click.echo(ctx.get_help()
        return

    command_description = " ".join(command_description)
    prompt = format_prompt(command_description)
    click.echo()

    with live:
        generated_text = chatgpt_request(
            prompt,
            stream=True,
            chunk_callback=rich_markdown_callback,
        )[0]
    click.echo()

    click.echo(click.style("Be careful with your answer.", fg="blue"))
    execute_cmd = click.confirm("Do you want to execute this command?")

    if execute_cmd:
        cmd = re.search(r"`bash\n(.+?)\n`", generated_text).group(1)
        if cmd:
            subprocess.run(cmd, shell=True, check=True)
        else:
            click.echo(click.style("No command found", fg="red"))
    else:
        click.echo(click.style("Command not executed", fg="red"))
