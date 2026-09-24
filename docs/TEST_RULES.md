# Test rules

Before merging, run these checks:

1. Compile the Python modules containing translation, DWG conversion, and API logic.
2. Assert every mode maps to the expected DeepL language pair and output prefix.
3. Assert representative glossary entries bypass DeepL and return the configured translation.
4. Assert Azure Translator v3 uses Azure language codes and that F0 error `403001` fails without queue retry.
5. Build the React frontend.
6. Perform a human-style DWG round trip with a real Chinese drawing:
   - launch the normal app flow with ODA File Converter and a valid DeepL API Key;
   - translate Chinese → English, verify the generated name begins with `en_` and the output DWG is readable;
   - translate that DWG English → Chinese, verify the generated name begins with `zh_` and the output DWG is readable;
   - compare extracted text entities to confirm that both passes changed text.

The final DWG test consumes DeepL API quota.

## v1.9.0 language-asset acceptance

1. Verify provider-success records include direction, provider, drawing filename, timestamps, hit count, and manual status; glossary and cache hits do not create provider records.
2. Verify records are searchable by source/target keyword and filterable by direction, provider, manual status, and one of the latest ten distinct drawing filenames; verify paging reaches older records.
3. Verify editing a record changes the next same-direction translation without a provider request and clears the running cache.
4. Verify promotion to a direction term makes it override built-in YAML and provider records, regardless of provider or layer.
5. Verify `S.A.S`, `s-a-s`, `S_A_S`, and `SAS` are equivalent, while `A-01` and `A01` remain different.
6. Verify local legacy terms migrate into direction terms once, and an existing `.hcterms.json` file is neither read nor modified.

## v1.9.1 professional-classification acceptance

1. Verify all four directions accept `general`, `electrical`, `hvac`, `plumbing`, `architecture`, and `decoration`; invalid values are rejected.
2. Verify the selected professional user term, built-in term, and record each override their general counterpart according to the v1.9.1 priority order.
3. Verify a general term and record provide the fallback for a selected professional, but a record for another professional does not.
4. Verify legacy SQLite terms and records migrate once to `general`, without data loss.
5. Verify the frontend starts at 通用, sends the selected classification with single and batch requests, and a started batch keeps its original classification.

## v1.9.2 intelligent split-text merging acceptance

1. Verify `智能合并拆行文字` defaults to off and that off preserves individual `TEXT` translation requests and write-back.
2. Verify an aligned two- or three-line short room label is translated once as a joined source and the translated output is reflowed to the original number of `TEXT` entities.
3. Verify differing layer, style, height, rotation, alignment, excessive gap, long text, `MTEXT`, attributes, dimensions, tables, and block-definition text are not grouped.
4. Verify a joined source still uses the selected professional term before a general term or provider.
5. Verify both single and batch API requests accept the Boolean setting, and an already started batch retains its initial value.

## Mandatory real-user E2E release gate

No executable may be marked release-ready until this test passes through the desktop UI, using valid Azure Translator and DeepL credentials. API keys must be configured locally and must never be written to test output, source files, logs, or reports.

Run all four directions with **each** provider (eight successful translations total): Chinese→French, French→Chinese, Chinese→English, and English→Chinese. For every run, use the same user-visible flow: add or drag in a CAD file, choose the provider/direction/output options, then click **Start translation**. Do not call translator internals as a substitute for these clicks. The credential-isolation check is mandatory: every DeepL run has only a DeepL Key configured (Azure Key empty), and every Azure run has only an Azure Key configured (DeepL Key empty).

For every run, randomly choose one supported output format (`source`, `dxf`, or `dwg`) and one supported output version; record the chosen combination. A run passes only when all of the following are true:

- the queue reports success and the live log contains no error;
- the output file exists and opens successfully through ezdxf/ODA as applicable;
- extracted output text is translated correctly for the target language and is not merely the source text;
- the user clicks **Export logs**, saves the UTF-8 text file, and the saved file is non-empty and readable;
- the user clicks **Locate file** on the completed task and Windows Explorer or macOS Finder opens with that output selected.

The final report must list each provider, direction, selected format/version, output path, openability result, translated-text check, log-export path, and locate-file result. Any failure blocks release.

## Batch queue tests

Follow the automated and real-DWG acceptance cases in [BATCH_TRANSLATION_HARNESS.md](BATCH_TRANSLATION_HARNESS.md), including queue recovery, pause/resume, retry, output formats and versions, all four language directions, and safe API concurrency.

Status (2026-08-07): completed. Python compilation, translation-mode/glossary tests, batch recovery/queue-operation tests, and React build passed. The specified real DWG completed Chinese → French → Chinese and Chinese → English → Chinese; all four output DWGs were readable and extracted text changed on every pass. API keys were neither logged nor persisted in queue state.

