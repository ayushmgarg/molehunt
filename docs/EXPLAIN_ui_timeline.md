# Timeline panel

- Case 3's generated timestamped CSV is filled into the Evidence tools timeline field.
- The timeline loader reads one or more semicolon-separated event files and sorts by normalized UTC time.
- A text filter searches timestamps, employee IDs, event names, devices, printer IDs, and source filenames.
- Selecting a row is the timeline brush; Pin selected event adds it to the visible pinned findings list.
- Repeated pin actions do not duplicate an identical event.
- Example: filtering for `print` leaves the print-job row; pinning it records its time, employee, event, and source.

Brush: shift-click or drag a block of rows; the label shows the time window (first to last event, minutes, people involved) and 'Pin selected events' pins the whole block.
