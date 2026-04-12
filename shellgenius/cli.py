from __future__ import annotations

import os
import platform
import select
import shutil
import subprocess
import sys
from dataclasses import dataclass, field

import click
from click_default_group import DefaultGroup
from rich.live import Live

from .api_key import edit_key, set_key
from .gpt_integration import (
    RateLimitError,
    chatgpt_request,
    estimate_prompt_cost,
    format_prompt,
    num_tokens_from_messages,
)
from .response_parser import (
    ParsedShellResponse,
    ShellGeniusResponseError,
    parse_shellgenius_response,
    validate_executable_shell_response,
)
from .theme import LmtTheme, load_lmt_theme, make_console, make_renderable

DEFAULT_MODEL = "gpt-5.4-mini"

VALID_MODELS: dict[str, tuple[str, ...]] = {
    "gpt-4.1": ("4.1",),
    "gpt-4.1-mini": ("4.1-mini",),
    "gpt-4.1-nano": ("4.1-nano",),
    "gpt-4o": ("4o",),
    "gpt-4o-mini": ("4o-mini",),
    "gpt-5": ("5",),
    "gpt-5-mini": ("5-mini",),
    "gpt-5-nano": ("5-nano",),
    "gpt-5.4": ("5.4",),
    "gpt-5.4-mini": ("5.4-mini",),
    "gpt-5.4-nano": ("5.4-nano",),
}


def validate_model_name(ctx, param, value):
    """Resolve aliases and validate model names."""
    name = value.lower()
    for canonical, aliases in VALID_MODELS.items():
        if name == canonical or name in aliases:
            return canonical
    raise click.BadParameter(
        f"{click.style('Invalid model name.', fg='red')}\n"
        f"{click.style('Use ', fg='red')}"
        f"{click.style('shellgenius models', fg='blue')}"
        f"{click.style(' to list supported models and aliases.', fg='red')}"
    )


def _list_models() -> None:
    for model, aliases in VALID_MODELS.items():
        click.echo(model)
        click.echo(f"  Alias: {', '.join(aliases)}")


@dataclass(frozen=True, slots=True)
class TTYState:
    stdin: bool
    stdout: bool
    stderr: bool

    @property
    def can_prompt(self) -> bool:
        """Stdout must be a TTY so the user can see the prompt.

        Stdin readiness is checked separately so piped confirmations keep
        working without aborting when stdin is already at EOF.
        """
        return self.stdout

    @property
    def can_stream_live(self) -> bool:
        return self.stdout


def get_tty_state() -> TTYState:
    return TTYState(
        stdin=sys.stdin.isatty(),
        stdout=sys.stdout.isatty(),
        stderr=sys.stderr.isatty(),
    )


def _seekable_stream_has_input(stream) -> bool | None:
    try:
        if not stream.seekable():
            return None
        position = stream.tell()
        chunk = stream.read(1)
        stream.seek(position)
    except (AttributeError, OSError, ValueError):
        return None

    return bool(chunk)


def _posix_stream_can_prompt(stream, fd: int) -> bool:
    try:
        readable = bool(select.select([fd], [], [], 0)[0])
    except (OSError, ValueError):
        return False

    if not readable:
        return True

    buffer = getattr(stream, "buffer", None)
    if buffer is None or not hasattr(buffer, "peek"):
        return False

    previous_blocking = os.get_blocking(fd)
    try:
        os.set_blocking(fd, False)
        return bool(buffer.peek(1))
    except (BlockingIOError, OSError, ValueError):
        return True
    finally:
        os.set_blocking(fd, previous_blocking)


def _windows_stream_can_prompt(fd: int) -> bool:
    try:
        import ctypes
        import msvcrt
        from ctypes import wintypes
    except ImportError:
        return False

    handle = msvcrt.get_osfhandle(fd)
    available = wintypes.DWORD()
    ok = ctypes.windll.kernel32.PeekNamedPipe(
        wintypes.HANDLE(handle),
        None,
        0,
        None,
        ctypes.byref(available),
        None,
    )
    if ok:
        return True

    return False


