# ShellGenius

ShellGenius turns task descriptions into shell commands. Describe what you need and it suggests a command, explains it, and offers to run it.

Part of the [lmtoolbox](https://github.com/sderev/lmtoolbox).

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

ShellGenius also honors the `OPENAI_API_KEY` environment variable (checked first, before `~/.config/lmt/key.env`).

On Windows (the `shellgenius key set` command also works there):

```powershell
setx OPENAI_API_KEY your_key
```

## Usage

Generate a command:

```bash
shellgenius "list the ten largest files here"
```

![ShellGenius demo](assets/demo.gif)

The demo above uses canned responses from `assets/mock_server.py`. Regenerate it with `assets/generate-demo.sh`.

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

Enable Click's generated completion for flags and explicit subcommand paths:

Bash:

```bash
eval "$(_SHELLGENIUS_COMPLETE=bash_source shellgenius)"
```

Zsh:

```bash
eval "$(_SHELLGENIUS_COMPLETE=zsh_source shellgenius)"
```

This covers cases such as `shellgenius --<TAB>` and `shellgenius key s<TAB>`.
Because the default command treats the first bare token as prompt text, type full subcommand names instead of expecting top-level discovery from `shellgenius k<TAB>` or `shellgenius m<TAB>`.

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

ShellGenius reads `~/.config/lmt/config.json`.

Legacy `lmterminal` compatibility keys still work:

* `code_block_theme` for fenced code blocks. Any [Pygments style](https://pygments.org/styles/) name works, plus the built-in `alabaster` and `alabaster-shellgenius` themes.
* `inline_code_theme` for visible inline code. Use any Rich style string, such as `"#325cc0 on #f0f0f0"`.

ShellGenius also supports an optional nested `shellgenius` block:

* `shellgenius.theme` selects ShellGenius's own preset and renderer behavior. `default`, `alabaster`, and `alabaster-shellgenius` are built in. Any valid Pygments theme name also works here for ShellGenius's fenced code blocks without changing the shared top-level `code_block_theme`.
* `shellgenius.styles` overrides individual Rich semantic styles, such as `markdown.h1`, `markdown.code`, or `markdown.code_block`. `markdown.code` overrides the top-level `inline_code_theme` for ShellGenius only. When a ShellGenius command-block preset is active, `markdown.code_block` controls that block's background in live and non-streamed TTY output.

Example:

```json
{
  "code_block_theme": "alabaster",
  "inline_code_theme": "#325cc0 on #f0f0f0",
  "shellgenius": {
    "theme": "alabaster",
    "styles": {
      "markdown.code_block": "on #f0f0f0",
      "markdown.h1": "bold #325cc0"
    }
  }
}
```

The top-level `code_block_theme` and `inline_code_theme` keep their shared `lmterminal` compatibility meaning. The nested `shellgenius` block only changes ShellGenius, so you can keep `code_block_theme: "alabaster"` for other tools while still enabling ShellGenius's `alabaster` command-block renderer. Invalid `shellgenius.styles` entries are ignored one by one, so one bad override does not discard valid siblings.

The built-in `alabaster` preset keeps the upstream `#f8f8f8` syntax background. If you want a darker ShellGenius command block, add it explicitly with `shellgenius.styles`, for example `{"markdown.code_block": "on #f0f0f0"}`. Legacy top-level `code_block_theme: "alabaster-shellgenius"` is still honored, but new config should prefer `shellgenius.theme`.

These settings affect Rich output only. Raw (`--raw`) and command-only (`--cmd`) output are unchanged. If the config file is missing or unreadable, Rich's built-in defaults are used.

## License

ShellGenius is released under the [Apache 2.0 Licence](LICENSE).

<https://github.com/sderev/shellgenius>
