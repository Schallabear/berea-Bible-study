# Attribution

The data under `data/` is redistributed from the sources below. These notices
travel with the data, in this repository and in anything built from it.

## Berean Standard Bible — English text

The Berean Bible text was placed in the public domain (CC0) on 30 April 2023 by
the BSB translation team and BSB Publishing. No licence is required for any use;
attribution is appreciated but not required.

<https://bereanbible.com/>

## STEPBible-Data — tagged Greek text and lexicon

Licensed under **Creative Commons Attribution 4.0 International (CC BY 4.0)**.

- **TAGNT** — Translators Amalgamated Greek New Testament. Greek text covering
  the words of NA27/28, TR, SBLGNT, Tregelles, Byzantine, Westcott-Hort, and
  THGNT, with each word marked for which editions contain it, and tagged
  lexically (disambiguated Strong's numbers) and morphologically.
- **TBESG** — Translators Brief lexicon of Extended Strong's for Greek,
  incorporating Abbott-Smith's *A Manual Greek Lexicon of the New Testament*.

Created by Tyndale House, Cambridge, for STEP Bible.
<https://github.com/STEPBible/STEPBible-Data> · <https://www.stepbible.org/>

## OpenBible.info — cross-references

Cross-reference dataset licensed under **Creative Commons Attribution (CC BY)**,
derived primarily from the Treasury of Scripture Knowledge, with relevance
weightings from reader votes.

<https://www.openbible.info/labs/cross-references/>

Obtained via the CC BY expanded CSV at <https://github.com/shandran/openbible>.

## Changes made

The build script (`scripts/build_data.py`) reformats these sources without
altering their substance: filtering to the books included here, restructuring
into per-chapter JSON, decoding morphology codes into readable English
(`scripts/morphology.py`), and converting lexicon markup to safe HTML. No
scripture text, lexicon content, or cross-reference data was edited.
