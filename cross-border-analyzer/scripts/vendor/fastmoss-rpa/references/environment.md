# Environment & Shell Quirks (fastmoss, unified)

Read this before writing any shell command or new `evaluate` JS for this skill.
The project typically runs on **Windows + bash shell**; the same rules apply to
any platform, but several "normal Linux" idioms break silently on Windows.

## Paths

- Use forward slashes (`/`) in all paths. Backslashes break JSON strings.
- Use `/dev/null`, NOT `NUL` (Windows) — bash handles `/dev/null` correctly.
- The `bsk` CLI is at `~/.local/bin/bsk` (on PATH). The BrowserSkill browser
  extension must be installed in Chrome/Edge and connected (`bsk status` →
  `browsers connected: N`).
- Output paths are user-supplied via `--out` / `--out-md`. The bundled scripts
  accept any path and create parent dirs as needed.

## BrowserSkill (bsk) transport

- No local HTTP daemon — bsk drives the user's real Chrome/Edge via the
  BrowserSkill extension and reuses the logged-in session (cookies + origin).
  This is why the `market` API fetchers work without an API key.
- CLI: `bsk` (`session start/stop`, `navigate`, `evaluate`, `screenshot`,
  `status` subcommands).
- One Chrome/Edge extension connects to bsk; verify with `bsk status`
  (`browsers connected: N`). If `0`, ask the user to open their browser and
  click the BrowserSkill extension to connect.
- For ad-hoc drives from the shell:
  ```bash
  bsk session start --json
  bsk navigate "https://www.fastmoss.com/zh/e-commerce/newProducts" --session <id> --wait-until load
  bsk evaluate "document.title" --session <id>
  bsk session stop <id>
  ```
  The bundled Python scripts call `bsk` directly via subprocess
  (`bridge_browserskill.py`).

## Bash + JSON escaping rules

### Heredoc `<<EOF` with JS regex: BREAKS

Bash eats one backslash layer, so `/\n+/g` arrives malformed → extension returns
`"Invalid regular expression: missing /"`.

**Fix**: prefer `.split('\n')` over `.replace(/\n+/g, ...)`. For complex JS,
write it to a `.js` file and POST via Python `urllib` (no shell layer).

### `curl -d @file.json`: works for any payload

Save the JSON request body to a file, then `curl -d @body.json`. Bypasses shell
escaping entirely.

### Screenshots

`bsk screenshot --session <id> --out out.jpeg` writes a JPEG directly — no `jq`
and no base64 decode needed.

## Python file encoding

On Windows, Python defaults to GBK for `open()` and `pathlib.Path.read_text()`.
CSVs produced by this skill are `utf-8-sig` (BOM) for Excel compatibility. Always
read with explicit encoding:

```python
with open('your.csv', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
```

## Browser session

- Session name (e.g. `"fastmoss-products"`, `"fastmoss-market"`) keeps the bsk
  session isolated from other browser work. Override via `--session` if running
  multiple projects in parallel.
- Sessions auto-close when the Python script exits (atexit). To force-close:
  `bsk session stop <id>` or `bsk session stop --all`.
- `navigate` opens a tab in the session whether or not it pre-exists.
- `nav_sleep` (after navigation) defaults to 5–6 s; `page_sleep` (between pages)
  defaults to 3.5 s. Increase if you see 0-row pages (SPA hydration lag).
