# Third-party notices

## Bible text
The World English Bible is in the public domain. Translation publisher and rights statement: https://ebible.org/engwebp/copyright.htm and https://worldenglish.bible/ . The name identifies this translation; no endorsement is implied.

Bundled verse text is derived from JSON text data in https://github.com/TehShrike/world-english-bible/tree/master/json , retrieved 24 October 2026. Only Bible verse text was extracted; upstream application/build code was not copied. Paragraph and line fragments belonging to each verse were joined and whitespace normalised. `data/source_hashes.json` records SHA-256 hashes of each downloaded source file. This is a static snapshot; it is not claimed to be the latest publisher revision.

## Runtime dependencies
- Streamlit: Apache-2.0 — https://github.com/streamlit/streamlit
- python-pptx: MIT — https://github.com/scanny/python-pptx
- PyMuPDF: AGPL-3.0 or a commercial licence — https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright

TCC Worship source is released under AGPL-3.0-or-later to accompany the open-source PDF processing dependency. Preserve licence notices and make the corresponding source available when distributing or providing a modified network-accessible version as required by that licence. See LICENSE.

## Worship application references
Holyrics, FreeShow, Quelea and OpenLP are referenced as workflow inspirations or separately installed applications. None of their code, branding assets, song catalogues or Bible packages is included. Their names belong to their respective owners. FreeShow's optional REST interface is documented at https://freeshow.app/api . No bundled song text is taken from commercial catalogues; the sample song is original demonstration text.

The source snapshot has empty text entries at Luke 17:36, Acts 8:37, Acts 15:34, Acts 24:7, Romans 16:25. These empty entries are not selectable. No replacement scripture has been invented.

The supplied TCC logo is church artwork supplied by the user, included as provided. The project software licence does not grant rights to reuse the church logo or identity.

## Curated Bible catalogue — 24 October 2026

The optional catalogue uses AO Lab's Free Use Bible API: https://bible.helloao.org/ and its per-translation permissions metadata and links. Selected IDs: BSB, eng_kjv, eng_web, eng_asv, eng_bbe, eng_fbv, eng_dby, eng_ylt, eng_rv5, eng_wbs, eng_gnv, eng_lsv.

The source marks ten selected editions public domain. KJV printing rights in the United Kingdom remain subject to Crown Letters Patent; that notice is retained. Free Bible Version (Copyright © 2018 Dr. Jonathan Gallagher) and Literal Standard Version (Copyright © 2020 Covenant Press) are distributed under CC BY-SA 4.0: https://creativecommons.org/licenses/by-sa/4.0/. For those editions the app retrieves and retains source copyright/licence notices, carries attribution into prepared scripture items and embeds the notices with Bible data in offline exports. Verse wording is not rewritten; formatting, commentary and study annotations are not represented as verse text.

Publisher references: https://ebible.org/Scriptures/details.php?id=engfbv and https://ebible.org/Scriptures/details.php?id=englsv. Catalogue snapshot metadata is retained under data/bible_catalogue.json.gz.b64. Bible texts are downloaded only when selected; the existing WEB remains available offline.
