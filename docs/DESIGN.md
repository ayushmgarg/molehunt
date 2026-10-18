# MoleHunt design direction

## Concept in five lines

An examiner’s desk after hours, lit by a task lamp.
Case folders, stamped evidence tags, and paper notes give the bench its physical cues.
The default bench is dim; the paper dossier stays warm and legible.
UV violet appears only when hidden content is revealed.
Every mark communicates through shape and text as well as colour.

## Design tokens

These are the proposed frozen tokens. In the application they live in one token module; styles are derived from that module rather than set ad hoc in widgets.

### Colour

| Token | Value | Use |
|---|---|---|
| `paper` | `#EFE9DC` | Dossier surfaces, primary text on dim surfaces |
| `ink` | `#1B1F24` | Text on paper, deep panel surface |
| `graphite` | `#3A4048` | Raised dim surface, secondary rules |
| `tag_amber` | `#D9822B` | Evidence tags, selection and action accents |
| `seal_red` | `#B3261E` | Broken custody, seal ink |
| `uv_violet` | `#7C5CFF` | Revealed hidden content and its ribbon only |
| `bench_bg` | `#14171A` | Default application background |
| `focus` | `#EFE9DC` | Keyboard focus outline on dark surfaces |

Use paper text on dim surfaces and ink text on paper. Keep small text at 4.5:1 contrast or greater. Amber and seal red are accents; do not use them alone for small text or state. UV marks pair a violet field/glow with a high-contrast glyph and explicit state marker. The match, mismatch, and erasure symbols differ by shape, not just colour.

### Type scale

| Token | Size / line height | Family and use |
|---|---|---|
| `case_title` | 28 / 34 px | Source Serif 4, dossier titles |
| `section` | 20 / 26 px | Source Serif 4, section headings |
| `body` | 16 / 24 px | Source Serif 4, case prose and notes |
| `label` | 13 / 18 px | IBM Plex Mono, controls and evidence metadata |
| `data` | 14 / 20 px | IBM Plex Mono, code points, offsets, hashes |
| `stamp` | 18 / 22 px | Special Elite, stamp impressions only |
| `margin_note` | 16 / 20 px | Caveat, one-line examiner notes only |

Bundle all four typefaces and their OFL license files for offline use. Do not use the display faces for long passages. Provide a readable system fallback during development and for missing-font cases.

### Spacing and shape

| Token | Value | Use |
|---|---:|---|
| `space_1` | 4 px | Glyph / label gap |
| `space_2` | 8 px | Compact control gap |
| `space_3` | 12 px | Form rows |
| `space_4` | 16 px | Standard inset |
| `space_6` | 24 px | Panel inset |
| `space_8` | 32 px | Major section gap |
| `radius_tag` | 2 px | Evidence tags and paper edges |
| `radius_control` | 3 px | Buttons and inputs |
| `radius_panel` | 4 px | Work surfaces |
| `stroke_hairline` | 1 px | Dividers and custody links |

Use squared paper corners, small radii, and clear dividers. No equal rounded-card grid, decorative gradients, or texture above 4% opacity.

### Motion

| Token | Value | Use |
|---|---:|---|
| `press` | 120 ms | Button / seal press |
| `lamp` | 180 ms | Bench dim transition and UV reveal |
| `panel` | 220 ms | Dossier and panel transition |
| `reduced_motion` | 0 ms | Skip interpolation; apply final state |

Motion confirms an action and never gates access to evidence. Honour the operating system reduced-motion setting.

## Component inventory

| Component | States |
|---|---|
| Case folder tabs | closed, selected, pinned |
| Evidence tree row | idle, selected, hashed, missing, read-only |
| Evidence tag | intact, selected, dragged, filed, custody-broken |
| Seal stamp | ready, pressing, sealed, verification-failed |
| UV lamp toggle | off, switching, on |
| Hex viewport | loading, normal, UV reveal, selected byte, truncated view, read error |
| Bit ribbon | hidden, visible, selected slot |
| Slot matrix cell | match circle, mismatch cross, erasure dash, selected |
| Timeline rail | idle, selected, pinned, linked-to-tag |
| Notebook finding | empty, edited, linked-to-evidence, saved |
| Primary / secondary button | idle, hover, focus, pressed, disabled |
| Personnel card | idle, selected, linked-to-event |
| Report preview | draft, validated, exported, export-error |

Hex view, slot matrix, timeline, and bit ribbon are custom-painted and virtualized. Widgets call only the core API facade; forensic logic stays in the engine. A file-backed page source and visible-row painting keep large evidence files from being loaded into the widget. Analysis runs on a worker thread. Every interactive component has a keyboard path, visible focus, and accessible text/state. No embedded web view.

## Screen sketches

### 1. Case dossier cover

```text
┌ MOLEHUNT ──────────────────────────────────────────────── ? ┐
│ [C-01 CASE FOLDER]  [C-02]  [C-03]                         │
│                                                            │
│ CASE 01 / THE INVISIBLE COPY      PERSONNEL                │
│ ┌ brief: <= 50 words ─────────┐  ┌ Mira Sen ────────────┐  │
│ │ Synthetic case brief.       │  │ Records / evening    │  │
│ └────────────────────────────┘  │ “The copier ran late.”│  │
│ EVIDENCE                         └───────────────────────┘  │
│ [tag C-01 / E-01 / HASH / READY]  [tag ...]                 │
│                                             [OPEN DOSSIER]  │
└────────────────────────────────────────────────────────────┘
```

### 2. Bench: evidence, viewer, notebook

