"""Decoder for the Robinson-style Greek morphology codes used in STEPBible TAGNT.

The goal here is honesty over completeness: when a code segment is not
recognised we surface the raw code rather than inventing a parse. Every
returned description is something a reader can trust.
"""

PART_OF_SPEECH = {
    "N": "noun",
    "A": "adjective",
    "T": "article",
    "P": "personal pronoun",
    "R": "relative pronoun",
    "C": "reciprocal pronoun",
    "D": "demonstrative pronoun",
    "K": "correlative pronoun",
    "I": "interrogative pronoun",
    "X": "indefinite pronoun",
    "Q": "correlative or interrogative pronoun",
    "F": "reflexive pronoun",
    "S": "possessive pronoun",
    "V": "verb",
    "ADV": "adverb",
    "CONJ": "conjunction",
    "COND": "conditional particle",
    "PRT": "particle",
    "PREP": "preposition",
    "INJ": "interjection",
    "ARAM": "Aramaic transliteration",
    "HEB": "Hebrew transliteration",
}

CASE = {
    "N": "nominative",
    "G": "genitive",
    "D": "dative",
    "A": "accusative",
    "V": "vocative",
}
NUMBER = {"S": "singular", "P": "plural", "D": "dual"}
GENDER = {"M": "masculine", "F": "feminine", "N": "neuter"}

TENSE = {
    "P": "present",
    "I": "imperfect",
    "F": "future",
    "A": "aorist",
    "R": "perfect",
    "L": "pluperfect",
    "X": "perfect",
    "Y": "pluperfect",
    "2A": "second aorist",
    "2F": "second future",
    "2R": "second perfect",
    "2L": "second pluperfect",
    "2X": "second perfect",
}
VOICE = {
    "A": "active",
    "M": "middle",
    "P": "passive",
    "E": "middle or passive",
    "D": "middle deponent",
    "O": "passive deponent",
    "N": "middle or passive deponent",
    "Q": "impersonal active",
    "X": "no voice stated",
}
MOOD = {
    "I": "indicative",
    "S": "subjunctive",
    "O": "optative",
    "M": "imperative",
    "N": "infinitive",
    "P": "participle",
}
PERSON = {"1": "1st person", "2": "2nd person", "3": "3rd person"}

# Trailing segments mean different things depending on the part of speech: an
# "N" on a particle marks negation, while on a noun it marks a proper name.
# Guessing wrong here would misdescribe the text, so the tables are per-head.
SUFFIX_BY_HEAD = {
    "N": {
        "P": "proper name (person)",
        "L": "place name",
        "T": "title or divine name",
        "PG": "gentilic (a people group)",
        "LG": "gentilic formed from a place name",
        "PRI": "proper noun (indeclinable)",
        "OI": "indeclinable",
        "LI": "letter of the alphabet",
        "NUI": "numeral (indeclinable)",
        "HEB": "Hebrew term carried over into Greek",
        "ARAM": "Aramaic term carried over into Greek",
        "ABB": "abbreviation",
    },
    "A": {
        "N": "negative",
        "S": "superlative",
        "C": "comparative",
        "NUI": "numeral (indeclinable)",
        "PRI": "indeclinable",
        "T": "title or divine name",
        "L": "place name",
        "P": "proper name (person)",
        "PG": "gentilic (a people group)",
        "LG": "gentilic formed from a place name",
    },
    "PRT": {
        "N": "negative",
        "I": "interrogative",
        "K": "correlative",
    },
    "ADV": {
        "N": "negative",
        "I": "interrogative",
        "S": "superlative",
        "C": "comparative",
        "K": "correlative",
        "T": "title or divine name",
        "L": "place name",
    },
    "INJ": {
        "HEB": "Hebrew term carried over into Greek",
        "ARAM": "Aramaic term carried over into Greek",
    },
    "V": {
        "HEB": "Hebrew term carried over into Greek",
        "ARAM": "Aramaic term carried over into Greek",
    },
    "CONJ": {"N": "negative", "I": "interrogative"},
    "T": {"T": "title or divine name"},
}

