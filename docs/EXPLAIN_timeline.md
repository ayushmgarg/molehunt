# Event timeline merge

- Each CSV needs a timestamp (`timestamp` or `ts`), `employee_id`, and `event` or `action`.
- Optional device and printer columns are carried into the merged event record.
- ISO timestamps with a timezone are converted to UTC; timestamps without one are treated as UTC.
- The combined events are sorted by timestamp, source filename, employee ID, then event name.
- Sorting N events costs `O(N log N)`; all rows remain available for filtering in the UI.
- Example: a 10:00 UTC print row sorts after a 09:15 UTC badge entry even when input files are passed in reverse order.
