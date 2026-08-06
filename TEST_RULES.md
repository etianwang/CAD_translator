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
