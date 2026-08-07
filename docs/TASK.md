# English translation and glossary support

Extend the CAD translator from Chinese ↔ French to Chinese ↔ English, with terminology that actually controls high-risk CAD labels.

## Deliverables

1. Keep the four translation modes and target-based `fr_`, `en_`, and `zh_` output prefixes.
2. Make every existing language-pair glossary apply when a complete CAD text entity exactly matches a term.
3. Add Chinese → English and English → Chinese YAML glossaries for ambiguous building, structural, and MEP terms.
4. Include the new YAML files in the Windows package.
5. Retain the existing DeepL fallback for non-glossary text and DXF/DWG conversion workflow.
6. Refine Chinese ↔ French structural, MEP, and room-label terminology, including corrections for known mistranslations.

## Glossary rule

- A glossary is an exact, case-insensitive match after text cleaning.
- Exact labels use the glossary value directly and do not consume a DeepL request.
- Longer or unmatched text continues through DeepL; no global substring replacement is allowed because terms such as `板`, `墙`, and `管` are context-dependent.

## Non-goals

- No second translation provider, automatic terminology extraction, or generic dictionary.
- Do not change the source DWG or DXF; translated files remain separate outputs.

## Current task: batch translation queue

Status (2026-08-07): complete. The confirmed UI is the clockwise rotated-triangle layout: queue at upper-left (70% of the left column), live log at lower-left (30%), and translation settings filling the right column. One batch has one shared target language; it supports Chinese ↔ French and Chinese ↔ English, persists state, serializes ODA conversion, and limits work to two files per DeepL key and three globally.
