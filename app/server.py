#!/usr/bin/env python3
"""
Custom MD - a tiny local server for a folder of markdown notes.

It serves the static UI from ./static and a small JSON file API under /api.
Everything the API touches is constrained to the notes root (see safe_resolve),
so the browser can browse, edit, create, rename, delete and search notes.

Run:
    python3 server.py
    python3 server.py --notes ~/my-notes --port 8765 --host 127.0.0.1
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import shutil
import sys
import tempfile
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

MD_EXTENSIONS = {".md", ".markdown"}
STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_FILE_BYTES = 5 * 1024 * 1024      # refuse to open/edit absurdly large notes
MAX_REQUEST_BYTES = 6 * 1024 * 1024   # request body cap
MAX_SEARCH_RESULTS = 200

# Set once in main(). All path helpers read this global.
NOTES_ROOT: Path = Path(".")


class ApiError(Exception):
    """An error that should be returned to the client as JSON."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


# --------------------------------------------------------------------------- #
# Path safety
# --------------------------------------------------------------------------- #

def safe_resolve(rel: str) -> Path:
    """Map a client-supplied relative path to an absolute path inside NOTES_ROOT.

    Rejects absolute paths and anything that escapes the notes root, including
    traversal via '..' or symlinks. Path.resolve() collapses '..' and follows
    symlinks, then we verify the result is still under the root.
    """
    rel = (rel or "").strip()
    if rel.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", rel):
        raise ApiError(400, "absolute paths are not allowed")
    candidate = None
    try:
        candidate = (NOTES_ROOT / rel).resolve()
    except (ValueError, OSError) as exc:
        # e.g. an embedded NUL byte raises ValueError; resolve() can raise
        # OSError on unreadable parent dirs. Either way: invalid path, 400.
        raise ApiError(400, "invalid path") from exc
    if candidate != NOTES_ROOT and not candidate.is_relative_to(NOTES_ROOT):
        raise ApiError(400, "path escapes the notes folder")
    return candidate


def reject_symlinks(rel: str) -> None:
    """Refuse to mutate through a symlink.

    safe_resolve() collapses symlinks before we can inspect the named entry
    (a DELETE of `alias.md -> real.md` would otherwise unlink the *real*
    file). So this checks the raw on-disk entry chain — lstat semantics, no
    link following — and raises if any existing component is a symlink,
    including the final one and dangling links.
    """
    current = NOTES_ROOT
    for part in Path(rel).parts:
        current = current / part
        if current.is_symlink():
            raise ApiError(400, "symlinks are not supported")


def relative(path: Path) -> str:
    return path.relative_to(NOTES_ROOT).as_posix()


def is_markdown(path: Path) -> bool:
    return path.suffix.lower() in MD_EXTENSIONS


# --------------------------------------------------------------------------- #
# File operations
# --------------------------------------------------------------------------- #

def build_tree(directory: Path) -> list[dict]:
    """Recursively describe a directory as folders + markdown files.

    Hidden entries and symlinks are skipped, so a symlink cannot pull content
    from outside the vault into the listing.
    """
    items: list[dict] = []
    try:
        children = list(directory.iterdir())
    except OSError:
        return items

    children.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
    for child in children:
        if child.name.startswith(".") or child.is_symlink():
            continue
        if child.is_dir():
            items.append({
                "type": "dir",
                "name": child.name,
                "path": relative(child),
                "children": build_tree(child),
            })
        elif child.is_file() and is_markdown(child):
            items.append({"type": "file", "name": child.name, "path": relative(child)})
    return items


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise ApiError(415, "file is not valid UTF-8 text")
    except OSError as exc:
        raise ApiError(500, f"could not read file: {exc}")


