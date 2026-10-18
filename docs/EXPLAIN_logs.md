# Log evidence input

- The CSV schema is `employee_id,access_level,event`.
- Access levels are `direct`, `indirect`, or `none`; they map to prior weights 1, 0.05, and 0.
- Event names must match the factors documented by the fusion module.
- Repeated rows retain the strongest access level and each distinct event once.
- Unknown employees, malformed fields, empty files, and unknown events are rejected.
- Example: rows with `indirect` and `direct` access produce the `direct` prior.
- These are explicit demo weights, not calibrated likelihoods from real logs.