def stdin_has_prompt_input(stream=None) -> bool:
    """Return whether ``stream`` can still answer a confirmation prompt."""
    stream = sys.stdin if stream is None else stream

    if stream.closed:
        return False

    if stream.isatty():
        return True

    seekable_result = _seekable_stream_has_input(stream)
    if seekable_result is not None:
        return seekable_result

    try:
        fd = stream.fileno()
    except (AttributeError, OSError, ValueError):
        return False

    if os.name == "nt":
        return _windows_stream_can_prompt(fd)

    return _posix_stream_can_prompt(stream, fd)


@dataclass(slots=True)
class LiveMarkdownCallback:
    live: Live
    theme: LmtTheme
    chunks: list[str] = field(default_factory=list)

    @property
    def has_output(self) -> bool:
        return bool(self.chunks)

    def __call__(self, chunk: str) -> None:
        if not chunk:
            return
        self.chunks.append(chunk)
        self.live.update(make_renderable("".join(self.chunks), self.theme))


def echo_error(message: str) -> None:
    click.secho(f"Error: {message}", fg="red", err=True)


def style_bad_usage(message: str) -> str:
    return click.style(message, fg="red")


def parse_generated_command(generated_text: str) -> ParsedShellResponse:
    try:
        parsed_response = parse_shellgenius_response(generated_text)
        validate_executable_shell_response(parsed_response)
        return parsed_response
    except ShellGeniusResponseError as error:
        raise click.ClickException(str(error) or "No command found.") from error


def parse_executable_command(generated_text: str) -> ParsedShellResponse:
    parsed_response = parse_generated_command(generated_text)
    resolve_execution_command(parsed_response)
    return parsed_response


def render_response(
    generated_text: str,
    *,
    tty_state: TTYState,
    raw: bool,
    rich_flag: bool,
    command_only: bool,
    theme: LmtTheme,
    leading_blank_line: bool = True,
) -> None:
    if command_only:
        parsed_response = parse_executable_command(generated_text)
        click.echo(parsed_response.command)
        return

    if tty_state.stdout and (rich_flag or not raw):
        if leading_blank_line:
            click.echo()
        make_console(theme).print(make_renderable(generated_text, theme))
        return

    click.echo(generated_text.rstrip("\n"))


def should_stream_live(
    *,
    tty_state: TTYState,
    raw: bool,
    command_only: bool,
    no_stream: bool,
) -> bool:
    return tty_state.can_stream_live and not raw and not command_only and not no_stream


def resolve_execution_command(parsed_response: ParsedShellResponse) -> list[str]:
    fence_language = (
        parsed_response.fence_language.lower() if parsed_response.fence_language else None
    )

    if platform.system() == "Windows":
        if fence_language in {None, "powershell", "shell"}:
            return ["powershell.exe", "-NoProfile", "-Command", parsed_response.command]

        raise click.ClickException(
            f"Cannot run `{parsed_response.fence_language}` fences on Windows. "
            "Regenerate with `powershell`, `shell`, or no language."
        )

    shell_name = "sh" if fence_language in {None, "shell"} else fence_language
    if shell_name == "powershell":
        raise click.ClickException(
            "Cannot run `powershell` fences on this platform. "
            "Regenerate with `bash`, `sh`, `zsh`, `shell`, or no language."
        )

    executable = shutil.which(shell_name)
    if executable is None:
        raise click.ClickException(f"Cannot execute: `{shell_name}` is not installed.")

    return [executable, "-c", parsed_response.command]


def run_generated_command(parsed_response: ParsedShellResponse) -> None:
    subprocess.run(resolve_execution_command(parsed_response), check=True)


class _GroupAliasContext(click.Context):
    """Context whose ``command_path`` resolves to the parent group's path."""

    @property
    def command_path(self):
        if self.parent is not None:
            return self.parent.command_path
        return super().command_path


class DefaultCommand(click.Command):
    """Command that presents itself as the parent group in usage/error text."""

    context_class = _GroupAliasContext


