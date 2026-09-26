# English translation and glossary support

Extend the CAD translator from Chinese ↔ French to Chinese ↔ English, with terminology that actually controls high-risk CAD labels.

## Deliverables

1. Keep the four translation modes and target-based `fr_`, `en_`, and `zh_` output prefixes.
2. Make every existing language-pair glossary apply when a complete CAD text entity exactly matches a term.
3. Add Chinese → English and English → Chinese YAML glossaries for ambiguous building, structural, and MEP terms.
4. Include the new YAML files in the Windows package.
5. Retain the existing DeepL fallback for non-glossary text and DXF/DWG conversion workflow; Azure Translator F0 is an optional second provider.
6. Refine Chinese ↔ French structural, MEP, and room-label terminology, including corrections for known mistranslations.

## Glossary rule

- A glossary is an exact, case-insensitive match after text cleaning.
- Exact labels use the glossary value directly and do not consume a DeepL request.
- Longer or unmatched text continues through DeepL; no global substring replacement is allowed because terms such as `板`, `墙`, and `管` are context-dependent.

## Non-goals

- No Google Cloud provider, automatic terminology extraction, or generic dictionary. Azure support is limited to Translator Text v3 with F0 quota handling.
- Do not change the source DWG or DXF; translated files remain separate outputs.

## Current task: v1.9.4 facade professional classification

Implement [PRD_v1.9.4.md](PRD_v1.9.4.md): add the fixed local `facade`/“幕墙” classification to the existing professional-aware terminology, records, single/batch settings, and language-assets UI. Keep one direction glossary/library/record store, preserve general fallback, and never send the classification to providers.

## Previous task: v1.9.3 secure automatic updates

Implement [PRD_v1.9.3.md](PRD_v1.9.3.md): check the stable GitHub Release in the background, accept only a newer SHA-256-digested Inno Setup installer, and let the Windows desktop application download, verify, close, install, and restart. Do not self-overwrite the running EXE or auto-install macOS DMGs.

## Previous task: v1.9.2 intelligent split-text merging

Implement the confirmed optional CAD label preprocessor in [PRD_v1.9.2.md](PRD_v1.9.2.md). It is disabled by default, only joins conservatively matched short standalone `TEXT` lines, translates the joined label once, and reflows the result back to the original entities. It must work with the existing professional-classification lookup and batch settings snapshot.

## Previous task: v1.9.1 professional classification terminology

Implement the confirmed local professional-classification workflow in [PRD_v1.9.1.md](PRD_v1.9.1.md). It uses one glossary and one editable library per language direction, with professional fields inside each term; it never sends classification context to a provider.

## Previous task: v1.9.0 direction terminology and translation records

Implement the confirmed v1.9.0 workflow in [PRD_v1.9.0.md](PRD_v1.9.0.md). The product has four independent direction terminology libraries and provider-result translation records; no project-package or layer-based terminology lookup remains.

## Previous task: batch translation queue

Status (2026-08-07): complete. The confirmed UI is the clockwise rotated-triangle layout: queue at upper-left (70% of the left column), live log at lower-left (30%), and translation settings filling the right column. One batch has one shared target language; it supports Chinese ↔ French and Chinese ↔ English, persists state, serializes ODA conversion, and limits work to two files per DeepL key and three globally.
