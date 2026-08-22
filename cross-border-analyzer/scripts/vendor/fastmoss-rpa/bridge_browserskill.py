"""BrowserSkill (bsk) transport adapter for FastMoss scrapers.

Replaces the old kimi-webbridge HTTP daemon (127.0.0.1:10086). Public API
mirrors the old kimi transport so the scrapers need almost no changes:

    from bridge_browserskill import call, evaluate, session_stop

    call(action, args, session) -> dict   # action in navigate/evaluate/screenshot/close_session
    evaluate(code, session)     -> parsed JSON (dict/list) or {"error": ...}/{"raw": ...}
    session_stop(name=None)     -> stop one named session, or all if name is None

A bsk session is started lazily on first use of a given `session` name and is
stopped automatically at process exit (atexit) or via an explicit session_stop().
"""
import json
import os
import shutil
import subprocess
import atexit
from pathlib import Path


def _resolve_bsk():
    """跨平台查找 bsk：优先环境变量，其次 PATH，最后 ~/.local/bin。"""
    env = os.environ.get("BSK_BIN")
    if env:
        return env
    found = shutil.which("bsk")
    if found:
        return found
    local = Path.home() / ".local/bin/bsk"
    return str(local) if local.exists() else "bsk"


BSK = _resolve_bsk()

# session name -> bsk session id (4-letter)
_SESSIONS = {}


def _start(name):
    p = subprocess.run([BSK, "session", "start", "--json"],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    if p.returncode != 0:
        raise RuntimeError(f"bsk session start failed: {p.stderr.strip()}")
    sid = json.loads(p.stdout)["session_id"]
    _SESSIONS[name] = sid
    return sid


def _sid(name):
    return _SESSIONS.get(name) or _start(name)


def call(action, args, session):
    sid = _sid(session)
    if action == "navigate":
        url = args.get("url", "")
        p = subprocess.run([BSK, "navigate", url, "--session", sid,
                            "--wait-until", "load", "--timeout", "30s"],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=45)
        return {"ok": p.returncode == 0, "data": p.stdout.strip()}
    if action == "evaluate":
        code = args.get("code", "")
        p = subprocess.run([BSK, "evaluate", code, "--session", sid, "--timeout", "30s"],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=45)
        out = (p.stdout or "").strip()
        if p.returncode != 0 or not out:
            return {"ok": False, "error": {"message": (p.stderr or "empty output").strip()}}
        # bsk prints the JSON value text directly (return-by-value). Wrap it to
        # match the old kimi shape {type: "string", value: <json>} so the
        # existing evaluate() wrapper can json.loads(data["value"]) unchanged.
        return {"ok": True, "data": {"type": "string", "value": out}}
    if action == "screenshot":
        out_path = args.get("path") or args.get("out")
        cmd = [BSK, "screenshot", "--session", sid]
        if out_path:
            cmd += ["--out", out_path]
        p = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=45)
        return {"ok": p.returncode == 0, "data": p.stdout.strip()}
    if action == "close_session":
        if session in _SESSIONS:
            subprocess.run([BSK, "session", "stop", _SESSIONS.pop(session)],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30)
        return {"ok": True}
    return {"ok": False, "error": {"message": f"unknown action: {action}"}}


def evaluate(code, session):
    res = call("evaluate", {"code": code}, session)
    if not res.get("ok"):
        return {"error": res.get("error", {}).get("message", "unknown")}
    data = res["data"]
    if isinstance(data, dict) and data.get("type") == "string":
        try:
            return json.loads(data["value"])
        except Exception:
            return {"raw": data.get("value")}
    return data


def session_stop(name=None):
    if name is None:
        for _n, _s in list(_SESSIONS.items()):
            subprocess.run([BSK, "session", "stop", _s], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=30)
        _SESSIONS.clear()
        return
    sid = _SESSIONS.pop(name, None)
    if sid:
        subprocess.run([BSK, "session", "stop", sid], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=30)


atexit.register(session_stop)
