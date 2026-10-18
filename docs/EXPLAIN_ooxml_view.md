# Explain: OOXML explorer (Case 4)

A .docx file is a ZIP package of XML parts. The explorer lists every part and size,
then reads:
- `docProps/core.xml`: creator, lastModifiedBy, created/modified, revision
  (user-editable, so weak evidence);
- `docProps/app.xml`: Template, TotalTime, Application (also editable);
- `docProps/custom.xml`: custom properties;
- `word/settings.xml`: the rsid list; `rsidRoot` is the first editing session;
- `word/document.xml`: how often each rsid appears on paragraphs and runs, and
  tracked changes (`w:ins` / `w:del` with author and date).

Reliability: rsids are structural (written by the editor on every save session,
rarely edited by hand), so they rank above lastModifiedBy and Template, which any
user can type. Parsing disables entities and network access.

Worked example: a leak shows lastModifiedBy = E006 and Template = Template-41.dotx
(both decoys), but rsidRoot = 9A3F10C2, which the IT rsid registry lists for E003.
The reliable finding is "copy issued to E003".
