# ShellGenius

ShellGenius turns task descriptions into shell commands.

In a terminal it prints a suggested command with an explanation and asks whether to run it. When `stdout` is piped it prints only the command; when `stdin` is at EOF it shows the response without prompting.

Part of the [LLM-Toolbox](https://github.com/sderev/llm-toolbox).

## Installation

Install with [`uv`](https://docs.astral.sh/uv/) (recommended):

```bash
uv tool install shellgenius
```

Or with `pip`:

```bash
python3 -m pip install shellgenius
```

## OpenAI API key

ShellGenius requires an OpenAI API key. Obtain one at [OpenAI's website](https://platform.openai.com/settings/organization/api-keys).

The quickest way to store it:

```bash
shellgenius key set
```

This writes the key to `~/.config/lmt/key.env`. To edit it later:

```bash
shellgenius key edit
```

To configure the key manually on macOS or Linux:

```bash
mkdir -p ~/.config/lmt
cat <<'EOF' > ~/.config/lmt/key.env
OPENAI_API_KEY="your-api-key-here"
EOF
chmod 600 ~/.config/lmt/key.env
```

ShellGenius can also use the `OPENAI_API_KEY` environment variable. It checks that first, then `~/.config/lmt/key.env`.

If you want your shell to reuse the same key, load it from the file in your shell startup instead of pasting the raw key into `.bashrc` or `.zshrc`:

```bash
if [ -f "$HOME/.config/lmt/key.env" ]; then
  . "$HOME/.config/lmt/key.env"
  export OPENAI_API_KEY
fi
```

On Windows (the `shellgenius key set` command also works there):

```powershell
setx OPENAI_API_KEY your_key
```

## Usage

Generate a command:

```bash
shellgenius "list the ten largest files here"
```

When `stdout` is not a TTY, ShellGenius prints only the generated command so it stays safe to pipe:

```bash
cmd=$(shellgenius "find all TODO comments")
shellgenius "find all TODO comments" | bash
shellgenius "list all .log files" | bash | xargs wc -l
```

Use `--raw` for the full response as plain text. Use `--rich` to force Rich formatting in a terminal; in a pipe it falls back to plain text. Use `--cmd` to print only the command in any context.

## Options

| Flag | Effect |
|---|---|
| `-m`, `--model` | Model to use (default: `gpt-5.4-mini`). Run `shellgenius models` to list options. |
| `--no-stream` | Disable live Rich streaming. |
| `-r`, `--raw` | Print the full response as plain text. |
| `-R`, `--rich` | Force Rich formatting in a TTY; fall back to plain text otherwise. |
| `--cmd` | Print only the command, even in a TTY. |
| `--tokens` | Print prompt token count and estimated cost, then exit. |

## Shell Completion

Bash:

```bash
eval "$(_SHELLGENIUS_COMPLETE=bash_source shellgenius)"
```

Zsh:

```bash
eval "$(_SHELLGENIUS_COMPLETE=zsh_source shellgenius)"
```

If you prefer checked-in scripts, this repo also includes `completion/_complete_shellgenius.bash` and `completion/_complete_shellgenius.zsh`.

## Model Selection

List supported models and their short aliases:

```bash
shellgenius models
```

Use an alias with `-m`:

```bash
shellgenius -m 4.1 "list the ten largest files"
shellgenius -m 5.4-mini "find all TODO comments"
```

## Customizing Colors

ShellGenius reads `~/.config/lmt/config.json` for two optional keys:

* `code_block_theme` for fenced code blocks. Any [Pygments style](https://pygments.org/styles/) name works, plus the built-in `alabaster` theme.
* `inline_code_theme` for inline code. Use any Rich style string, such as `"#325cc0 on #f0f0f0"`.

Example:

```json
{
  "code_block_theme": "alabaster",
  "inline_code_theme": "#325cc0 on #f0f0f0"
}
```

These settings affect Rich output only. Raw (`--raw`) and command-only (`--cmd`) output are unchanged. If the config file is missing or unreadable, Rich's built-in defaults are used.

## License

ShellGenius is released under the [Apache 2.0 Licence](LICENSE).

<https://github.com/sderev/shellgenius>
