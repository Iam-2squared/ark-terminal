from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

MUTATION_KEYS = (
    "orderSubmit",
    "orderCancel",
    "killSwitchChange",
    "strategyEdit",
    "brokerWrite",
    "excelOrderWrite",
    "rssOrderFunction",
)
MODEL_SCHEMA = "ARK_TERMINAL_UI_READ_MODEL_V1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso(value: Any) -> float | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def validate_read_model(model: Any) -> dict[str, Any]:
    if not isinstance(model, dict):
        raise ValueError("UI_READ_MODEL_OBJECT_REQUIRED")
    if model.get("schemaId") != MODEL_SCHEMA:
        raise ValueError("UI_READ_MODEL_SCHEMA_INVALID")
    if model.get("readOnly") is not True:
        raise ValueError("UI_READ_MODEL_NOT_READ_ONLY")
    capabilities = model.get("mutationCapabilities")
    if not isinstance(capabilities, dict):
        raise ValueError("UI_READ_MODEL_MUTATION_CAPABILITIES_REQUIRED")
    for key in MUTATION_KEYS:
        if capabilities.get(key) is not False:
            raise ValueError(f"UI_READ_MODEL_MUTATION_CAPABILITY_NOT_FALSE:{key}")
    return model


def project_observed_model(
    model: dict[str, Any],
    *,
    now_epoch: float | None = None,
    max_model_age_seconds: float = 15.0,
    refresh_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_read_model(model)
    projected = copy.deepcopy(model)
    now_epoch = time.time() if now_epoch is None else float(now_epoch)
    source = projected.setdefault("source", {})
    freshness = source.setdefault("freshness", {})
    timestamp = freshness.get("timestamp") or projected.get("generatedAt")
    timestamp_epoch = parse_iso(timestamp)
    if timestamp_epoch is None:
        age_seconds = None
        freshness["state"] = "INVALID"
    else:
        age_seconds = max(0.0, now_epoch - timestamp_epoch)
        freshness["ageSeconds"] = age_seconds
        if age_seconds > max_model_age_seconds:
            freshness["state"] = "STALE"

    if freshness.get("state") != "FRESH":
        system = projected.setdefault("system", {})
        system["health"] = "BLOCKED"
        system["tradeReadiness"] = "BLOCKED"
        home = projected.setdefault("home", {})
        if home.get("buyingPower") is not None:
            home["buyingPowerState"] = freshness.get("state", "INVALID")

    projected["localBridge"] = {
        "readOnly": True,
        "loopbackOnly": True,
        "observedAt": datetime.fromtimestamp(now_epoch, timezone.utc).isoformat(),
        "modelAgeSeconds": age_seconds,
        "maxModelAgeSeconds": max_model_age_seconds,
        "refresh": copy.deepcopy(refresh_state or {}),
        "mutationCapabilities": {key: False for key in MUTATION_KEYS},
    }
    return projected


class RefreshState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {
            "enabled": False,
            "running": False,
            "lastAttemptAt": None,
            "lastSuccessAt": None,
            "lastError": None,
        }

    def update(self, **values: Any) -> None:
        with self._lock:
            self._data.update(values)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._data)


