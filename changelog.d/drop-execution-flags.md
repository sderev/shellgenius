### Removed

* `-y`/`--yes` and `-x`/`--execute` flags. Execution now requires the interactive confirmation prompt (`Execute this command? [y/N]`). Piped stdin is supported when `stdout` is a TTY (e.g., `printf 'y\n' | shellgenius "task"`).
