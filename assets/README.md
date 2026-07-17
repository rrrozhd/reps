# Brand assets

Served by the app at `/assets/*` (see the mount in `backend/app.py`) and used by
the root `README.md` — one source of truth, no duplicated copies.

| File | What it is | Text? | Use it on |
|------|------------|-------|-----------|
| `reps-mark.svg` | barbell mark only | no | light backgrounds |
| `reps-mark-dark.svg` | barbell mark, light bars | no | dark backgrounds (the app header, GitHub dark) |
| `reps-app-icon.svg` | green rounded square + mark | no | favicon, app icon, avatars |
| `reps-primary.svg` | mark + "reps" wordmark | **yes** | light backgrounds |
| `reps-dark.svg` | mark + wordmark on a dark plate | **yes** | dark backgrounds |
| `reps-mono.svg` | single-colour lockup | **yes** | one-colour printing, stamps |
| `reps-stacked.svg` | mark above wordmark | **yes** | square/vertical spaces |

## The font caveat (read before using a wordmark file)

The four wordmark files render "reps" as a **live `<text>` element** in
**Space Grotesk** (`font-family="'Space Grotesk','Helvetica Neue',Arial,sans-serif"`).
SVG text is resolved by *the viewer's* machine, so:

- **With Space Grotesk installed** → the intended wordmark.
- **Without it** (most machines, incl. default macOS) → silently falls back to
  Helvetica Neue / Arial, and the wordmark looks different.

So the wordmark files are **not pixel-stable across machines**. That's why:

- the **app header** uses `reps-mark-dark.svg` + real HTML text, and
- the **README** uses the mark via `<picture>` + a markdown heading.

Both are text-free images, so they render identically everywhere.

**If you want pixel-exact wordmarks**, convert the `<text>` to outlines in your
design tool and save them alongside (e.g. `reps-primary-outlined.svg`). Note:
outline them from **Space Grotesk** (SIL OFL — embedding/outlining is permitted),
never from the Helvetica fallback, which is proprietary and can't ship in an
MIT-licensed repo.

## Colours

| Token | Hex | Where |
|-------|-----|-------|
| brand black | `#16161a` | mark on light, wordmark, ink on accent |
| brand green | `#2fb877` | mark centre bar on light, app-icon plate |
| brand green (dark UI) | `#42c586` | mark centre on dark; the app's `--accent` |
| off-white | `#fbfaf7` | mark bars on dark |
