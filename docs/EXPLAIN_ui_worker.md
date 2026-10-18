# UI background worker

- `TaskWorker` receives a zero-argument callable and runs it once when its Qt slot is invoked.
- It emits the return value on `completed`, an exception summary on `failed`, and always emits `finished`.
- The window moves the worker object to a `QThread`; the engine operation stays outside the UI event loop.
- Example: candidate scoring returns an immutable result for the main thread to display.
- Qt widgets are updated only by the window after receiving a worker signal.
