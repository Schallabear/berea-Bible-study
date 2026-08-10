#!/usr/bin/env python3
"""Build Berea's static study data from open datasets.

Everything this script produces is committed to the repo, so the app needs no
server and no API keys at runtime. Run it again to add another book.

Sources (all downloaded from raw.githubusercontent.com):
  * Berean Standard Bible (CC0) - readable English text
  * STEPBible TAGNT (CC BY 4.0) - Greek NT tagged word-by-word
  * STEPBible TBESG (CC BY 4.0) - Abbott-Smith Greek lexicon keyed to Strong's
  * OpenBible.info cross-references (CC BY) - ~344k weighted cross-references

Usage:
    python3 scripts/build_data.py            # builds the default book (John)
    python3 scripts/build_data.py Mark Luke  # builds specific books
"""

import csv
import html
import json
import os
import re
import sys
import urllib.request
from collections import defaultdict

from morphology import decode

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(ROOT, ".cache")

RAW = "https://raw.githubusercontent.com"
SOURCES = {
    "bsb": f"{RAW}/scrollmapper/bible_databases/master/formats/json/BSB.json",
    "tagnt_gospels": (
        f"{RAW}/STEPBible/STEPBible-Data/master/Translators%20Amalgamated%20OT%2BNT/"
        "TAGNT%20Mat-Jhn%20-%20Translators%20Amalgamated%20Greek%20NT%20-%20STEPBible.org%20CC-BY.txt"
    ),
    "tagnt_rest": (
        f"{RAW}/STEPBible/STEPBible-Data/master/Translators%20Amalgamated%20OT%2BNT/"
        "TAGNT%20Act-Rev%20-%20Translators%20Amalgamated%20Greek%20NT%20-%20STEPBible.org%20CC-BY.txt"
    ),
    "tbesg": (
        f"{RAW}/STEPBible/STEPBible-Data/master/Lexicons/"
        "TBESG%20-%20Translators%20Brief%20lexicon%20of%20Extended%20Strongs%20for%20Greek%20-%20STEPBible.org%20CC%20BY.txt"
    ),
    "xrefs": f"{RAW}/shandran/openbible/main/cross_references_expanded.csv",
}

DEFAULT_BOOKS = ["John"]