Packaging status: Windows packages with `pyinstaller --clean --noconfirm Honsen_CAD_Translator_v1.9.0.spec` and verifies `dist/Honsen_CAD_Translator_v1.9.0.exe`. macOS packages independently with `python installer/build_macos.py --oda-dmg /path/to/ODAFileConverter_macOS.dmg --dmg` and verifies `dist/Honsen CAD Translator.app` plus `dist/Honsen_CAD_Translator_v1.9.0_macOS_arm64.dmg`. Before external distribution, perform a desktop launch smoke test and a real DWG round trip with the platform's ODA File Converter.

macOS ODA layout rule (2026-08-15): `installer/build_macos.py` validates and embeds the complete architecture-matched official DMG at `Honsen CAD Translator.app/Contents/Resources/ODAFileConverter.dmg`. Runtime mounts it read-only, calls the signed ODA application from that volume, and detaches it on normal shutdown; never copy only the ODA executable. Automated checks must cover embedded-DMG and adjacent-app fallback lookup. Before distribution, require stable outer signature after a runtime smoke check, ODA Gatekeeper acceptance, notarization, and the real DWG round trip.

macOS ODA filename/window rule (2026-08-15): before every ODA conversion, stage the source as an ASCII `input.dwg` or `input.dxf` file in a private temporary directory. ODA 27.1 fails to match command-line filters made from decomposed Unicode macOS filenames (for example French accented names) and otherwise opens its GUI with “There is no matched files in input folder”. When the executable belongs to an `.app` bundle, launch it through LaunchServices as `open -g -j -W -n -a ODAFileConverter.app --args …` as a best-effort request not to activate or show it; ODA can override those flags and foreground its own Qt window, so this is not a `nowindow` guarantee. The original source and requested output path must remain unchanged; automated checks must cover this staging and launch path. ODA has no supported truly headless macOS mode, so a strict no-window product requirement needs a separately licensed non-GUI conversion engine; retain the ezdxf direct-executable fallback for non-bundle executables.

Queue execution rule (2026-08-07): adding files must not start ODA or DeepL work. Verify a task remains `queued` until the user selects **开始翻译**, and verify original translator logs appear in the live-log panel after startup.

Pause rule (2026-08-07): verify each task shows an independent progress bar and percentage; pausing must block further queue work and the original translation loop after its current ODA or DeepL call finishes. The queue control belongs below the API Key and changes from **开始翻译** to **暂停** to **继续**.

Close rule (2026-08-07): closing the desktop window must cancel batch work, persist running tasks as `queued`, and leave no non-daemon queue worker able to keep the process alive.

Shutdown enforcement: after state persistence and cancellation, the close control must force the application process to exit; verify no `Honsen_CAD_Translator_v1.9.0.exe` process remains after closing the window.

Recovery and stop rule (2026-08-07): after restart, recovered tasks must remain idle until **继续** is clicked. **停止** must cancel the batch and restore **开始翻译**; **清空列表** is available only after the batch is stopped/completed, never while it is running or paused.

Restart settings rule (2026-08-07): after **停止**, the next batch **开始翻译** resets cancelled tasks and applies the settings currently shown at right. A task-level **重翻** must instead retain that task's original saved direction, output format/version, output directory, and block option.

ODA version rule (2026-08-07): the version picker lists ACAD9 through ACAD2018 as supported by local ODA/ezdxf; selected versions are finalized through ODA for DXF and DWG output.

ODA working-copy rule (2026-08-17): use the ODA identifier `ACAD2010` for the internal DWG → DXF working copy. Do not pass ezdxf's display label `R2010` to ODA; ODA rejects it as an invalid output version.

CAD text-coverage rule (2026-08-17): the desktop block-definition option is enabled by default and must translate title blocks, reusable legends, and sheet-index text. With the option disabled, extraction must still include visible anonymous `*T` (table) and `*D` (dimension) blocks. Translate explicit `DIMENSION.dxf.text` overrides, but preserve the standard `<>` measurement placeholder. For native `ACAD_TABLE` entities, translate and write back the authoritative `AcDbTable` cell strings as well as their rendered `*T` representation, otherwise AutoCAD may restore the original text when the table is regenerated. Regression coverage must include an anonymous table text item, an `ACAD_TABLE` source-cell write-back, and both cases of dimension override text.

ODA legacy-text rule (2026-08-17): decode ODA's `\\M+5xxxx` GBK text escapes before validating or translating entity text. This encoding is used by ODA in affected paper-space layouts (including the reported Layout1); otherwise valid Chinese is incorrectly treated as invalid control text and skipped. Preserve unrelated CAD format controls and cover Chinese plus accented-Latin GBK escapes in regression tests.

Reliability rule (2026-08-08): automated checks must cover atomic queue/config persistence and corrupted-state recovery, bounded task/upload/SSE retention, atomic output delivery, backend rejection of unknown ODA versions, and preservation of Azure settings by the legacy UI's DeepL-key save action.

Licensing rule (2026-08-08): when `LICENSE_ENFORCEMENT_ENABLED` is enabled, verify a 30-day network-time trial, a valid signed activation code, an expired activation code, and that blocked licences cannot call translation or queue API routes. When disabled, assert that no network-time request occurs. Never place the vendor private key or a customer activation code in source, logs, or test reports.