class ShellGeniusGroup(DefaultGroup):
    """Default-group variant that keeps prompt routing and help coherent."""

    def _default_command(self) -> click.Command:
        return self.commands[self.default_cmd_name]

    def _default_command_context(self, ctx: click.Context) -> click.Context:
        return self._default_command().make_context(
            ctx.info_name or ctx.command_path,
            [],
            parent=ctx,
            resilient_parsing=True,
        )

    def _looks_like_subcommand_invocation(
        self,
        command: click.Command,
        args: list[str],
    ) -> bool:
        if isinstance(command, click.Group):
            if not args:
                return True

            first_arg = args[0]
            if first_arg.startswith("-"):
                return True

            subcommand = command.commands.get(first_arg)
            if subcommand is None:
                return False

            return self._looks_like_subcommand_invocation(subcommand, args[1:])

        # Once a full subcommand path resolves to a leaf command, keep the call
        # on the subcommand path and let Click handle malformed arguments
        # locally. Falling back to the default prompt here can leak sensitive
        # tokens such as API keys into the normal prompt flow.
        return True

    def _should_route_to_default_command(self, args: list[str]) -> bool:
        if not args:
            return False

        command_name = args[0]
        if command_name == self.default_cmd_name or command_name not in self.commands:
            return False

        return not self._looks_like_subcommand_invocation(
            self.commands[command_name],
            args[1:],
        )

    def resolve_command(self, ctx, args):
        if self._should_route_to_default_command(args):
            args = [self.default_cmd_name, *args]

        return super().resolve_command(ctx, args)

    def format_usage(self, ctx, formatter):
        default_ctx = self._default_command_context(ctx)
        usage_pieces = self._default_command().collect_usage_pieces(default_ctx)
        formatter.write_usage(ctx.command_path, " ".join(usage_pieces))

    def format_help(self, ctx, formatter):
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        self.format_options(ctx, formatter)
        self.format_commands(ctx, formatter)
        self.format_epilog(ctx, formatter)

    def format_help_text(self, ctx, formatter):
        self._default_command().format_help_text(self._default_command_context(ctx), formatter)

    def format_options(self, ctx, formatter):
        help_records = []

        for param in self.get_params(ctx):
            record = param.get_help_record(ctx)
            if record is not None:
                help_records.append(record)

        default_ctx = self._default_command_context(ctx)
        for param in self._default_command().get_params(default_ctx):
            if isinstance(param, click.Option) and param.name == "help":
                continue

            record = param.get_help_record(default_ctx)
            if record is not None:
                help_records.append(record)

        if help_records:
            with formatter.section("Options"):
                formatter.write_dl(help_records)

    def format_commands(self, ctx, formatter):
        command_records = []
        for command_name in self.list_commands(ctx):
            if command_name == self.default_cmd_name:
                continue

            command = self.get_command(ctx, command_name)
            if command is None or command.hidden:
                continue

            command_records.append((command_name, command.get_short_help_str()))

        if command_records:
            with formatter.section("Commands"):
                formatter.write_dl(command_records)


@click.group(
    cls=ShellGeniusGroup,
    default="prompt",
    default_if_no_args=True,
    epilog="Run `shellgenius prompt --help` for the explicit default command.",
)
@click.version_option()
def shellgenius():
    """
    Generate a shell command from a natural-language task description.

    Run ``shellgenius models`` to list supported models and aliases.
    """


@shellgenius.command()
def models():
    """List supported models and their aliases."""
    _list_models()


@shellgenius.group()
def key():
    """Manage the OpenAI API key."""


@key.command(name="set")
def key_set():
    """Set the OpenAI API key."""
    set_key()


@key.command(name="edit")
def key_edit():
    """Edit the OpenAI API key."""
    edit_key()