# Plain-language notes for the grammatical features most likely to change how a
# reader understands a verse. Shown as short "why it matters" hints.
FEATURE_NOTES = {
    "aorist": "Views the action as a single whole, without commenting on how long it took.",
    "imperfect": "Ongoing or repeated action in the past — 'was doing', not merely 'did'.",
    "perfect": "A completed action whose result still stands.",
    "pluperfect": "An action completed before some other past point.",
    "present": "Ongoing or characteristic action; in narrative it can heighten immediacy.",
    "future": "Action expected to occur.",
    "middle": "The subject is somehow involved in or affected by its own action.",
    "passive": "The subject receives the action rather than performing it.",
    "middle or passive": "Form is ambiguous — context decides whether the subject acts on itself or is acted upon.",
    "middle deponent": "Middle in form but active in meaning.",
    "passive deponent": "Passive in form but active in meaning.",
    "subjunctive": "Presents the action as possible, intended, or contingent rather than factual.",
    "imperative": "A command or appeal.",
    "participle": "A verbal adjective — describes while it acts ('believing', 'having come').",
    "infinitive": "The action named in the abstract, often expressing purpose or result.",
    "optative": "Expresses a wish — rare, and always deliberate.",
    "vocative": "Direct address — someone is being spoken to.",
    "genitive": "Typically 'of' — possession, source, or the sphere something belongs to.",
    "dative": "Typically 'to/for/with' — the indirect object, means, or location.",
    "negative": "Negates what follows.",
}


def _decode_verb(segments):
    """Decode the segments following a V- head."""
    features = []
    unknown = []
    if not segments:
        return features, unknown

    tvm = segments[0]
    if len(tvm) >= 2 and tvm[0] == "2":
        tense, rest = tvm[:2], tvm[2:]
    else:
        tense, rest = tvm[:1], tvm[1:]
    voice = rest[0] if len(rest) >= 1 else None
    mood = rest[1] if len(rest) >= 2 else None

    resolved = True
    for table, key, label in (
        (TENSE, tense, "tense"),
        (VOICE, voice, "voice"),
        (MOOD, mood, "mood"),
    ):
        if key is None:
            continue
        if key in table:
            features.append((label, table[key]))
        else:
            resolved = False
            break
    if not resolved:
        features = []
        unknown.append(tvm)

    for seg in segments[1:]:
        if len(seg) == 2 and seg[0] in PERSON and seg[1] in NUMBER:
            features.append(("person", PERSON[seg[0]]))
            features.append(("number", NUMBER[seg[1]]))
        elif len(seg) == 3 and seg[0] in CASE and seg[1] in NUMBER and seg[2] in GENDER:
            features.append(("case", CASE[seg[0]]))
            features.append(("number", NUMBER[seg[1]]))
            features.append(("gender", GENDER[seg[2]]))
        elif seg in SUFFIX_BY_HEAD.get("V", {}):
            features.append(("note", SUFFIX_BY_HEAD["V"][seg]))
        else:
            unknown.append(seg)
    return features, unknown