class RefreshLoop(threading.Thread):
    def __init__(
        self,
        *,
        state: RefreshState,
        preview_script: Path,
        workbook_path: Path,
        model_path: Path,
        ownership_path: Path | None,
        interval_seconds: float,
    ) -> None:
        super().__init__(name="ark-ui2-readonly-refresh", daemon=True)
        self.state = state
        self.preview_script = preview_script
        self.workbook_path = workbook_path
        self.model_path = model_path
        self.ownership_path = ownership_path
        self.interval_seconds = interval_seconds
        self.stop_event = threading.Event()

    def stop(self) -> None:
        self.stop_event.set()

    def _powershell(self) -> str:
        return shutil.which("powershell.exe") or shutil.which("powershell") or shutil.which("pwsh") or ""

    def _command(self) -> list[str]:
        executable = self._powershell()
        if not executable:
            raise RuntimeError("POWERSHELL_NOT_FOUND")
        command = [
            executable,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(self.preview_script),
            "-WorkbookPath",
            str(self.workbook_path),
            "-UiReadModelPath",
            str(self.model_path),
        ]
        if self.ownership_path is not None:
            command.extend(["-OwnershipBaselinePath", str(self.ownership_path)])
        return command

    def _refresh_once(self) -> None:
        attempted_at = utc_now_iso()
        self.state.update(running=True, lastAttemptAt=attempted_at)
        try:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            result = subprocess.run(
                self._command(),
                cwd=str(self.preview_script.parent.parent),
                capture_output=True,
                text=True,
                timeout=max(15.0, self.interval_seconds * 2.0),
                creationflags=creationflags,
            )
            if result.returncode != 0:
                message = (result.stderr or result.stdout or "refresh failed").strip()
                raise RuntimeError(message[-1200:])
            self.state.update(
                running=False,
                lastSuccessAt=utc_now_iso(),
                lastError=None,
            )
        except Exception as exc:
            self.state.update(running=False, lastError=f"{type(exc).__name__}:{exc}")

    def run(self) -> None:
        self.state.update(enabled=True)
        while not self.stop_event.is_set():
            started = time.monotonic()
            self._refresh_once()
            elapsed = time.monotonic() - started
            wait = max(0.25, self.interval_seconds - elapsed)
            if self.stop_event.wait(wait):
                break


class ArkUiServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        handler: type[BaseHTTPRequestHandler],
        *,
        index_path: Path,
        overlay_path: Path,
        model_path: Path,
        max_model_age_seconds: float,
        refresh_state: RefreshState,
    ) -> None:
        super().__init__(address, handler)
        self.index_path = index_path
        self.overlay_path = overlay_path
        self.model_path = model_path
        self.max_model_age_seconds = max_model_age_seconds
        self.refresh_state = refresh_state