```text
┌ C-01 / EVIDENCE ─────────────── UV OFF ─────── NOTEBOOK ──┐
│ case folder tree │ offset | hex bytes | decoded text       │
│ ▸ leak.txt       │ 0000   4D 65 65 74 20 ...   Meet ...    │
│   badge.csv      │        selected byte / code point       │
│   print.log      │ evidence tags drag to note or report    │
│                  │                                         │
│ SHA-256: …       │ [ADD FINDING] [SAVE NOTE] [MAKE REPORT]  │
└────────────────────────────────────────────────────────────┘
```

### 3. UV reveal

```text
┌ E-01 / leak.txt ─────────────────────── UV ON ────────────┐
│ HIDDEN SLOTS: 04                 [UV LAMP: ON]             │
│ offset | raw code points | text                            │
│ 0010   4D 65 65 74 E2 80 8B 20  ...                        │
│                         ··· violet glow ···                 │
│ ── slot 01  U+200B  bit 1 ── slot 02  U+2060  decoy ───── │
│ [TAG SELECTED SLOT]                         [UV LAMP: OFF] │
└────────────────────────────────────────────────────────────┘
```

### 4. Slot matrix

```text
┌ CANDIDATES × OBSERVED SLOTS ──────────────────────────────┐
│             01 02 03 04 05 06 07 08   MATCHES / N         │
│ Mira Sen     ○  ○  ×  ○  —  ○  ○  ○       6 / 7           │
│ Dev Rao      ×  ○  ○  ×  —  ○  ×  ○       3 / 7           │
│ Noor Das     ○  ×  ×  ○  —  ×  ○  ×       3 / 7           │
│ ○ match   × mismatch   — erasure                              │
│ Select cell → linked evidence offset; erasure excluded       │
└────────────────────────────────────────────────────────────┘
```

### 5. Timeline

```text
┌ CASE EVENTS ──────────────────────────────────────────────┐
│ 18:04         19:17          21:42          22:08         │
│   ●────────────●──────────────●──────────────●             │
│ badge in     file open      print job      leak found      │
│    └────────────── thread to evidence tags ──────┘         │
│ [PIN EVENT] [FILTER SOURCE]                [CUSTODY STRIP] │
└────────────────────────────────────────────────────────────┘
```

### 6. Report preview

```text
┌ REPORT / C-01 ────────────────────────────────────────────┐
│ CASE DOSSIER                    seal: SHA-256  7F20A1C4   │
│ Question / material examined / method / findings          │
│ Candidate | n | matches | log10 LR | verbal scale          │
│ Limit: copy attribution does not identify the actor.        │
│ [linked evidence tags]  [custody chain]  [bench results]    │
│ [BACK TO NOTEBOOK]                      [EXPORT DOCX]       │
└────────────────────────────────────────────────────────────┘
```

## Signature interactions

1. **UV lamp.** The lamp is a keyboard-operable toggle. Switching it on dims non-evidence chrome, reveals hidden code points and slot boundaries in violet, and shows a one-line bit ribbon directly above the text. The ribbon reports slot index, observed bit or erasure, and source offset. Violet is reserved for this revealed content. Toggling off restores the prior bench brightness and selection. Motion takes 180 ms or zero when reduced motion is enabled.
2. **Seal and custody.** Hashing an evidence item computes SHA-256 from its read-only original, displays the first eight hex characters and intake time in an ink stamp, then appends the custody entry. A bottom strip draws custody entries as linked ticks in order. Verification checks the complete hash chain; the first invalid link and later dependent links turn seal red and receive a text failure state. Hash work runs off the UI thread.
3. **Evidence tags.** Every artefact gets a draggable tag containing case number, item number, hash8, and status. Dragging to a notebook finding links that exact evidence item and source location; dropping into the report includes its citation. Keyboard users can focus a tag, invoke “File tag,” and choose the notebook or report destination. Filed tags remain linked to their source and hash.
4. **Slot matrix.** Candidate rows and slot columns use circle for match, cross for mismatch, and dash for erasure, alongside accessible text. Hovering or selecting a non-erased cell highlights the corresponding text span and offset in the viewer; selecting an erasure shows why the slot could not be read. Erasures are never counted as mismatches. Keyboard arrows navigate cells; Enter pins the linked slot.
5. **Timeline rail.** Events are ordered by timestamp on a horizontal, keyboard-navigable rail. Pinning an event draws a thin connector to the related evidence tag and opens the source details. Ties share a timestamp lane and retain deterministic input order. Filtering by source hides unrelated events without changing the event data; clearing the filter restores the full rail.

## Text and interaction budget

- All interface strings live in one strings file. A test rejects labels longer than seven words; case brief and report content use explicit allowlists.
- A case brief is at most 50 words, followed by its evidence list.
- The help “?” sheet has at most five lines.
- Tooltips fit one line. Prefer a visible state or direct manipulation over explanatory prose.
- Examiner voice is dry and procedural. No “Welcome,” “Unlock,” “Seamless,” emoji, exclamation marks, em dashes, filler text, or generic dashboard copy.
- Button and panel text stays short; data is shown as evidence, not marketing copy.

## Style tile

The companion `docs/ui/style_tile.png` is a rendered specimen of an evidence tag, seal, normal and UV hex rows, a slot strip, personnel card, and button states. The machine lacks the requested offline typefaces, so the specimen uses installed Georgia and Cascadia Mono as clearly provisional stand-ins. The final application should bundle the selected OFL families and license files before its typography is frozen.
