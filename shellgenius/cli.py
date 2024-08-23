"""
cli.py: Command Line Interface for ShellGenius

This module provides a command-line interface (CLI) for the ShellGenius application, which utilizes
the gpt-4o-mini AI model to generate shell commands based on a given textual description. The
generated commands are displayed with explanations, and the user can choose to execute them directly
from the interface.

The module defines the `shellgenius()` function, which is the main entry point for the CLI command,
and a `rich_markdown_callback()` function for updating the live markdown display with chunks of text
received from the AI API.

Functions:
    * shellgenius(command_description: Tuple[str, ...]) -> None
        Generate and optionally execute a shell command based on the given command description
        using the gpt-4o-mini AI model.
        
    * rich_markdown_callback(chunk: str) -> None
        Update the live markdown display with the received chunk of text from the gpt-4o-mini AI
        API.
"""
import platform
import re
import subprocess
import sys

import click
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
import openai

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
@click.version_option()
@click.argument("command_description", type=str, nargs=-1)
@click.pass_context
def shellgenius(ctx, command_description):
    """
    Generate and optionally execute a shell command based on the given command description.

    Example:

        shellgenius create a new file called example.txt

        `touch example.txt`

        Explanation:

        - touch command is used to create a new file if it doesn't exist

        - example.txt is the name of the new file

        Do you want to execute this command? [Y/n]: y
    """
    if not command_description:
        click.echo(ctx.get_help())
        return

    command_description = " ".join(command_description)
    os_name = "macOS" if platform.system() == "Darwin" else platform.system()
    prompt = format_prompt(command_description, os_name)
    click.echo()

    with live:
        try:
            generated_text = chatgpt_request(
                prompt,
                stream=True,
                chunk_callback=rich_markdown_callback,
            )[0]

        except openai.error.RateLimitError as error:
            click.echo(f"{click.style('Error', fg='red')}: {error}")
            handle_rate_limit_error()
            sys.exit(1)
        except Exception as error:
            click.echo(f"{click.style('Error', fg='red')}: {error}")
            sys.exit(1)

    click.echo()
    click.echo(click.style("Be careful with your answer.", fg="blue"))
    execute_cmd = click.confirm("Do you want to execute this command?")

    if execute_cmd:
        cmd = re.search(r"`bash\n(.+?)\n`", generated_text).group(1)
        if cmd:
            try:
                subprocess.run(cmd, shell=True, check=True)
            except subprocess.CalledProcessError as error:
                click.echo(f"{click.style('Command failed', fg='red')}: {error}")
        else:
            click.echo(click.style("No command found", fg="blue"))
    else:
        click.echo(click.style("Command not executed", fg="red"))


def handle_rate_limit_error():
    """
    Provides guidance on how to handle a rate limit error.
    """
    click.echo()
    click.echo(
        click.style(
            (
                "You might not have set a usage rate limit in your"
                " OpenAI account settings. "
            ),
            fg="blue",
        )
    )
    click.echo(
        "If that's the case, you can set it"
        " here:\nhttps://platform.openai.com/account/billing/limits"
    )

    click.echo()
    click.echo(
        click.style(
            "If you have set a usage rate limit, please try the following steps:",
            fg="blue",
        )
    )
    click.echo("- Wait a few seconds before trying again.")
    click.echo()
    click.echo(
        "- Reduce your request rate or batch tokens. You can read the"
        " OpenAI rate limits"
        " here:\nhttps://platform.openai.com/account/rate-limits"
    )
    click.echo()
    click.echo(
        "- If you are using the free plan, you can upgrade to the paid"
        " plan"
        " here:\nhttps://platform.openai.com/account/billing/overview"
    )
    click.echo()
    click.echo(
        "- If you are using the paid plan, you can increase your usage"
        " rate limit"
        " here:\nhttps://platform.openai.com/account/billing/limits"
    )