# Maps the abbreviations used by STEPBible and OpenBible.info to BSB book names.
ABBREV_TO_NAME = {
    "Gen": "Genesis", "Exo": "Exodus", "Lev": "Leviticus", "Num": "Numbers",
    "Deu": "Deuteronomy", "Jos": "Joshua", "Jdg": "Judges", "Rut": "Ruth",
    "1Sa": "1 Samuel", "2Sa": "2 Samuel", "1Ki": "1 Kings", "2Ki": "2 Kings",
    "1Ch": "1 Chronicles", "2Ch": "2 Chronicles", "Ezr": "Ezra",
    "Neh": "Nehemiah", "Est": "Esther", "Job": "Job", "Psa": "Psalms",
    "Pro": "Proverbs", "Ecc": "Ecclesiastes", "Sng": "Song of Solomon",
    "Sos": "Song of Solomon", "Isa": "Isaiah", "Jer": "Jeremiah",
    "Lam": "Lamentations", "Ezk": "Ezekiel", "Eze": "Ezekiel", "Dan": "Daniel",
    "Hos": "Hosea", "Jol": "Joel", "Joe": "Joel", "Amo": "Amos",
    "Oba": "Obadiah", "Jon": "Jonah", "Mic": "Micah", "Nam": "Nahum",
    "Nah": "Nahum", "Hab": "Habakkuk", "Zep": "Zephaniah", "Hag": "Haggai",
    "Zec": "Zechariah", "Mal": "Malachi",
    "Mat": "Matthew", "Mrk": "Mark", "Mar": "Mark", "Luk": "Luke",
    "Jhn": "John", "Joh": "John", "Act": "Acts", "Rom": "Romans",
    "1Co": "1 Corinthians", "2Co": "2 Corinthians", "Gal": "Galatians",
    "Eph": "Ephesians", "Php": "Philippians", "Phi": "Philippians",
    "Col": "Colossians", "1Th": "1 Thessalonians", "2Th": "2 Thessalonians",
    "1Ti": "1 Timothy", "2Ti": "2 Timothy", "Tit": "Titus",
    "Phm": "Philemon", "Heb": "Hebrews", "Jas": "James", "Jam": "James",
    "1Pe": "1 Peter", "2Pe": "2 Peter", "1Jn": "1 John", "2Jn": "2 John",
    "3Jn": "3 John", "Jud": "Jude", "Jde": "Jude", "Rev": "Revelation",
}
NAME_TO_ABBREV = {
    "Genesis": "Gen", "Exodus": "Exo", "Leviticus": "Lev", "Numbers": "Num",
    "Deuteronomy": "Deu", "Joshua": "Jos", "Judges": "Jdg", "Ruth": "Rut",
    "1 Samuel": "1Sa", "2 Samuel": "2Sa", "1 Kings": "1Ki", "2 Kings": "2Ki",
    "1 Chronicles": "1Ch", "2 Chronicles": "2Ch", "Ezra": "Ezr",
    "Nehemiah": "Neh", "Esther": "Est", "Job": "Job", "Psalms": "Psa",
    "Proverbs": "Pro", "Ecclesiastes": "Ecc", "Song of Solomon": "Sng",
    "Isaiah": "Isa", "Jeremiah": "Jer", "Lamentations": "Lam",
    "Ezekiel": "Ezk", "Daniel": "Dan", "Hosea": "Hos", "Joel": "Jol",
    "Amos": "Amo", "Obadiah": "Oba", "Jonah": "Jon", "Micah": "Mic",
    "Nahum": "Nam", "Habakkuk": "Hab", "Zephaniah": "Zep", "Haggai": "Hag",
    "Zechariah": "Zec", "Malachi": "Mal", "Matthew": "Mat", "Mark": "Mrk",
    "Luke": "Luk", "John": "Jhn", "Acts": "Act", "Romans": "Rom",
    "1 Corinthians": "1Co", "2 Corinthians": "2Co", "Galatians": "Gal",
    "Ephesians": "Eph", "Philippians": "Php", "Colossians": "Col",
    "1 Thessalonians": "1Th", "2 Thessalonians": "2Th", "1 Timothy": "1Ti",
    "2 Timothy": "2Ti", "Titus": "Tit", "Philemon": "Phm", "Hebrews": "Heb",
    "James": "Jas", "1 Peter": "1Pe", "2 Peter": "2Pe", "1 John": "1Jn",
    "2 John": "2Jn", "3 John": "3Jn", "Jude": "Jud", "Revelation": "Rev",
}

# The OpenBible.info cross-reference table uses SBL-style abbreviations, which
# differ from the STEPBible set above, so it needs its own mapping.
XREF_ABBREV_TO_NAME = {
    "Gen": "Genesis", "Exod": "Exodus", "Lev": "Leviticus", "Num": "Numbers",
    "Deut": "Deuteronomy", "Josh": "Joshua", "Judg": "Judges", "Ruth": "Ruth",
    "1Sam": "1 Samuel", "2Sam": "2 Samuel", "1Kgs": "1 Kings", "2Kgs": "2 Kings",
    "1Chr": "1 Chronicles", "2Chr": "2 Chronicles", "Ezra": "Ezra",
    "Neh": "Nehemiah", "Esth": "Esther", "Job": "Job", "Ps": "Psalms",
    "Prov": "Proverbs", "Eccl": "Ecclesiastes", "Song": "Song of Solomon",
    "Isa": "Isaiah", "Jer": "Jeremiah", "Lam": "Lamentations",
    "Ezek": "Ezekiel", "Dan": "Daniel", "Hos": "Hosea", "Joel": "Joel",
    "Amos": "Amos", "Obad": "Obadiah", "Jonah": "Jonah", "Mic": "Micah",
    "Nah": "Nahum", "Hab": "Habakkuk", "Zeph": "Zephaniah", "Hag": "Haggai",
    "Zech": "Zechariah", "Mal": "Malachi", "Matt": "Matthew", "Mark": "Mark",
    "Luke": "Luke", "John": "John", "Acts": "Acts", "Rom": "Romans",
    "1Cor": "1 Corinthians", "2Cor": "2 Corinthians", "Gal": "Galatians",
    "Eph": "Ephesians", "Phil": "Philippians", "Col": "Colossians",
    "1Thess": "1 Thessalonians", "2Thess": "2 Thessalonians",
    "1Tim": "1 Timothy", "2Tim": "2 Timothy", "Titus": "Titus",
    "Phlm": "Philemon", "Heb": "Hebrews", "Jas": "James", "1Pet": "1 Peter",
    "2Pet": "2 Peter", "1John": "1 John", "2John": "2 John",
    "3John": "3 John", "Jude": "Jude", "Rev": "Revelation",
}
NAME_TO_XREF_ABBREV = {name: abbrev for abbrev, name in XREF_ABBREV_TO_NAME.items()}

