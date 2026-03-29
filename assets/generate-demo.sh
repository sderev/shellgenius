#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
repo_name=$(basename "$repo_root")
port_file="$HOME/.cache/chrome-debug/${repo_name}.port"
port=8765
shim_dir=""
server_pid=""
demo_home=".demo-home"
demo_bin=".demo-bin"

find_local_browser() {
    local candidate=""

    if [[ -n "${SHELLGENIUS_DEMO_CHROME:-}" ]] && [[ -x "${SHELLGENIUS_DEMO_CHROME}" ]]; then
        printf '%s\n' "${SHELLGENIUS_DEMO_CHROME}"
        return 0
    fi

    for candidate in \
        "$HOME/.cache/ms-playwright"/chromium-*/chrome-linux/chrome \
        "$(command -v chromium 2>/dev/null || true)" \
        "$(command -v chromium-browser 2>/dev/null || true)" \
        "$(command -v google-chrome 2>/dev/null || true)" \
        "$(command -v google-chrome-stable 2>/dev/null || true)"; do
        if [[ -n "$candidate" ]] && [[ -x "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    return 1
}

cleanup() {
    if [[ -n "$server_pid" ]] && kill -0 "$server_pid" 2>/dev/null; then
        kill "$server_pid" 2>/dev/null || true
        wait "$server_pid" 2>/dev/null || true
    fi

    if [[ -n "$shim_dir" ]]; then
        rm -rf "$shim_dir"
    fi

    rm -rf "$demo_home"
    rm -rf "$demo_bin"
}

trap cleanup EXIT

cd "$repo_root"

mkdir -p "$demo_home/.config/lmt"
cat > "$demo_home/.config/lmt/config.json" <<'EOF'
{
  "code_block_theme": "alabaster",
  "shellgenius": {
    "theme": "alabaster",
    "styles": {
      "markdown.code": "#325cc0",
      "markdown.code_block": "on #f0f0f0"
    }
  }
}
EOF

mkdir -p "$demo_bin"
cat > "$demo_bin/shellgenius" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export HOME="$repo_root/$demo_home"
export OPENAI_API_KEY="sk-demo-key"
export OPENAI_BASE_URL="http://127.0.0.1:$port/v1"
unset NO_COLOR
cd "$repo_root"
exec uv run shellgenius --no-stream "\$@"
EOF
chmod +x "$demo_bin/shellgenius"

uv run python assets/mock_server.py "$port" &
server_pid=$!

for _ in {1..50}; do
    if curl --max-time 2 -fsS "http://127.0.0.1:$port/health" >/dev/null 2>&1; then
        break
    fi
    sleep 0.1
done

if ! curl --max-time 2 -fsS "http://127.0.0.1:$port/health" >/dev/null 2>&1; then
    echo "Mock server did not become ready." >&2
    exit 1
fi

shim_dir=$(mktemp -d)
browser_binary=""
real_bash="$(command -v bash)"
if browser_binary=$(find_local_browser); then
    ln -s "$browser_binary" "$shim_dir/chrome"
else
    if [[ ! -f "$port_file" ]]; then
        echo "No local Chromium/Chrome binary found and no chrome-debug session tracked for $repo_name." >&2
        echo "Set SHELLGENIUS_DEMO_CHROME, install a local browser, or start chrome-debug once from this worktree." >&2
        exit 1
    fi

    for _ in {1..50}; do
        browser_port=""
        if [[ -f "$port_file" ]]; then
            browser_port=$(<"$port_file")
        fi
        if [[ -n "$browser_port" ]] \
            && curl --max-time 2 -fsS "http://127.0.0.1:$browser_port/json/version" >/dev/null 2>&1; then
            break
        fi
        sleep 0.1
    done

    browser_port=$(<"$port_file")
    if ! curl --max-time 2 -fsS "http://127.0.0.1:$browser_port/json/version" >/dev/null 2>&1; then
        echo "chrome-debug is tracked on port $browser_port but not responding." >&2
        echo "Reuse the existing session or restart it once, then rerun assets/generate-demo.sh." >&2
        exit 1
    fi

    cat >"$shim_dir/chrome" <<EOF
#!/usr/bin/env bash
set -euo pipefail
printf 'DevTools listening on ws://127.0.0.1:%s/devtools/browser/\n' "$browser_port"
while :; do
    sleep 3600
done
EOF
    chmod +x "$shim_dir/chrome"
fi

cat >"$shim_dir/bash" <<EOF
#!$real_bash
set -euo pipefail
exec "$real_bash" --noprofile --norc "\$@"
EOF
chmod +x "$shim_dir/bash"

PATH="$repo_root/$demo_bin:$shim_dir:$PATH" vhs assets/demo.tape

echo "Generated assets/demo.gif"