def _decode_nominal(head, segments):
    """Decode case/number/gender segments for everything that is not a verb."""
    features = []
    unknown = []
    suffixes = SUFFIX_BY_HEAD.get(head, {})

    for seg in segments:
        # Possessive pronouns encode the possessor too: S-1SGSN is a 1st person
        # singular possessor in the genitive singular neuter.
        if (
            len(seg) == 5
            and seg[0] in PERSON
            and seg[1] in NUMBER
            and seg[2] in CASE
            and seg[3] in NUMBER
            and seg[4] in GENDER
        ):
            features.append(("possessor", f"{PERSON[seg[0]]} {NUMBER[seg[1]]}"))
            features.append(("case", CASE[seg[2]]))
            features.append(("number", NUMBER[seg[3]]))
            features.append(("gender", GENDER[seg[4]]))
        # Reflexive pronouns: F-1GSM, F-3ASM.
        elif (
            len(seg) == 4
            and seg[0] in PERSON
            and seg[1] in CASE
            and seg[2] in NUMBER
            and seg[3] in GENDER
        ):
            features.append(("person", PERSON[seg[0]]))
            features.append(("case", CASE[seg[1]]))
            features.append(("number", NUMBER[seg[2]]))
            features.append(("gender", GENDER[seg[3]]))
        # Personal pronouns carry person as well: P-1AS, P-2DP.
        elif len(seg) == 3 and seg[0] in PERSON and seg[1] in CASE and seg[2] in NUMBER:
            features.append(("person", PERSON[seg[0]]))
            features.append(("case", CASE[seg[1]]))
            features.append(("number", NUMBER[seg[2]]))
        elif len(seg) == 3 and seg[0] in CASE and seg[1] in NUMBER and seg[2] in GENDER:
            features.append(("case", CASE[seg[0]]))
            features.append(("number", NUMBER[seg[1]]))
            features.append(("gender", GENDER[seg[2]]))
        elif len(seg) == 2 and seg[0] in CASE and seg[1] in NUMBER:
            features.append(("case", CASE[seg[0]]))
            features.append(("number", NUMBER[seg[1]]))
        elif len(seg) == 2 and seg[0] in PERSON and seg[1] in NUMBER:
            features.append(("person", PERSON[seg[0]]))
            features.append(("number", NUMBER[seg[1]]))
        elif seg in suffixes:
            features.append(("note", suffixes[seg]))
        else:
            unknown.append(seg)
    return features, unknown


def _decode_single(code):
    """Decode one morphology code with no crasis component."""
    parts = code.split("-")
    head = parts[0]
    segments = parts[1:]

    if head not in PART_OF_SPEECH:
        return {
            "code": code,
            "summary": code,
            "pos": None,
            "features": [],
            "notes": [],
            "unknown": [code],
        }

    pos = PART_OF_SPEECH[head]
    if head == "V":
        features, unknown = _decode_verb(segments)
    else:
        features, unknown = _decode_nominal(head, segments)

    values = [value for _, value in features]
    summary = ", ".join([pos] + values) if values else pos
    return {
        "code": code,
        "summary": summary,
        "pos": pos,
        "features": [{"label": label, "value": value} for label, value in features],
        "notes": [],
        "unknown": unknown,
    }


def _attach_notes(result):
    notes = []
    seen = set()
    for feature in result["features"]:
        value = feature["value"]
        note = FEATURE_NOTES.get(value)
        if note and value not in seen:
            seen.add(value)
            notes.append({"feature": value, "note": note})
    result["notes"] = notes
    return result


def decode(code):
    """Turn a morph code into a structured, human-readable description.

    Returns a dict with the raw code, a one-line summary, the parsed features,
    plain-language notes, and any segments that could not be identified.
    """
    code = (code or "").strip()
    if not code:
        return None

    # Some words are a crasis of two words (κἀγώ = καί + ἐγώ). STEPBible writes
    # these as "P-1NS + G2532=CONJ", so decode each half and join them.
    if " + " in code:
        merged = {
            "code": code,
            "summary": "",
            "pos": None,
            "features": [],
            "notes": [],
            "unknown": [],
        }
        summaries = []
        for index, piece in enumerate(code.split(" + ")):
            piece = piece.strip()
            if "=" in piece:
                piece = piece.split("=", 1)[1].strip()
            part = _decode_single(piece)
            summaries.append(part["summary"])
            if index == 0:
                merged["pos"] = part["pos"]
            merged["features"].extend(part["features"])
            merged["unknown"].extend(part["unknown"])
        merged["summary"] = " + ".join(s for s in summaries if s)
        _attach_notes(merged)
        merged["notes"].insert(
            0,
            {
                "feature": "crasis",
                "note": "Two words fused into one form — the Greek contracts them together.",
            },
        )
        return merged

    return _attach_notes(_decode_single(code))
