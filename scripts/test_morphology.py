#!/usr/bin/env python3
"""Checks for the morphology decoder. Run: python3 scripts/test_morphology.py

These lock in the cases that are easy to get subtly wrong — where a segment
means different things depending on the part of speech, and where an incorrect
parse would tell the reader something false about the text.
"""

import sys

from morphology import decode

CASES = [
    # (code, expected summary)
    ("N-NSM", "noun, nominative, singular, masculine"),
    ("V-IAI-3S", "verb, imperfect, active, indicative, 3rd person, singular"),
    ("V-PAP-NSM", "verb, present, active, participle, nominative, singular, masculine"),
    ("V-2AAI-3S", "verb, second aorist, active, indicative, 3rd person, singular"),
    ("T-NSM", "article, nominative, singular, masculine"),
    ("PREP", "preposition"),
    ("CONJ", "conjunction"),
    # "N" on a particle means negative, NOT "proper name" — οὐ, not a name.
    ("PRT-N", "particle, negative"),
    # ...and the same letter on an adjective is also negative (οὐδείς).
    ("A-ASM-N", "adjective, accusative, singular, masculine, negative"),
    # ...while on a noun it does mark a proper name.
    ("N-NSM-P", "noun, nominative, singular, masculine, proper name (person)"),
    ("N-NSF-LG", "noun, nominative, singular, feminine, gentilic formed from a place name"),
    ("N-NPM-PG", "noun, nominative, plural, masculine, gentilic (a people group)"),
    ("N-ASM-T", "noun, accusative, singular, masculine, title or divine name"),
    ("INJ-HEB", "interjection, Hebrew term carried over into Greek"),
    # Personal, reflexive, and possessive pronouns each encode person differently.
    ("P-1AS", "personal pronoun, 1st person, accusative, singular"),
    ("P-2DP", "personal pronoun, 2nd person, dative, plural"),
    ("F-3ASM", "reflexive pronoun, 3rd person, accusative, singular, masculine"),
    ("S-1SGSN", "possessive pronoun, 1st person singular, genitive, singular, neuter"),
    # Crasis: two words fused into one form (κἀγώ = καί + ἐγώ).
    ("P-1NS + G2532=CONJ",
     "personal pronoun, 1st person, nominative, singular + conjunction"),
]


def main():
    failures = []

    for code, expected in CASES:
        result = decode(code)
        if result is None:
            failures.append(f"{code}: decoded to None")
            continue
        if result["summary"] != expected:
            failures.append(f"{code}:\n    expected {expected!r}\n    got      {result['summary']!r}")
        if result["unknown"]:
            failures.append(f"{code}: unresolved segments {result['unknown']}")

    # Plain-language notes should fire for features that change the meaning.
    aorist = decode("V-AAI-3S")
    if not any(n["feature"] == "aorist" for n in aorist["notes"]):
        failures.append("V-AAI-3S: expected a note explaining the aorist")

    # Crasis should say so.
    crasis = decode("P-1NS + G2532=CONJ")
    if not any(n["feature"] == "crasis" for n in crasis["notes"]):
        failures.append("crasis: expected a note explaining the fused form")

    # An unrecognised code must surface itself rather than inventing a parse.
    unknown = decode("Z-QQQ")
    if unknown["summary"] != "Z-QQQ" or not unknown["unknown"]:
        failures.append("Z-QQQ: unknown codes must be reported, not guessed at")

    if decode("") is not None or decode(None) is not None:
        failures.append("empty code should decode to None")

    if failures:
        print(f"FAILED ({len(failures)})\n")
        for f in failures:
            print(f"  {f}")
        return 1

    print(f"ok — {len(CASES)} codes decoded correctly, notes and fallbacks behave")
    return 0


if __name__ == "__main__":
    sys.exit(main())