def write_text(path: Path, content: str) -> None:
    """Write atomically: a temp file in the same folder, then os.replace.

    Preserves the existing file's permissions (new files default to 0644) and
    always cleans up the temp file on failure, so a failed or partial write
    never truncates the original.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = 0o644
    if path.exists():
        try:
            mode = path.stat().st_mode & 0o777
        except OSError:
            pass

    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".md")
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp, path)
    except Exception as exc:
        try:
            os.close(fd)
        except OSError:
            pass
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise ApiError(500, f"could not write file: {exc}")


def search_notes(query: str) -> list[dict]:
    """Case-insensitive substring search over note names and contents.

    os.walk(followlinks=False) never descends into directory symlinks (rglob
    behavior varies across Python versions), hidden folders are pruned, and
    files larger than MAX_FILE_BYTES are skipped so one giant note cannot
    stall or exhaust the search.
    """
    needle = query.lower()
    results: list[dict] = []

    for dirpath, dirnames, filenames in os.walk(NOTES_ROOT, followlinks=False):
        dirnames[:] = sorted(
            d for d in dirnames
            if not d.startswith(".") and not (Path(dirpath) / d).is_symlink()
        )
        for name in sorted(filenames):
            if name.startswith("."):
                continue
            path = Path(dirpath) / name
            if path.is_symlink() or not path.is_file() or not is_markdown(path):
                continue
            rel = relative(path)

            if needle in rel.lower():
                results.append({"path": rel, "line": 0, "text": "(filename match)"})
                if len(results) >= MAX_SEARCH_RESULTS:
                    return results

            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            for number, line in enumerate(text.splitlines(), start=1):
                if needle in line.lower():
                    results.append({"path": rel, "line": number, "text": line.strip()[:200]})
                    if len(results) >= MAX_SEARCH_RESULTS:
                        return results
    return results


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #

def handle_api(method: str, route: str, query: dict, body: dict):
    # Normalize ONCE: safe_resolve() and reject_symlinks() must inspect the
    # exact same string, or a padded path (e.g. " x.md") could make them check
    # different files (a symlink-guard bypass).
    path = (query.get("path") or [""])[0].strip()

    if route == "/api/health" and method == "GET":
        return {"ok": True, "root": str(NOTES_ROOT)}

    if route == "/api/tree" and method == "GET":
        return {"name": NOTES_ROOT.name, "children": build_tree(NOTES_ROOT)}

    if route == "/api/search" and method == "GET":
        q = (query.get("q") or [""])[0].strip()
        return {"query": q, "results": search_notes(q) if q else []}

    if route == "/api/file":
        target = safe_resolve(path)

        if method == "GET":
            if not target.is_file():
                raise ApiError(404, "file not found")
            if not is_markdown(target):
                raise ApiError(400, "not a markdown file")
            if target.stat().st_size > MAX_FILE_BYTES:
                raise ApiError(413, "file is too large to open")
            return {"path": relative(target), "content": read_text(target)}

        if method == "PUT":  # save existing / overwrite
            reject_symlinks(path)
            if target.exists() and target.is_dir():
                raise ApiError(409, "that path is a folder")
            if not is_markdown(target):
                raise ApiError(400, "only markdown files can be edited")
            content = body.get("content")
            if not isinstance(content, str):
                raise ApiError(400, "missing 'content'")
            if len(content.encode("utf-8")) > MAX_FILE_BYTES:
                raise ApiError(413, "content is too large to save")
            write_text(target, content)
            return {"path": relative(target), "saved": True}

        if method == "POST":  # create a new empty file
            reject_symlinks(path)
            if not is_markdown(target):
                raise ApiError(400, "new files must end in .md")
            if target.exists():
                raise ApiError(409, "a file with that name already exists")
            write_text(target, "")
            return {"path": relative(target), "created": True}

        if method == "DELETE":
            reject_symlinks(path)
            if not target.exists():
                raise ApiError(404, "file not found")
            if not target.is_file():
                raise ApiError(400, "not a file")
            rel = relative(target)
            target.unlink()
            return {"path": rel, "deleted": True}

    if route == "/api/folder":
        target = safe_resolve(path)

        if method == "POST":
            reject_symlinks(path)
            if target.exists():
                raise ApiError(409, "that folder already exists")
            target.mkdir(parents=True, exist_ok=True)
            return {"path": relative(target), "created": True}

        if method == "DELETE":
            reject_symlinks(path)
            if not target.exists():
                raise ApiError(404, "folder not found")
            if target == NOTES_ROOT:
                raise ApiError(400, "cannot delete the notes root")
            if not target.is_dir():
                raise ApiError(400, "not a folder")
            rel = relative(target)
            recursive = (query.get("recursive") or ["false"])[0].lower() == "true"
            if any(target.iterdir()):
                if not recursive:
                    raise ApiError(409, "folder is not empty")
                shutil.rmtree(target)
            else:
                target.rmdir()
            return {"path": rel, "deleted": True}

    if route == "/api/rename" and method == "POST":
        source_rel = body.get("from", "").strip()
        dest_rel = body.get("to", "").strip()
        source = safe_resolve(source_rel)
        destination = safe_resolve(dest_rel)
        reject_symlinks(source_rel)
        reject_symlinks(dest_rel)
        if not source.exists():
            raise ApiError(404, "source not found")
        if source == NOTES_ROOT:
            raise ApiError(400, "cannot rename the notes root")
        if destination.exists():
            raise ApiError(409, "a file or folder with that name already exists")
        if source.is_dir() and destination.is_relative_to(source):
            raise ApiError(400, "cannot move a folder into itself")
        if source.is_file() and not is_markdown(destination):
            raise ApiError(400, "renamed files must keep a .md/.markdown extension")
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)
        return {"from": relative(source), "to": relative(destination)}

    raise ApiError(404, "unknown API route")


# --------------------------------------------------------------------------- #
# HTTP glue
# --------------------------------------------------------------------------- #

class Handler(BaseHTTPRequestHandler):
    server_version = "CustomMD/0.1"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # keep startup quiet, log requests to stderr
        sys.stderr.write("  %s\n" % (fmt % args))

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, payload) -> None:
        self._send(status, json.dumps(payload).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _error(self, status: int, message: str) -> None:
        self._json(status, {"error": message})

    def _read_body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            raise ApiError(400, "invalid Content-Length")
        if length <= 0:
            return {}
        if length > MAX_REQUEST_BYTES:
            raise ApiError(413, "request body is too large")
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ApiError(400, "request body must be JSON")
        if not isinstance(data, dict):
            raise ApiError(400, "request body must be a JSON object")
        return data

    def _serve_static(self, route: str) -> None:
        if route in ("", "/"):
            route = "/index.html"
        rel = unquote(route).lstrip("/")
        if "\x00" in rel:  # embedded NUL would make Path.resolve() raise a 500
            self._error(400, "invalid path")
            return
        target = (STATIC_DIR / rel).resolve()
        if target != STATIC_DIR and not target.is_relative_to(STATIC_DIR):
            self._error(400, "invalid path")
            return
        if not target.is_file():
            self._error(404, "not found")
            return
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        self._send(200, target.read_bytes(), ctype)

    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        query = parse_qs(parsed.query)
        try:
            if route.startswith("/api/"):
                body = self._read_body() if method in ("POST", "PUT") else {}
                self._json(200, handle_api(method, route, query, body))
            elif method == "GET":
                self._serve_static(route)
            else:
                self._error(405, "method not allowed")
        except ApiError as exc:
            self._error(exc.status, exc.message)
        except Exception as exc:  # never let one bad request kill the server
            traceback.print_exc()
            self._error(500, f"internal error: {exc}")

    def do_GET(self):
        self._dispatch("GET")

    def do_HEAD(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")


class Server(ThreadingHTTPServer):
    daemon_threads = True


def main() -> None:
    global NOTES_ROOT

    default_notes = Path(__file__).resolve().parent.parent / "notes"
    parser = argparse.ArgumentParser(description="Serve a folder of markdown notes.")
    parser.add_argument("--notes", default=str(default_notes),
                        help="the notes folder / vault (default: ../notes)")
    parser.add_argument("--host", default="127.0.0.1", help="bind address")
    parser.add_argument("--port", type=int, default=8765, help="port")
    args = parser.parse_args()

    NOTES_ROOT = Path(args.notes).expanduser().resolve()
    NOTES_ROOT.mkdir(parents=True, exist_ok=True)
    if not STATIC_DIR.is_dir():
        parser.error(f"missing static assets: {STATIC_DIR}")

    try:
        server = Server((args.host, args.port), Handler)
    except OSError as exc:
        parser.error(f"could not start on {args.host}:{args.port} - {exc}")

    print("Custom MD")
    print(f"  notes:  {NOTES_ROOT}")
    print(f"  url:    http://{args.host}:{args.port}/")
    print("  stop:   Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()