class Handler(BaseHTTPRequestHandler):
    server: ArkUiServer

    def _base_headers(self, content_type: str, length: int) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Ark-Read-Only", "true")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")

    def _send_bytes(self, payload: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self._base_headers(content_type, len(payload))
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._send_bytes(body, "application/json; charset=utf-8", status)

    def _index(self) -> None:
        source = self.server.index_path.read_text(encoding="utf-8-sig")
        marker = '<script src="/ark-readonly-overlay.js" defer></script>'
        if marker not in source:
            if "</body>" not in source:
                raise RuntimeError("UI_INDEX_BODY_END_MISSING")
            source = source.replace("</body>", marker + "</body>", 1)
        self._send_bytes(source.encode("utf-8"), "text/html; charset=utf-8")

    def _model(self) -> None:
        if not self.server.model_path.is_file():
            self._send_json(
                {
                    "ok": False,
                    "readOnly": True,
                    "code": "UI_READ_MODEL_FILE_MISSING",
                    "message": str(self.server.model_path),
                },
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
            return
        try:
            source = json.loads(self.server.model_path.read_text(encoding="utf-8-sig"))
            projected = project_observed_model(
                source,
                max_model_age_seconds=self.server.max_model_age_seconds,
                refresh_state=self.server.refresh_state.snapshot(),
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            self._send_json(
                {
                    "ok": False,
                    "readOnly": True,
                    "code": "UI_READ_MODEL_INVALID",
                    "message": f"{type(exc).__name__}:{exc}",
                },
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
            return
        self._send_json(projected)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        try:
            if path in ("/", "/index.html"):
                self._index()
                return
            if path == "/ark-readonly-overlay.js":
                self._send_bytes(
                    self.server.overlay_path.read_bytes(),
                    "text/javascript; charset=utf-8",
                )
                return
            if path == "/api/ui-read-model":
                self._model()
                return
            if path == "/health":
                self._send_json(
                    {
                        "ok": True,
                        "service": "ark-terminal-ui2-readonly",
                        "readOnly": True,
                        "loopbackOnly": True,
                        "mutationCapabilities": {key: False for key in MUTATION_KEYS},
                        "refresh": self.server.refresh_state.snapshot(),
                    }
                )
                return
            if path == "/favicon.ico":
                self.send_response(HTTPStatus.NO_CONTENT)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return
            self._send_json({"ok": False, "code": "NOT_FOUND"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._send_json(
                {
                    "ok": False,
                    "readOnly": True,
                    "code": "LOCAL_UI_SERVER_ERROR",
                    "message": f"{type(exc).__name__}:{exc}",
                },
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def do_POST(self) -> None:
        self._send_json(
            {"ok": False, "readOnly": True, "code": "READ_ONLY_METHOD_NOT_ALLOWED"},
            HTTPStatus.METHOD_NOT_ALLOWED,
        )

    do_PUT = do_POST
    do_PATCH = do_POST
    do_DELETE = do_POST

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stdout.write("[ark-ui2-readonly] " + (fmt % args) + "\n")


def build_parser(repo_root: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Serve Ark Terminal 2.0 with a loopback-only read-only UI model overlay.")
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument(
        "--model",
        type=Path,
        default=Path(r"C:\Ark\ui-readonly\ark-terminal-ui-read-model.json"),
    )
    parser.add_argument(
        "--workbook",
        type=Path,
        default=Path(r"C:\Ark\Ark_MSII_LiveSource.xlsx"),
    )
    parser.add_argument("--ownership", type=Path, default=None)
    parser.add_argument("--refresh-seconds", type=float, default=5.0)
    parser.add_argument("--max-model-age-seconds", type=float, default=15.0)
    parser.add_argument("--no-refresh", action="store_true")
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument(
        "--ui-root",
        type=Path,
        default=repo_root / "prototypes" / "ark-terminal-2-readonly" / "public",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parent.parent
    args = build_parser(repo_root).parse_args(argv)
    if not (1 <= args.port <= 65535):
        raise SystemExit("PORT_OUT_OF_RANGE")
    if args.refresh_seconds <= 0 or args.max_model_age_seconds <= 0:
        raise SystemExit("REFRESH_INTERVAL_OUT_OF_RANGE")

    ui_root = args.ui_root.resolve()
    index_path = ui_root / "index.html"
    overlay_path = ui_root / "ark-readonly-overlay.js"
    if not index_path.is_file():
        raise SystemExit(f"UI_INDEX_MISSING:{index_path}")
    if not overlay_path.is_file():
        raise SystemExit(f"UI_OVERLAY_MISSING:{overlay_path}")

    model_path = args.model.resolve()
    refresh_state = RefreshState()
    refresh_loop: RefreshLoop | None = None
    if not args.no_refresh:
        refresh_loop = RefreshLoop(
            state=refresh_state,
            preview_script=repo_root / "tools" / "Start-ArkUiReadOnlyPreview.ps1",
            workbook_path=args.workbook.resolve(),
            model_path=model_path,
            ownership_path=args.ownership.resolve() if args.ownership else None,
            interval_seconds=args.refresh_seconds,
        )
        refresh_loop.start()

    server = ArkUiServer(
        ("127.0.0.1", args.port),
        Handler,
        index_path=index_path,
        overlay_path=overlay_path,
        model_path=model_path,
        max_model_age_seconds=args.max_model_age_seconds,
        refresh_state=refresh_state,
    )

    url = f"http://127.0.0.1:{args.port}/"
    print("ARK_UI2_READ_ONLY_SERVER_READY")
    print(f"URL           : {url}")
    print(f"Model         : {model_path}")
    print(f"AutoRefresh   : {not args.no_refresh}")
    print(f"RefreshSeconds: {args.refresh_seconds}")
    print("LoopbackOnly  : TRUE")
    print("Mutations     : FALSE")
    if args.open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("ARK_UI2_READ_ONLY_SERVER_STOPPING")
    finally:
        if refresh_loop is not None:
            refresh_loop.stop()
            refresh_loop.join(timeout=2.0)
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
