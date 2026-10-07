# Releasing Custom MD

How to cut a release for this repo. Two-minute version at the bottom.

## Version numbers

This project uses [semantic versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

| Change type        | Example              | Bump     |
| ------------------ | -------------------- | -------- |
| Initial release    | first commit         | `1.0.0`  |
| Small new feature  | autosave             | `1.1.0`  |
| Bug fix            | a crash fix          | `1.1.1`  |
| Breaking change    | rewrote the API      | `2.0.0`  |

Tags are written with a leading `v`: `v1.1.0`. Alpha/beta are *pre-release*
labels for a version that isn't stable yet (`1.1.0-beta.1` → stable `1.1.0`);
for this repo, just ship the stable version.

## The mental model

- **git** tracks history on your machine. A *commit* is a snapshot of changes;
  a *tag* is a named bookmark on a commit.
- **GitHub** is the remote copy of that history (`origin`) plus extras: releases,
  issues, pull requests.
- A **release** is a pushed tag wrapped in a public page with notes. The tag is
  the source of truth; the release page is just presentation.

## Before you release

1. Run the test suite and make sure it's green:

   ```sh
   python3 -m unittest discover -s app/tests -t .
   ```

2. Update `README.md` if behavior changed (the docs agent can do this).
3. Sanity-check the change with the reviewer / tester agents (see `PLAN.md`).
4. Update `tracker/STATE.md` — add one session-log entry and refresh Status /
   Next up (protocol in `AGENTS.md`). Stage it with the release commit.
5. Check `git status`. Stage only files that belong in the release — leave junk
   and loose sample notes out.

## Cut the release

```sh
# 1. commit the change
git add <files>
git commit -m "Short summary of the change"

# 2. tag it
git tag v1.1.0 -m "v1.1.0 - short description"

# 3. push the commit and the tag
git push origin main --tags

# 4. create the GitHub release (gh CLI)
gh release create v1.1.0 --title "v1.1.0 — Short title" --notes "Release notes..."
```

Verify with `gh release view v1.1.0` or open the URL it prints.

## Notes

- `git push origin main --tags` pushes the branch and every tag in one go; you
  can also push them separately (`git push origin main`, `git push origin v1.1.0`).
- A tag alone does **not** create a GitHub release — that last `gh release create`
  step is what makes the public release page.
- Only tag once per release. If a released version needs a fix, that's a new
  patch release (`1.1.1`), never a retag.

---

## Two-minute version

```sh
python3 -m unittest discover -s app/tests -t .        # all green?
git add <files> && git commit -m "Summary"
git tag v1.1.0 -m "v1.1.0 - description"
git push origin main --tags
gh release create v1.1.0 --title "v1.1.0 — Title" --notes "Notes..."
```