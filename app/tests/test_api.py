"""Integration tests for the Custom MD backend file API.

These tests run against the *real* HTTP server (server.Server on 127.0.0.1,
ephemeral port) but with a fresh temporary directory as the notes root, so the
repository's notes/ folder is never touched.

Run from the repo root:

    python3 -m unittest discover -s app/tests -t .

Only the Python standard library is used (unittest, urllib.request,
tempfile, threading).
"""

import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Make sure the repo root is importable even when this file is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import server  # noqa: E402

# Keep the test output readable: the Handler logs one line per request to
# stderr by default. This only silences logging in the test process.
server.Handler.log_message = lambda self, fmt, *args: None


def flatten(items, prefix=""):
    """Flatten a /api/tree payload into (type, path) tuples."""
    out = []
    for item in items:
        p = prefix + item["name"]
        out.append((item["type"], p))
        if item["type"] == "dir":
            out.extend(flatten(item.get("children", []), p + "/"))
    return out


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="custommd-test-")
        self.notes_root = Path(self._tmp.name).resolve()
        server.NOTES_ROOT = self.notes_root

        self.httpd = server.Server(("127.0.0.1", 0), server.Handler)
        self.port = self.httpd.socket.getsockname()[1]
        self.base = "http://127.0.0.1:%d" % self.port
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)
        self._tmp.cleanup()

    # ------------------------------------------------------------------ #
    # HTTP helpers
    # ------------------------------------------------------------------ #

    def api(self, method, path, body=None, timeout=15):
        headers = {"Content-Type": "application/json"} if body is not None else {}
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            self.base + path, data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                return resp.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                payload = json.loads(raw)
            except Exception:
                payload = None
            return exc.code, payload
        except urllib.error.URLError as exc:
            self.fail("connection error on %s %s: %s" % (method, path, exc))

    @staticmethod
    def file_url(rel):
        return "/api/file?path=" + urllib.parse.quote(rel, safe="")

    @staticmethod
    def folder_url(rel, recursive=None):
        url = "/api/folder?path=" + urllib.parse.quote(rel, safe="")
        if recursive:
            url += "&recursive=true"
        return url

    # ------------------------------------------------------------------ #
    # Health / tree
    # ------------------------------------------------------------------ #

    def test_health_ok(self):
        status, payload = self.api("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["root"], str(self.notes_root))

    def test_unknown_route_404(self):
        status, payload = self.api("GET", "/api/bogus")
        self.assertEqual(status, 404)
        self.assertIn("error", payload)

    def test_tree_lists_folders_and_markdown_only(self):
        (self.notes_root / "sub").mkdir()
        (self.notes_root / "sub" / "child.md").write_text("# child", encoding="utf-8")
        (self.notes_root / "welcome.md").write_text("# hello", encoding="utf-8")
        (self.notes_root / "notes.txt").write_text("plain", encoding="utf-8")
        (self.notes_root / "image.png").write_bytes(b"\x89PNG")
        (self.notes_root / ".hidden.md").write_text("hidden", encoding="utf-8")
        (self.notes_root / ".hiddendir").mkdir()
        try:
            os.symlink("/etc/hostname", self.notes_root / "link.md")
        except OSError:
            pass

        status, payload = self.api("GET", "/api/tree")
        self.assertEqual(status, 200)
        self.assertEqual(payload["name"], self.notes_root.name)

        got = flatten(payload["children"])
        self.assertIn(("dir", "sub"), got)
        self.assertIn(("file", "sub/child.md"), got)  # child.md is a file
        self.assertIn(("file", "welcome.md"), got)

        names = {name for _, name in got}
        self.assertNotIn("notes.txt", names)      # non-markdown file
        self.assertNotIn("image.png", names)      # non-markdown file
        self.assertNotIn(".hidden.md", names)     # hidden file
        self.assertNotIn(".hiddendir", names)     # hidden folder
        self.assertNotIn("link.md", names)        # symlink

    # ------------------------------------------------------------------ #
    # Read / write round trips
    # ------------------------------------------------------------------ #

    def test_read_write_round_trip_unicode(self):
        content = "# Héllo Wörld\n\n日本語テキスト 🎉\nünïcödé → čžš\n"
        status, payload = self.api("POST", self.file_url("note.md"))
        self.assertEqual(status, 200)
        status, payload = self.api(
            "PUT", self.file_url("note.md"), body={"content": content}
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["saved"])

        status, payload = self.api("GET", self.file_url("note.md"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["path"], "note.md")
        self.assertEqual(payload["content"], content)
        self.assertEqual(
            (self.notes_root / "note.md").read_text(encoding="utf-8"), content
        )

    def test_round_trip_exact_content(self):
        content = "\nline one\n\nline two\n  indented  \n# heading\n"
        self.api("PUT", self.file_url("exact.md"), body={"content": content})
        status, payload = self.api("GET", self.file_url("exact.md"))
        self.assertEqual(payload["content"], content)

    def test_empty_file_round_trip(self):
        status, payload = self.api("POST", self.file_url("empty.md"))
        self.assertEqual(status, 200)
        status, payload = self.api("GET", self.file_url("empty.md"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["content"], "")
        self.assertEqual((self.notes_root / "empty.md").stat().st_size, 0)

    def test_filename_with_spaces(self):
        status, payload = self.api("POST", self.file_url("my note.md"))
        self.assertEqual(status, 200)
        self.assertTrue((self.notes_root / "my note.md").exists())
        self.api(
            "PUT", self.file_url("my note.md"), body={"content": "spaced out"}
        )
        status, payload = self.api("GET", self.file_url("my note.md"))
        self.assertEqual(payload["content"], "spaced out")

    def test_nested_folders_in_tree_and_round_trip(self):
        self.api("POST", self.folder_url("a"))
        self.api("POST", self.folder_url("a/b"))
        self.api(
            "PUT",
            self.file_url("a/b/deep note.md"),
            body={"content": "deep content"},
        )
        # PUT auto-creates missing parent folders
        self.assertTrue((self.notes_root / "a" / "b" / "deep note.md").is_file())

        status, payload = self.api("GET", "/api/tree")
        got = set(flatten(payload["children"]))
        self.assertIn(("dir", "a"), got)
        self.assertIn(("dir", "a/b"), got)
        self.assertIn(("file", "a/b/deep note.md"), got)

        status, payload = self.api("GET", self.file_url("a/b/deep note.md"))
        self.assertEqual(payload["content"], "deep content")

    # ------------------------------------------------------------------ #
    # Autosave (repeated PUT to the same path)
    # ------------------------------------------------------------------ #

    def test_repeated_put_same_file_last_write_wins(self):
        """Autosave PUTs the open note again and again; each save must replace
        the previous content entirely (no stale merge/append) and report the
        same path."""
        self.api("POST", self.file_url("draft.md"))
        versions = ["first", "second version\nwith a newline", "", "final ✅ ünïcödé"]
        for content in versions:
            with self.subTest(content=content):
                status, payload = self.api(
                    "PUT", self.file_url("draft.md"), body={"content": content}
                )
                self.assertEqual(status, 200)
                self.assertTrue(payload["saved"])
                self.assertEqual(payload["path"], "draft.md")

                # Both the GET view and the raw bytes on disk reflect the save.
                status, payload = self.api("GET", self.file_url("draft.md"))
                self.assertEqual(status, 200)
                self.assertEqual(payload["content"], content)
                self.assertEqual(
                    (self.notes_root / "draft.md").read_text(encoding="utf-8"),
                    content,
                )

        # The final save wins and no earlier content survives anywhere.
        self.assertEqual(
            (self.notes_root / "draft.md").read_text(encoding="utf-8"),
            versions[-1],
        )

    def test_put_creates_nonexistent_file(self):
        """A save to a path that is not on disk yet must create it with exactly
        that content (first autosave after a new note / rename)."""
        target = self.notes_root / "brand new note.md"
        self.assertFalse(target.exists())
        content = "# fresh\n\ncreated by autosave 🆕\n"
        status, payload = self.api(
            "PUT", self.file_url("brand new note.md"), body={"content": content}
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["saved"])
        self.assertEqual(payload["path"], "brand new note.md")
        self.assertTrue(target.is_file())
        self.assertEqual(target.read_text(encoding="utf-8"), content)

        status, payload = self.api("GET", self.file_url("brand new note.md"))
        self.assertEqual(payload["content"], content)

    def test_put_create_in_missing_nested_folder(self):
        """PUT must create missing parent folders as part of the save."""
        target = self.notes_root / "auto" / "nested" / "note.md"
        self.assertFalse(target.parent.exists())
        status, payload = self.api(
            "PUT", self.file_url("auto/nested/note.md"), body={"content": "deep save"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["path"], "auto/nested/note.md")
        self.assertEqual(target.read_text(encoding="utf-8"), "deep save")

    def test_save_leaves_unrelated_sibling_untouched(self):
        """Saving one note must never touch another file in the same folder,
        whether or not both are open in the editor."""
        self.api("POST", self.file_url("open.md"))
        self.api("POST", self.file_url("other.md"))
        self.api("PUT", self.file_url("other.md"), body={"content": "other original"})
        (self.notes_root / "unrelated.md").write_text(
            "raw unrelated", encoding="utf-8"
        )

        for content in ("open one", "open two\nchanged", "open three 🎯"):
            with self.subTest(content=content):
                status, payload = self.api(
                    "PUT", self.file_url("open.md"), body={"content": content}
                )
                self.assertEqual(status, 200)

        self.assertEqual(
            (self.notes_root / "other.md").read_text(encoding="utf-8"),
            "other original",
        )
        self.assertEqual(
            (self.notes_root / "unrelated.md").read_text(encoding="utf-8"),
            "raw unrelated",
        )
        status, payload = self.api("GET", self.file_url("other.md"))
        self.assertEqual(payload["content"], "other original")
        status, payload = self.api("GET", self.file_url("open.md"))
        self.assertEqual(payload["content"], "open three 🎯")

    # ------------------------------------------------------------------ #
    # Create
    # ------------------------------------------------------------------ #

    def test_create_file_duplicate_conflict_409(self):
        status, payload = self.api("POST", self.file_url("once.md"))
        self.assertEqual(status, 200)
        self.assertTrue((self.notes_root / "once.md").exists())
        status, payload = self.api("POST", self.file_url("once.md"))
        self.assertEqual(status, 409)
        self.assertIn("error", payload)

    def test_create_folder_and_duplicate_conflict_409(self):
        status, payload = self.api("POST", self.folder_url("docs"))
        self.assertEqual(status, 200)
        self.assertTrue((self.notes_root / "docs").is_dir())
        status, payload = self.api("POST", self.folder_url("docs"))
        self.assertEqual(status, 409)

    # ------------------------------------------------------------------ #
    # Rename
    # ------------------------------------------------------------------ #

    def test_rename_file_changes_disk(self):
        self.api("POST", self.file_url("old.md"))
        status, payload = self.api(
            "POST", "/api/rename", body={"from": "old.md", "to": "renamed.md"}
        )
        self.assertEqual(status, 200)
        self.assertFalse((self.notes_root / "old.md").exists())
        self.assertTrue((self.notes_root / "renamed.md").exists())

    def test_rename_into_nested_folder(self):
        self.api("POST", self.file_url("a.md"))
        status, payload = self.api(
            "POST", "/api/rename", body={"from": "a.md", "to": "sub/deep/a.md"}
        )
        self.assertEqual(status, 200)
        self.assertTrue((self.notes_root / "sub" / "deep" / "a.md").exists())
        self.assertFalse((self.notes_root / "a.md").exists())

    def test_rename_onto_existing_conflict_409(self):
        self.api("POST", self.file_url("a.md"))
        self.api("POST", self.file_url("b.md"))
        status, payload = self.api(
            "POST", "/api/rename", body={"from": "a.md", "to": "b.md"}
        )
        self.assertEqual(status, 409)
        self.assertTrue((self.notes_root / "a.md").exists())  # untouched

    def test_rename_missing_source_404(self):
        status, payload = self.api(
            "POST", "/api/rename", body={"from": "ghost.md", "to": "b.md"}
        )
        self.assertEqual(status, 404)

    def test_rename_file_to_non_markdown_rejected(self):
        """Renaming a note to a name without a markdown extension would make it
        vanish from the tree; the API must refuse it (folders are unrestricted)."""
        self.api("POST", self.file_url("keep.md"))
        status, payload = self.api(
            "POST", "/api/rename", body={"from": "keep.md", "to": "keep.txt"}
        )
        self.assertEqual(status, 400)
        self.assertTrue((self.notes_root / "keep.md").exists())
        self.assertFalse((self.notes_root / "keep.txt").exists())

        # .markdown is a valid markdown extension.
        status, payload = self.api(
            "POST", "/api/rename", body={"from": "keep.md", "to": "keep.markdown"}
        )
        self.assertEqual(status, 200)
        self.assertTrue((self.notes_root / "keep.markdown").exists())

        # Folder names are not bound to markdown extensions.
        self.api("POST", self.folder_url("docs"))
        status, payload = self.api(
            "POST", "/api/rename", body={"from": "docs", "to": "notes-archive"}
        )
        self.assertEqual(status, 200)
        self.assertTrue((self.notes_root / "notes-archive").is_dir())

    def test_nul_byte_in_static_path_is_400_not_500(self):
        """A NUL byte in a static route must be rejected with 400, never crash
        into a 500 from Path.resolve() raising on the embedded \\x00."""
        for bad in ("/%00", "/index.html%00", "/%00robots.txt"):
            status, _ = self.api("GET", bad)
            self.assertEqual(status, 400, "expected 400 for %r" % bad)

        # Well-formed static paths still work afterwards (raw fetch: CSS/JS are
        # not JSON, which the api() helper assumes).
        status = urllib.request.urlopen(self.base + "/styles.css").status
        self.assertEqual(status, 200)

    def test_rename_folder_changes_disk(self):
        """Renaming a folder moves the whole tree on disk and on read."""
        self.api("POST", self.folder_url("olddir"))
        self.api("PUT", self.file_url("olddir/a.md"), body={"content": "# moved"})
        status, payload = self.api(
            "POST", "/api/rename", body={"from": "olddir", "to": "newdir"}
        )
        self.assertEqual(status, 200)
        self.assertFalse((self.notes_root / "olddir").exists())
        self.assertTrue((self.notes_root / "newdir" / "a.md").is_file())
        status, payload = self.api("GET", self.file_url("newdir/a.md"))
        self.assertEqual(payload["content"], "# moved")

    def test_rename_notes_root_rejected(self):
        """The vault root itself must never be renameable."""
        status, payload = self.api(
            "POST", "/api/rename", body={"from": "", "to": "moved"}
        )
        self.assertEqual(status, 400)
        self.assertIn("error", payload)
        self.assertTrue(self.notes_root.is_dir())

    def test_move_folder_into_itself_rejected(self):
        """A folder cannot be moved under its own subtree (would recurse)."""
        self.api("POST", self.folder_url("box"))
        for to in ("box/inner", "box/inner/deep"):
            with self.subTest(to=to):
                status, payload = self.api(
                    "POST", "/api/rename", body={"from": "box", "to": to}
                )
                self.assertEqual(status, 400)
                self.assertFalse((self.notes_root / "box" / "inner").exists())

    # ------------------------------------------------------------------ #
    # Delete
    # ------------------------------------------------------------------ #

    def test_delete_file_changes_disk_and_404s_after(self):
        self.api("POST", self.file_url("del.md"))
        status, payload = self.api("DELETE", self.file_url("del.md"))
        self.assertEqual(status, 200)
        self.assertTrue(payload["deleted"])
        self.assertFalse((self.notes_root / "del.md").exists())

        status, payload = self.api("GET", self.file_url("del.md"))
        self.assertEqual(status, 404)
        status, payload = self.api("DELETE", self.file_url("del.md"))
        self.assertEqual(status, 404)

    def test_delete_empty_folder(self):
        self.api("POST", self.folder_url("empty"))
        status, payload = self.api("DELETE", self.folder_url("empty"))
        self.assertEqual(status, 200)
        self.assertFalse((self.notes_root / "empty").exists())

    def test_delete_nonempty_folder_requires_recursive(self):
        self.api("POST", self.folder_url("stuff"))
        self.api("POST", self.file_url("stuff/a.md"))

        status, payload = self.api("DELETE", self.folder_url("stuff"))
        self.assertEqual(status, 409)
        self.assertTrue((self.notes_root / "stuff").exists())

        status, payload = self.api(
            "DELETE", self.folder_url("stuff", recursive=True)
        )
        self.assertEqual(status, 200)
        self.assertFalse((self.notes_root / "stuff").exists())

    def test_delete_folder_recursive_removes_nested_tree(self):
        """recursive=true must delete nested subfolders too, while leaving
        sibling files in the vault untouched."""
        self.api("POST", self.folder_url("tree"))
        self.api("POST", self.folder_url("tree/inner"))
        self.api("PUT", self.file_url("tree/top.md"), body={"content": "top"})
        self.api("PUT", self.file_url("tree/inner/deep.md"), body={"content": "deep"})
        self.api("PUT", self.file_url("keep.md"), body={"content": "keep me"})

        status, payload = self.api(
            "DELETE", self.folder_url("tree", recursive=True)
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["deleted"])
        self.assertFalse((self.notes_root / "tree").exists())
        self.assertTrue((self.notes_root / "keep.md").is_file())

    def test_delete_file_path_that_is_a_folder_400(self):
        """DELETE /api/file on an existing folder must refuse (400), not
        unlink the directory."""
        self.api("POST", self.folder_url("folder.md"))
        status, payload = self.api("DELETE", self.file_url("folder.md"))
        self.assertEqual(status, 400)
        self.assertIn("error", payload)
        self.assertTrue((self.notes_root / "folder.md").is_dir())

    def test_delete_notes_root_rejected(self):
        status, payload = self.api("DELETE", "/api/folder?path=")
        self.assertEqual(status, 400)
        self.assertTrue(self.notes_root.is_dir())

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #

    def test_search_matches_content_and_filenames(self):
        (self.notes_root / "groceries.md").write_text(
            "Buy milk and eggs", encoding="utf-8"
        )
        (self.notes_root / "todo.md").write_text(
            "Plan the week out", encoding="utf-8"
        )
        (self.notes_root / "sub").mkdir()
        (self.notes_root / "sub" / "deep.md").write_text(
            "a needle nested in here", encoding="utf-8"
        )

        # content match
        status, payload = self.api("GET", "/api/search?q=milk")
        self.assertEqual(status, 200)
        paths = [r["path"] for r in payload["results"]]
        self.assertIn("groceries.md", paths)
        match = next(r for r in payload["results"] if r["path"] == "groceries.md")
        self.assertEqual(match["line"], 1)
        self.assertIn("Buy milk and eggs", match["text"])

        # title/filename match
        status, payload = self.api("GET", "/api/search?q=todo")
        match = next(r for r in payload["results"] if r["path"] == "todo.md")
        self.assertEqual(match["line"], 0)
        self.assertEqual(match["text"], "(filename match)")

        # nested file, case-insensitive content match
        status, payload = self.api("GET", "/api/search?q=NEEDLE")
        self.assertIn("sub/deep.md", [r["path"] for r in payload["results"]])

        # empty query -> no results
        status, payload = self.api("GET", "/api/search?q=")
        self.assertEqual(payload["results"], [])

    def test_search_skips_hidden_nonmarkdown_symlinks_and_oversized(self):
        """Search must never surface hidden entries, non-markdown files,
        symlinks (in-vault or escaping), or files over MAX_FILE_BYTES."""
        (self.notes_root / "visible.md").write_text(
            "needle in the haystack", encoding="utf-8"
        )
        (self.notes_root / "notes.md").write_text(
            "no match here", encoding="utf-8"
        )
        (self.notes_root / "plain.txt").write_text(
            "needle in plain text", encoding="utf-8"
        )
        (self.notes_root / ".hidden.md").write_text(
            "needle hidden", encoding="utf-8"
        )
        (self.notes_root / ".hiddendir").mkdir()
        (self.notes_root / ".hiddendir" / "h.md").write_text(
            "needle in hidden dir", encoding="utf-8"
        )
        (self.notes_root / "big.md").write_text(
            "needle " + "x" * server.MAX_FILE_BYTES, encoding="utf-8"
        )
        try:
            os.symlink("notes.md", self.notes_root / "alias.md")
            os.symlink("/etc/hostname", self.notes_root / "sys.md")
        except OSError as exc:
            self.skipTest("cannot create symlink: %s" % exc)

        status, payload = self.api("GET", "/api/search?q=needle")
        self.assertEqual(status, 200)
        paths = [r["path"] for r in payload["results"]]
        self.assertIn("visible.md", paths)
        self.assertNotIn("plain.txt", paths)        # non-markdown pruned
        self.assertNotIn(".hidden.md", paths)       # hidden file pruned
        self.assertNotIn(".hiddendir/h.md", paths)  # hidden folder pruned
        self.assertNotIn("alias.md", paths)         # symlink pruned
        self.assertNotIn("sys.md", paths)           # escaping symlink pruned
        self.assertNotIn("big.md", paths)           # oversized pruned

        # non-markdown files never match, even by filename
        status, payload = self.api("GET", "/api/search?q=plain")
        self.assertEqual(payload["results"], [])

    # ------------------------------------------------------------------ #
    # Path traversal / security
    # ------------------------------------------------------------------ #

    def test_path_traversal_rejected(self):
        attacks = (
            "../x",                       # plain parent traversal
            "/etc/passwd",                # absolute path
            "/etc",                       # absolute path, existing dir
            "a/../../x",                  # nested traversal
            "..%2f..%2fetc%2fpasswd",     # encoded slashes
            "%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # fully encoded dots+slashes
            "%2fetc%2fpasswd",            # encoded leading slash
        )
        for attack in attacks:
            with self.subTest(attack=attack):
                status, payload = self.api("GET", "/api/file?path=%s" % attack)
                self.assertEqual(status, 400, attack)
                self.assertIn("error", payload)

    def test_traversal_mutation_does_not_write_outside_root(self):
        parent = self.notes_root.parent
        for attack, rel in (
            ("..%2fescape-dir", "escape-dir"),
            ("..%2f..%2fescape-dir2", "escape-dir2"),
        ):
            with self.subTest(attack=attack):
                status, payload = self.api(
                    "POST", "/api/folder?path=%s" % attack
                )
                self.assertEqual(status, 400)
                self.assertFalse((parent / rel).exists())

        status, payload = self.api("POST", "/api/file?path=..%2fescape.md")
        self.assertEqual(status, 400)
        self.assertFalse((parent / "escape.md").exists())

        # notes root itself stays empty
        self.assertEqual(list(self.notes_root.iterdir()), [])

    def test_symlink_escaping_root_rejected(self):
        link = self.notes_root / "link.md"
        try:
            os.symlink("/etc/hostname", link)
        except OSError as exc:
            self.skipTest("cannot create symlink: %s" % exc)
        status, payload = self.api("GET", self.file_url("link.md"))
        self.assertEqual(status, 400)  # resolves outside the root

    def test_symlink_mutation_rejected(self):
        """Mutating through an in-vault symlink must be refused.

        Without this guard, DELETE/PUT on alias.md -> real.md would act on the
        *real* file (wrong-file overwrite/delete), and PUT on a dangling
        symlink would create the target under a different name.
        """
        try:
            (self.notes_root / "real.md").write_text("original", encoding="utf-8")
            os.symlink("real.md", self.notes_root / "alias.md")
            os.symlink("missing.md", self.notes_root / "dangling.md")
        except OSError as exc:
            self.skipTest("cannot create symlink: %s" % exc)

        # PUT through the alias must not touch real.md
        status, payload = self.api("PUT", self.file_url("alias.md"), body={"content": "x"})
        self.assertEqual(status, 400)
        self.assertEqual(
            (self.notes_root / "real.md").read_text(encoding="utf-8"), "original"
        )

        # DELETE of the alias must leave real.md in place
        status, payload = self.api("DELETE", self.file_url("alias.md"))
        self.assertEqual(status, 400)
        self.assertTrue((self.notes_root / "real.md").exists())

        # PUT on a dangling symlink must not create the referent file
        status, payload = self.api("PUT", self.file_url("dangling.md"), body={"content": "x"})
        self.assertEqual(status, 400)
        self.assertFalse((self.notes_root / "missing.md").exists())

        # rename *through* the alias is refused too
        status, payload = self.api(
            "POST", "/api/rename", body={"from": "alias.md", "to": "moved.md"}
        )
        self.assertEqual(status, 400)
        self.assertTrue((self.notes_root / "real.md").exists())

    def test_whitespace_padded_symlink_not_a_bypass(self):
        """A padded path (e.g. " x.md") must be checked and mutated as the
        SAME file. Before the strip fix, safe_resolve() stripped the space and
        targeted x.md, while reject_symlinks() inspected " x.md" - so a
        symlinked x.md -> real.md could be written through by padding.
        """
        try:
            (self.notes_root / "real.md").write_text("original", encoding="utf-8")
            os.symlink("real.md", self.notes_root / "x.md")
            (self.notes_root / " x.md").write_text("decoy", encoding="utf-8")
        except OSError as exc:
            self.skipTest("cannot create symlink: %s" % exc)

        status, payload = self.api(
            "PUT", self.file_url(" x.md"), body={"content": "clobbered"}
        )
        self.assertEqual(status, 400)
        self.assertEqual(
            (self.notes_root / "real.md").read_text(encoding="utf-8"), "original"
        )

    # ------------------------------------------------------------------ #
    # Validation / edge cases
    # ------------------------------------------------------------------ #

    def test_get_missing_file_404(self):
        status, payload = self.api("GET", self.file_url("nope.md"))
        self.assertEqual(status, 404)

    def test_non_markdown_operations_rejected(self):
        (self.notes_root / "plain.txt").write_text("x", encoding="utf-8")

        status, payload = self.api("GET", self.file_url("plain.txt"))
        self.assertEqual(status, 400)

        status, payload = self.api("POST", self.file_url("new.txt"))
        self.assertEqual(status, 400)
        self.assertFalse((self.notes_root / "new.txt").exists())

        status, payload = self.api(
            "PUT", self.file_url("plain.txt"), body={"content": "y"}
        )
        self.assertEqual(status, 400)
        self.assertEqual(
            (self.notes_root / "plain.txt").read_text(encoding="utf-8"), "x"
        )

    def test_put_into_folder_rejected_no_write(self):
        """PUT must never write through a folder path (always 409, any name).

        Fixed: server.py now checks `target.is_dir()` BEFORE the markdown
        extension check, so "that path is a folder" (409) is consistent for
        every folder, regardless of whether its name ends in .md.
        """
        self.api("POST", self.folder_url("x"))       # non-.md folder name
        status, payload = self.api(
            "PUT", self.file_url("x"), body={"content": "hi"}
        )
        self.assertEqual(status, 409)                # folder check fires first
        self.assertEqual(list((self.notes_root / "x").iterdir()), [])

        self.api("POST", self.folder_url("x.md"))    # .md-suffixed folder name
        status, payload = self.api(
            "PUT", self.file_url("x.md"), body={"content": "hi"}
        )
        self.assertEqual(status, 409)                # consistent with the above
        self.assertIn("error", payload)
        self.assertEqual(list((self.notes_root / "x.md").iterdir()), [])

    def test_put_requires_string_content(self):
        """PUT with a missing or non-string 'content' must be rejected and
        must not create or truncate anything on disk."""
        status, payload = self.api("PUT", self.file_url("x.md"), body={})
        self.assertEqual(status, 400)
        self.assertFalse((self.notes_root / "x.md").exists())

        status, payload = self.api(
            "PUT", self.file_url("x.md"), body={"content": 42}
        )
        self.assertEqual(status, 400)
        self.assertFalse((self.notes_root / "x.md").exists())

        status, payload = self.api("PUT", self.file_url("x.md"), body={"content": None})
        self.assertEqual(status, 400)
        self.assertFalse((self.notes_root / "x.md").exists())

    def test_put_content_too_large_rejected_413(self):
        big = "x" * (server.MAX_FILE_BYTES + 1)
        status, payload = self.api(
            "PUT", self.file_url("big.md"), body={"content": big}
        )
        self.assertEqual(status, 413)
        self.assertFalse((self.notes_root / "big.md").exists())

    def test_read_file_too_large_rejected_413(self):
        (self.notes_root / "big.md").write_text(
            "x" * (server.MAX_FILE_BYTES + 1), encoding="utf-8"
        )
        status, payload = self.api("GET", self.file_url("big.md"))
        self.assertEqual(status, 413)


if __name__ == "__main__":
    unittest.main()