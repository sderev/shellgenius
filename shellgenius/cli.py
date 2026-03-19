from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field

import click
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

from .gpt_integration import RateLimitError, chatgpt_request, format_prompt
from .response_parser import (
    ParsedShellResponse,
    ShellGeniusResponseError,
    parse_shellgenius_response,
    validate_executable_shell_response,
)

DEFAULT_MODEL = "gpt-5.4-mini"


@dataclass(frozen=True, slots=True)
class TTYState:
    stdin: bool
    stdout: bool
    stderr: bool

    @property
    def can_prompt(self) -> bool:
        return self.stdin and self.stdout

    @property
    def can_stream_live(self) -> bool:
        return self.stdout


def get_tty_state() -> TTYState:
    return TTYState(
        stdin=sys.stdin.isatty(),
        stdout=sys.stdout.isatty(),
        stderr=sys.stderr.isatty(),
    )


@dataclass(slots=True)
class LiveMarkdownCallback:
    live: Live
    chunks: list[str] = field(default_factory=list)

    @property
    def has_output(self) -> bool:
        return bool("".join(self.chunks))

    def __call__(self, chunk: str) -> None:
        if not chunk:
            return
        self.chunks.append(chunk)
        self.live.update(Markdown("".join(self.chunks)))


def echo_error(message: str) -> None:
    click.echo(f"{click.style('Error', fg='red')}: {message}", err=True)


def parse_generated_command(generated_text: str) -> ParsedShellResponse:
    try:
        parsed_response = parse_shellgenius_response(generated_text)
        validate_executable_shell_response(parsed_response)
        return parsed_response
    except ShellGeniusResponseError as error:
        raise click.ClickException(str(error) or "No command found.") from error


def render_response(
    generated_text: str,
    *,
    tty_state: TTYState,
    plain: bool,
    command_only: bool,
) -> None:
    if command_only:
        parsed_response = parse_generated_command(generated_text)
        click.echo(parsed_response.command)
        return

    if plain or not tty_state.stdout:
        click.echo(generated_text.rstrip("\n"))
        return

    Console().print(Markdown(generated_text))


def should_stream_live(
    *,
    tty_state: TTYState,
    plain: bool,
    command_only: bool,
    no_stream: bool,
) -> bool:
    return tty_state.can_stream_live and not plain and not command_only and not no_stream


def resolve_execution_command(parsed_response: ParsedShellResponse) -> list[str]:
    fence_language = (
        parsed_response.fence_language.lower() if parsed_response.fence_language else None
    )

    if platform.system() == "Windows":
        if fence_language in {None, "powershell", "shell"}:
            return ["powershell.exe", "-NoProfile", "-Command", parsed_response.command]

        raise click.ClickException(
            "`--execute` cannot run "
            f"`{parsed_response.fence_language}` fences on Windows. "
            "Regenerate with `powershell`, `shell`, or no language."
        )

    shell_name = "sh" if fence_language in {None, "shell"} else fence_language
    if shell_name == "powershell":
        raise click.ClickException(
            "`--execute` cannot run `powershell` fences on this platform. "
            "Regenerate with `bash`, `sh`, `zsh`, `shell`, or no language."
        )

    executable = shutil.which(shell_name)
    if executable is None:
        raise click.ClickException(
            f"`--execute` requires `{shell_name}` to be installed to run this response."
        )

    return [executable, "-c", parsed_response.command]


def run_generated_command(parsed_response: ParsedShellResponse) -> None:
    subprocess.run(resolve_execution_command(parsed_response), check=True)


@click.command()
@click.version_option()
@click.argument("command_description", type=str, nargs=-1)
@click.option(
    "--model",
    "-m",
    default=DEFAULT_MODEL,
    show_default=True,
    help="Model to use for the request.",
)
@click.option("--no-stream", is_flag=True, help="Disable live streaming.")
@click.option("--plain", "-p", is_flag=True, help="Print plain text instead of Rich output.")
@click.option("--command-only", "-c", is_flag=True, help="Print only the generated command.")
@click.option("--execute", "-x", is_flag=True, help="Execute the generated command.")
@click.option("--yes", "-y", is_flag=True, help="Skip the execution confirmation prompt.")
@click.pass_context
def shellgenius(ctx, command_description, model, no_stream, plain, command_only, execute, yes):
    """
    Generate a shell command from a natural-language task description.
    """
    if not command_description:
        click.echo(ctx.get_help())
        return

    if yes and not execute:
        raise click.UsageError("`--yes` can only be used together with `--execute`.")

    if command_only and execute:
        raise click.UsageError("`--command-only` cannot be used together with `--execute`.")

    tty_state = get_tty_state()
    plain = plain or not tty_state.stdout

    if execute and not yes and not tty_state.can_prompt:
        raise click.UsageError("`--execute` requires `--yes` when stdin or stdout is not a TTY.")

    command_description = " ".join(command_description)
    os_name = "macOS" if platform.system() == "Darwin" else platform.system()
    prompt = format_prompt(command_description, os_name)
    use_live_stream = should_stream_live(
        tty_state=tty_state,
        plain=plain,
        command_only=command_only,
        no_stream=no_stream,
    )

    try:
        if use_live_stream:
            live = Live(Markdown(""), console=Console())
            live_callback = LiveMarkdownCallback(live)
            with live:
                generated_text = chatgpt_request(
                    prompt,
                    model=model,
                    stream=True,
                    chunk_callback=live_callback,
                )[0]
            if live_callback.has_output:
                click.echo()
            elif generated_text:
                render_response(
                    generated_text,
                    tty_state=tty_state,
                    plain=plain,
                    command_only=command_only,
                )
        else:
            generated_text = chatgpt_request(
                prompt,
                model=model,
                stream=False,
            )[0]
            render_response(
                generated_text,
                tty_state=tty_state,
                plain=plain,
                command_only=command_only,
            )
    except RateLimitError as error:
        echo_error(str(error))
        handle_rate_limit_error()
        raise SystemExit(1) from error
    except click.ClickException:
        raise
    except Exception as error:
        echo_error(str(error))
        raise SystemExit(1) from error

    if not execute:
        return

    parsed_response = parse_generated_command(generated_text)

    if not yes and not click.confirm("Execute this command?", default=False):
        click.echo("Not executed.")
        return

    try:
        run_generated_command(parsed_response)
    except subprocess.CalledProcessError as error:
        raise click.ClickException(f"Command failed: {error}") from error


def handle_rate_limit_error() -> None:
    click.echo("", err=True)
    click.echo(
        click.style(
            "You may need to set a usage limit in your OpenAI account settings.",
            fg="blue",
        ),
        err=True,
    )
    click.echo("https://platform.openai.com/account/billing/limits", err=True)

    click.echo("", err=True)
    click.echo(
        click.style("If the limit is already set, try:", fg="blue"),
        err=True,
    )
    click.echo("* Wait a few seconds, then try again.", err=True)
    click.echo("* Lower your request rate or token usage.", err=True)
    click.echo("  https://platform.openai.com/account/rate-limits", err=True)
    click.echo("* Check your billing plan and usage limits.", err=True)
    click.echo("  https://platform.openai.com/account/billing/overview", err=True)
