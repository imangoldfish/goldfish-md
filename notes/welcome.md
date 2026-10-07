# Welcome to goldfish-md

This file lives in your `notes/` folder as a plain `.md` file. Edit it, rename
it, or delete it — it's just a file on disk.

goldfish-md is a small local markdown editor: a file tree on the left, a writing
pane on the right, and a live preview beside it. Everything you type is saved
to a real `.md` file, so your notes stay yours.

## Try the app

- **Browse** — click through the file tree (folders collapse with ▸).
- **Write** — click a note, edit, and watch the preview update as you type.
- **Save** — `Ctrl/Cmd+S`, or just wait — notes autosave after a pause.
- **Import** — drag `.md` files anywhere onto the window, or press **Import…**
  to copy notes from your device into the current folder.
- **Search** — the box at the top matches across every note.

---

## Every markdown feature, with an example

### Headings

# H1 — a section title
## H2 — subsections
### H3
#### H4
##### H5
###### H6

### Emphasis

**bold**, *italic*, ~~strikethrough~~, and `inline code`.

### Links

A [link to example.com](https://example.com), and an automatic link:
https://example.com. A reference link like [the docs][ref] works too.

[ref]: https://example.com/docs

### Images

An image uses the same syntax as a link, with a `!` in front (this one is an
inline SVG so it renders offline):

![A placeholder image](data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20width='400'%20height='120'%3E%3Crect%20width='400'%20height='120'%20fill='%23e6efff'/%3E%3Ctext%20x='200'%20y='72'%20font-size='26'%20text-anchor='middle'%20fill='%232563eb'%20font-family='sans-serif'%3ECustom%20MD%3C/text%3E%3C/svg%3E)

### Lists

Unordered:

- one
- two
  - nested item
  - another nested item

Ordered:

1. first
2. second
3. third

### Task lists

- [x] These render as checkboxes
- [ ] Mark items done by editing the box

### Blockquotes

> A quoted line.
>
> > A nested quote.

### Code

Inline: `const answer = 42;`

Fenced block with syntax highlighting:

```js
const greet = (name) => `Hello, ${name}!`;
console.log(greet("Custom MD"));
```

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"
```

```css
.editor {
  padding: 28px 32px;
  caret-color: var(--accent);
}
```

```bash
ls notes/ && head -n 3 notes/welcome.md
```

```json
{ "name": "Custom MD", "features": ["tree", "editor", "preview"] }
```

```sql
SELECT name, updated FROM notes WHERE name LIKE '%welcome%' ORDER BY updated DESC;
```

```html
<p>Hello <strong>world</strong> — rendered inline HTML.</p>
```

### Tables

| Feature   | Status |
|-----------|--------|
| Editing   | ✅ done |
| Preview   | ✅ live |
| Importing | 🆕 new |

### Horizontal rules

Above a rule, and below one:

---

---

### Escaping

If you need a literal markdown character, backslash-escape it:
\*not italic\*, \`not code\`, \# not a heading.

---

## Three example notes

Below are three ready-to-use notes. Copy each into its own `.md` file (or use
**Import…** / drag-and-drop) and make them yours.

### Example 1 — Daily notes template

```markdown
# 2026-10-07

**Focus:** <one thing to get done>

## Progress
- [ ]

## Notes
-

## Next
- [ ]
```

### Example 2 — Meeting notes

```markdown
# Meeting — project sync

**When:** <date, time>
**Who:** <attendees>

## Agenda
1. <topic>

## Decisions
-

## Action items
- [ ] **Owner:** <name> — <task>
```

### Example 3 — Ideas / scratchpad

```markdown
# Ideas

## Feature ideas
- <idea>

## Links worth keeping
- [<title>](<url>)

## Questions
- ?
```