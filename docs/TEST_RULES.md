# Test rules

Before merging, run these checks:

1. Compile the Python modules containing translation, DWG conversion, and API logic.
2. Assert every mode maps to the expected DeepL language pair and output prefix.
3. Assert representative glossary entries bypass DeepL and return the configured translation.
4. Build the React frontend.
5. Perform a human-style DWG round trip with a real Chinese drawing:
   - launch the normal app flow with ODA File Converter and a valid DeepL API Key;
   - translate Chinese → English, verify the generated name begins with `en_` and the output DWG is readable;
   - translate that DWG English → Chinese, verify the generated name begins with `zh_` and the output DWG is readable;
   - compare extracted text entities to confirm that both passes changed text.

The final DWG test consumes DeepL API quota.

## Batch queue tests

Follow the automated and real-DWG acceptance cases in [BATCH_TRANSLATION_HARNESS.md](BATCH_TRANSLATION_HARNESS.md), including queue recovery, pause/resume, retry, output formats and versions, all four language directions, and safe API concurrency.

Status (2026-08-07): completed. Python compilation, translation-mode/glossary tests, batch recovery/queue-operation tests, and React build passed. The specified real DWG completed Chinese → French → Chinese and Chinese → English → Chinese; all four output DWGs were readable and extracted text changed on every pass. API keys were neither logged nor persisted in queue state.

Packaging status (2026-08-07): `pyinstaller --clean --noconfirm Honsen_CAD_Translator_v1.7.0.spec` passed and produced `dist/Honsen_CAD_Translator_v1.7.0.exe`. Before external distribution, perform a desktop launch smoke test with the adjacent local `ODAFileConverter/` directory.

Queue execution rule (2026-08-07): adding files must not start ODA or DeepL work. Verify a task remains `queued` until the user selects **开始翻译**, and verify original translator logs appear in the live-log panel after startup.

Pause rule (2026-08-07): verify each task shows an independent progress bar and percentage; pausing must block further queue work and the original translation loop after its current ODA or DeepL call finishes. The queue control belongs below the API Key and changes from **开始翻译** to **暂停** to **继续**.

Close rule (2026-08-07): closing the desktop window must cancel batch work, persist running tasks as `queued`, and leave no non-daemon queue worker able to keep the process alive.

Shutdown enforcement (2026-08-07): after state persistence and cancellation, the close control must force the application process to exit; verify no `Honsen_CAD_Translator_v1.7.0.exe` process remains after closing the window.

Recovery and stop rule (2026-08-07): after restart, recovered tasks must remain idle until **继续** is clicked. **停止** must cancel the batch and restore **开始翻译**; **清空列表** is available only after the batch is stopped/completed, never while it is running or paused.

Restart settings rule (2026-08-07): after **停止**, the next batch **开始翻译** resets cancelled tasks and applies the settings currently shown at right. A task-level **重翻** must instead retain that task's original saved direction, output format/version, output directory, and block option.

ODA version rule (2026-08-07): the version picker lists ACAD9 through ACAD2018 as supported by local ODA/ezdxf; selected versions are finalized through ODA for DXF and DWG output.