@shellgenius.command(cls=DefaultCommand)
@click.argument("command_description", type=str, nargs=-1)
@click.option(
    "--model",
    "-m",
    default=DEFAULT_MODEL,
    show_default=True,
    callback=validate_model_name,
    help="Model to use (run `shellgenius models` to list options).",
)
@click.option("--no-stream", is_flag=True, help="Disable live streaming.")
@click.option("--raw", "-r", is_flag=True, help="Print plain text instead of Rich output.")
@click.option(
    "--rich",
    "-R",
    "rich_flag",
    is_flag=True,
    help="Force Rich formatting in a TTY; fall back to plain text otherwise.",
)
@click.option("--cmd", "command_only", is_flag=True, help="Print only the generated command.")
@click.option(
    "--tokens", is_flag=True, help="Print prompt token count and estimated cost, then exit."
)
@click.pass_context
def prompt(
    ctx,
    command_description,
    model,
    no_stream,
    raw,
    rich_flag,
    command_only,
    tokens,
):
    """Generate a shell command from a natural-language task description.

    Other commands: ``shellgenius models``, ``shellgenius key set``.
    """
    if not command_description:
        click.echo(ctx.get_help())
        return

    tty_state = get_tty_state()

    if raw and rich_flag:
        raise click.BadOptionUsage(
            option_name="rich",
            message=style_bad_usage("You cannot use `--raw` and `--rich` at the same time."),
        )

    plain_output = raw or (rich_flag and not tty_state.stdout)

    # Non-TTY default: bare command output (pipe-safe)
    pipe_mode = command_only or (not tty_state.stdout and not plain_output)

    command_description = " ".join(command_description)
    os_name = "macOS" if platform.system() == "Darwin" else platform.system()
    messages = format_prompt(command_description, os_name)

    if tokens:
        token_count = num_tokens_from_messages(messages, model)
        cost = estimate_prompt_cost(messages, model)
        click.echo(f"Prompt tokens: {click.style(str(token_count), fg='yellow')}")
        if cost is not None:
            click.echo(
                f"Estimated cost for {click.style(model, fg='blue')}:"
                f" {click.style(f'${cost}', fg='yellow')}"
            )
        else:
            click.echo(f"Cost unavailable for {click.style(model, fg='blue')}.")
        return

    use_live_stream = should_stream_live(
        tty_state=tty_state,
        raw=plain_output,
        command_only=command_only,
        no_stream=no_stream,
    )

    theme = load_lmt_theme()

    try:
        if use_live_stream:
            console = make_console(theme)
            live = Live(make_renderable("", theme), console=console)
            live_callback = LiveMarkdownCallback(live, theme)
            click.echo()
            with live:
                generated_text = chatgpt_request(
                    messages,
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
                    raw=plain_output,
                    rich_flag=rich_flag,
                    command_only=pipe_mode,
                    theme=theme,
                    leading_blank_line=False,
                )
        else:
            generated_text = chatgpt_request(
                messages,
                model=model,
                stream=False,
            )[0]
            render_response(
                generated_text,
                tty_state=tty_state,
                raw=plain_output,
                rich_flag=rich_flag,
                command_only=pipe_mode,
                theme=theme,
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

    if command_only:
        return

    if not tty_state.can_prompt or not stdin_has_prompt_input():
        return

    parsed_response = parse_generated_command(generated_text)

    click.echo()

    if not click.confirm("Execute this command?", default=False):
        click.echo("Not executed.")
        return

    try:
        run_generated_command(parsed_response)
    except subprocess.CalledProcessError as error:
        raise click.ClickException(f"Command failed: {error}") from error


def handle_rate_limit_error() -> None:
    click.echo(err=True)
    click.secho(
        "You may need to set a usage limit in your OpenAI account settings.",
        fg="blue",
        err=True,
    )
    click.echo("https://platform.openai.com/account/billing/limits", err=True)
    click.echo(err=True)
    click.secho("If the limit is already set, try:", fg="blue", err=True)
    click.echo(
        "* Wait a few seconds, then try again.\n"
        "* Lower your request rate or token usage.\n"
        "  https://platform.openai.com/account/rate-limits\n"
        "* Check your billing plan and usage limits.\n"
        "  https://platform.openai.com/account/billing/overview",
        err=True,
    )
