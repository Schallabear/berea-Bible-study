#!/usr/bin/env python3
"""Bundle Berea into one self-contained HTML file.

Inlines the stylesheet, the app, and every data file into a single page that
needs no server and no network. Used to publish a hosted copy where only static
files can be served.

    python3 scripts/build_single.py [out.html]

The app reads its data from window.__BEREA__ when present (see BUNDLE in
app.js), keyed by the same paths it would otherwise fetch — so the bundled and
served builds run identical code.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "berea-single.html")


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as handle:
        return handle.read()


def collect_data():
    """Every data file, keyed by the path the app fetches it from."""
    bundle = {"data/manifest.json": json.loads(read("data", "manifest.json"))}

    books_dir = os.path.join(ROOT, "data", "books")
    for abbrev in sorted(os.listdir(books_dir)):
        book_dir = os.path.join(books_dir, abbrev)
        if not os.path.isdir(book_dir):
            continue
        for name in sorted(os.listdir(book_dir)):
            if name.endswith(".json"):
                key = f"data/books/{abbrev}/{name}"
                with open(os.path.join(book_dir, name), encoding="utf-8") as handle:
                    bundle[key] = json.load(handle)
    return bundle


def body_of(html):
    """The markup between <body> and </body>, minus tags the host supplies."""
    match = re.search(r"<body[^>]*>(.*)</body>", html, re.S | re.I)
    markup = match.group(1) if match else html
    # The host injects its own script and stylesheet references.
    markup = re.sub(r'\s*<script[^>]*src="[^"]*"[^>]*></script>', "", markup)
    return markup.strip()


def main():
    data = collect_data()
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    # </script> anywhere inside the JSON would end the block early.
    payload = payload.replace("</", "<\\/")

    app = read("app.js")
    # The bundle is one file, so the module's import-free body can run inline.
    app = app.replace("</script>", "<\\/script>")

    page = f"""<title>Berea — read and study John</title>
<style>
{read("style.css")}
</style>

{body_of(read("index.html"))}

<script>window.__BEREA__ = {payload};</script>
<script type="module">
{app}
</script>
"""

    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write(page)

    size = os.path.getsize(OUT)
    verses = sum(
        len(v["verses"]) for k, v in data.items() if k.endswith(".json") and "verses" in v
    )
    print(f"wrote {OUT}")
    print(f"  {size / 1048576:.2f} MB · {len(data)} data files · {verses:,} verses")
    if size > 16 * 1048576:
        print("  WARNING: over the 16 MB artifact limit")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