MAX_XREFS_PER_VERSE = 8


def log(msg):
    print(f"  {msg}", flush=True)


def fetch(key):
    """Download a source once and cache it on disk."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, key)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    url = SOURCES[key]
    log(f"downloading {key} ...")
    request = urllib.request.Request(url, headers={"User-Agent": "berea-build"})
    with urllib.request.urlopen(request, timeout=300) as response, open(path, "wb") as out:
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    log(f"  {os.path.getsize(path):,} bytes")
    return path


# --- lexicon -----------------------------------------------------------------

ALLOWED_TAGS = ("b", "i", "em", "strong")


def clean_lexicon_html(raw):
    """Escape everything, then re-enable a small whitelist of tags.

    Escaping first and selectively un-escaping afterwards means no unexpected
    markup from the source data can reach the DOM.
    """
    text = html.escape(raw or "", quote=True)
    for tag in ALLOWED_TAGS:
        text = text.replace(f"&lt;{tag}&gt;", f"<{tag}>").replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    text = re.sub(r"&lt;BR\s*/?&gt;", "<br>", text, flags=re.IGNORECASE)

    # <ref='Jhn.1.1'>Jhn.1:1</ref> becomes a tappable scripture link.
    def ref_sub(match):
        target = match.group(1).split(",")[0].split(";")[0].strip()
        label = match.group(2)
        return f'<a class="lex-ref" data-ref="{html.escape(target, quote=True)}">{label}</a>'

    text = re.sub(
        r"&lt;ref=(?:&#x27;|&quot;|')([^&]*?)(?:&#x27;|&quot;|')&gt;(.*?)&lt;/ref&gt;",
        ref_sub,
        text,
        flags=re.DOTALL,
    )
    # Any ref tags we could not parse are reduced to their visible label.
    text = re.sub(r"&lt;/?ref[^&]*&gt;", "", text)

    # Abbott-Smith marks outline depth with a leading "__". The roman and arabic
    # numbering that follows carries the structure on its own, so drop the marker
    # rather than showing it to the reader.
    text = re.sub(r"(?:<br>\s*)?__+", "<br>", text)

    text = re.sub(r"(<br>\s*){3,}", "<br><br>", text)
    text = re.sub(r"^(<br>\s*)+", "", text)
    return text.strip()


def load_lexicon(path):
    """Parse TBESG into {strongs: entry}."""
    entries = {}
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.startswith("G") or "\t" not in line:
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 7:
                continue
            strongs = cols[0].strip()
            if not re.fullmatch(r"G\d+[A-Za-z]?", strongs):
                continue
            entry = {
                "strongs": strongs,
                "lemma": cols[3].strip(),
                "translit": cols[4].strip(),
                "gloss": cols[6].strip(),
            }
            full = clean_lexicon_html(cols[7]) if len(cols) > 7 else ""
            if full:
                entry["full"] = full
            # Keep the first (base) entry for each Strong's number.
            entries.setdefault(strongs, entry)
    return entries


# --- Greek text --------------------------------------------------------------

GREEK_WORD = re.compile(r"^(.*?)\s*\(([^)]*)\)\s*$")


def load_greek(paths, abbrev):
    """Parse TAGNT rows for one book into {(chapter, verse): [word, ...]}."""
    verses = defaultdict(list)
    prefix = abbrev + "."
    ref_re = re.compile(r"^" + re.escape(abbrev) + r"\.(\d+)\.(\d+)#(\d+)(?:=(\S+))?")

    for path in paths:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.startswith(prefix):
                    continue
                cols = line.rstrip("\n").split("\t")
                if len(cols) < 5:
                    continue
                match = ref_re.match(cols[0])
                if not match:
                    continue
                chapter, verse, position, witnesses = match.groups()

                surface = cols[1].strip()
                greek, translit = surface, ""
                parsed = GREEK_WORD.match(surface)
                if parsed:
                    greek, translit = parsed.group(1).strip(), parsed.group(2).strip()

                strongs, morph_code = "", ""
                if "=" in cols[3]:
                    strongs, morph_code = cols[3].split("=", 1)
                else:
                    strongs = cols[3]
                strongs, morph_code = strongs.strip(), morph_code.strip()

                lemma, lemma_gloss = "", ""
                if "=" in cols[4]:
                    lemma, lemma_gloss = cols[4].split("=", 1)
                else:
                    lemma = cols[4]

                word = {
                    "i": int(position),
                    "g": greek,
                    "t": translit,
                    "e": cols[2].strip(),
                    "s": strongs,
                    "lemma": lemma.strip(),
                    "lg": lemma_gloss.strip(),
                }
                morph = decode(morph_code)
                if morph:
                    word["m"] = morph
                if witnesses:
                    word["w"] = witnesses
                verses[(int(chapter), int(verse))].append(word)

    for words in verses.values():
        words.sort(key=lambda w: w["i"])
    return verses


# --- cross references --------------------------------------------------------

def load_xrefs(path, name, bsb_lookup):
    """Collect the highest-voted cross-references for one book."""
    from_abbrev = NAME_TO_XREF_ABBREV.get(name)
    if not from_abbrev:
        raise SystemExit(f"No cross-reference abbreviation for {name}")

    collected = defaultdict(list)
    with open(path, encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("From Book") != from_abbrev:
                continue
            try:
                chapter = int(row["From Chapter"])
                verse = int(row["From Verse number"])
                votes = int(row["Votes"] or 0)
            except (TypeError, ValueError):
                continue

            to_book = XREF_ABBREV_TO_NAME.get(row.get("To Verse start Book") or "")
            if not to_book:
                continue
            try:
                to_chapter = int(row["To Verse start Chapter"])
                to_verse = int(row["To Verse start number"])
            except (TypeError, ValueError):
                continue

            end_verse = None
            if (row.get("To Verse end number") or "").strip():
                try:
                    end_verse = int(row["To Verse end number"])
                except ValueError:
                    end_verse = None

            label = f"{to_book} {to_chapter}:{to_verse}"
            if end_verse and end_verse != to_verse:
                label += f"-{end_verse}"

            text = bsb_lookup.get((to_book, to_chapter, to_verse))
            if not text:
                continue
            if end_verse and end_verse > to_verse:
                extra = [
                    bsb_lookup.get((to_book, to_chapter, v))
                    for v in range(to_verse + 1, min(end_verse, to_verse + 3) + 1)
                ]
                text = " ".join([text] + [t for t in extra if t])

            collected[f"{chapter}.{verse}"].append(
                {"ref": label, "votes": votes, "text": text}
            )

    trimmed = {}
    for key, items in collected.items():
        items.sort(key=lambda x: (-x["votes"], x["ref"]))
        trimmed[key] = items[:MAX_XREFS_PER_VERSE]
    return trimmed


# --- build -------------------------------------------------------------------

def build_book(name, bsb_books, bsb_lookup, lexicon, greek_paths, xref_path):
    abbrev = NAME_TO_ABBREV.get(name)
    if not abbrev:
        raise SystemExit(f"Unknown book name: {name}")

    book = next((b for b in bsb_books if b["name"] == name), None)
    if not book:
        raise SystemExit(f"{name} not found in the BSB dataset")

    log(f"parsing Greek for {name} ...")
    greek = load_greek(greek_paths, abbrev)
    log(f"  {sum(len(w) for w in greek.values()):,} tagged Greek words")

    log(f"collecting cross-references for {name} ...")
    xrefs = load_xrefs(xref_path, name, bsb_lookup)
    log(f"  {sum(len(v) for v in xrefs.values()):,} cross-references")

    out_dir = os.path.join(DATA, "books", abbrev)
    os.makedirs(out_dir, exist_ok=True)

    used_strongs = set()
    chapters = []
    total_verses = 0

    for chapter in book["chapters"]:
        number = int(chapter["chapter"])
        verses = []
        for verse in chapter["verses"]:
            vnum = int(verse["verse"])
            words = greek.get((number, vnum), [])
            for word in words:
                if word.get("s"):
                    used_strongs.add(word["s"])
            entry = {"v": vnum, "text": verse["text"].strip()}
            if words:
                entry["words"] = words
            refs = xrefs.get(f"{number}.{vnum}")
            if refs:
                entry["xrefs"] = refs
            verses.append(entry)
            total_verses += 1

        payload = {
            "book": name,
            "abbrev": abbrev,
            "chapter": number,
            "verses": verses,
        }
        with open(os.path.join(out_dir, f"{number}.json"), "w", encoding="utf-8") as out:
            json.dump(payload, out, ensure_ascii=False, separators=(",", ":"))
        chapters.append({"chapter": number, "verses": len(verses)})

    # Ship only the lexicon entries this book actually needs.
    subset = {}
    missing = 0
    for strongs in sorted(used_strongs):
        entry = lexicon.get(strongs) or lexicon.get(re.sub(r"[A-Za-z]$", "", strongs))
        if entry:
            subset[strongs] = entry
        else:
            missing += 1
    with open(os.path.join(out_dir, "lexicon.json"), "w", encoding="utf-8") as out:
        json.dump(subset, out, ensure_ascii=False, separators=(",", ":"))
    log(f"  {len(subset):,} lexicon entries ({missing} Strong's numbers had no entry)")

    return {
        "name": name,
        "abbrev": abbrev,
        "chapters": chapters,
        "verses": total_verses,
        "language": "Greek",
    }


def main():
    books = sys.argv[1:] or DEFAULT_BOOKS
    os.makedirs(DATA, exist_ok=True)

    print("Berea data build")
    bsb_path = fetch("bsb")
    tbesg_path = fetch("tbesg")
    xref_path = fetch("xrefs")
    greek_paths = [fetch("tagnt_gospels"), fetch("tagnt_rest")]

    log("loading BSB ...")
    with open(bsb_path, encoding="utf-8") as handle:
        bsb = json.load(handle)
    bsb_books = bsb["books"]
    bsb_lookup = {
        (b["name"], int(c["chapter"]), int(v["verse"])): v["text"].strip()
        for b in bsb_books
        for c in b["chapters"]
        for v in c["verses"]
    }
    log(f"  {len(bsb_lookup):,} verses")

    log("loading Greek lexicon ...")
    lexicon = load_lexicon(tbesg_path)
    log(f"  {len(lexicon):,} entries")

    manifest_path = os.path.join(DATA, "manifest.json")
    existing = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as handle:
            for book in json.load(handle).get("books", []):
                existing[book["name"]] = book

    for name in books:
        info = build_book(name, bsb_books, bsb_lookup, lexicon, greek_paths, xref_path)
        existing[name] = info

    order = list(NAME_TO_ABBREV)
    ordered = sorted(existing.values(), key=lambda b: order.index(b["name"]))
    with open(manifest_path, "w", encoding="utf-8") as out:
        json.dump(
            {
                "translation": "Berean Standard Bible",
                "translationShort": "BSB",
                "books": ordered,
            },
            out,
            ensure_ascii=False,
            indent=2,
        )

    print("\nDone. Built:", ", ".join(b["name"] for b in ordered))


if __name__ == "__main__":
    main()
