# Berea

**→ [schallabear.github.io/berea-Bible-study](https://schallabear.github.io/berea-Bible-study/)**

A quiet place to read and study the Bible.

Named for the people in Acts 17:11 who "examined the Scriptures daily." It is
built around one idea: reading slowly, with the richness of the text within
reach — and nothing else competing for your attention.

**No feed. No streaks. No video. No autoplay. No notifications.** Those are not
missing features; they're the point.

## What it does

- **Reads** the Berean Standard Bible in a single, unhurried column.
- **Opens any verse** into a study panel with four things:
  - **Word by word** — the tagged Greek, each word with its transliteration,
    gloss, Strong's number, decoded morphology, and full Abbott-Smith lexicon
    entry. Grammar that changes the meaning gets a plain-language note (why an
    aorist isn't a past tense, what a middle voice implies).
  - **Cross-references** — the highest-voted connections from OpenBible.info,
    with the referenced verse's text inline so you don't lose your place.
  - **Notes** — your own, saved per verse in the browser.
  - **Go deeper** — optional. Ask open-ended questions about the passage
    (historical setting, contested readings, how a word functions) using your
    own Anthropic API key.
- **Works offline.** Install it to your home screen; every chapter you've opened
  once stays readable with no connection.
- **Tracks where you are** without nagging: mark chapters read, see the book at
  a glance. No streak to break.

A single-file copy (reading and study, without the API-backed *Go deeper* panel)
can be built with `python3 scripts/build_single.py` and hosted anywhere that
serves one static file.

## Installing it on your phone

Open the link above, then:

- **iPhone / iPad (Safari)** — Share → *Add to Home Screen*
- **Android (Chrome)** — menu → *Install app* (or the install prompt in the URL bar)

It then opens like an app, without browser chrome, and works with no
connection for any chapter you've already opened.

## Running it locally

It's a static site with no build step. Any static server will do:

```sh
python3 -m http.server 8000
# then open http://localhost:8000
```

Deploys to GitHub Pages automatically on push to `main`.

## The data

Everything the app needs is committed under `data/`, so it runs with no server,
no API keys, and no runtime dependency on anyone's service. To rebuild it or add
another book:

```sh
python3 scripts/build_data.py            # rebuild John
python3 scripts/build_data.py Mark Luke  # add more books
```

The script downloads its sources once into `.cache/` (gitignored) and writes
per-chapter JSON plus a per-book lexicon subset. Only New Testament books work
today — the Hebrew Bible needs the Old Testament tagged text wired up, which is
the same shape of work (see `scripts/build_data.py`, `SOURCES`).

### Sources

| Source | What it provides | Licence |
| --- | --- | --- |
| [Berean Standard Bible](https://bereanbible.com/) | English text | Public domain (CC0) |
| [STEPBible-Data](https://github.com/STEPBible/STEPBible-Data) | Tagged Greek NT (TAGNT), Greek lexicon (TBESG, incorporating Abbott-Smith) | CC BY 4.0 |
| [OpenBible.info](https://www.openbible.info/labs/cross-references/) | ~344,000 weighted cross-references | CC BY |

Deep thanks to the people behind these. The word-level study in this app is
their work; Berea just puts a reading surface on it.

## Go deeper, and your API key

The optional panel calls the Anthropic API **directly from your browser** with a
key you paste into Settings. The key is stored in that browser's local storage
and sent to `api.anthropic.com` and nowhere else. There is no backend here to
send it to — the whole app is static files.

That does mean the key sits in local storage, so use it on a device you control,
and prefer a key you can rotate. Cost is a fraction of a cent per question.

Everything else in Berea works with no key at all.

## Licence

Code is MIT (`LICENSE`). The scripture and study data keep their own licences —
see the table above and `ATTRIBUTION.md`, which travels with any redistribution.
