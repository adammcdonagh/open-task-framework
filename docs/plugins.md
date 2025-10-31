# Plugins — built-in plugin index and guidance

Plugins are small, reusable helpers that can be referenced in task payloads to compute values at runtime (for example: lookups, templating helpers). Plugins live under `src/opentaskpy/plugins/` and are intentionally lightweight.

## Table of contents

- [Built-in plugin families](#built-in-plugin-families)
- [Where plugins are used](#where-plugins-are-used)
- [How to author a plugin](#how-to-author-a-plugin)
- [Example usage](#example-usage)
- [Notes](#notes)

## Built-in plugin families

- `lookup` — helpers that resolve values from different sources. Built-in lookup plugins include:
  - `lookup.file` — read a value from a local file
  - `lookup.http_json` — fetch JSON over HTTP and extract a value
  - `lookup.random_number` — generate a random number (useful for tests)

## Where plugins are used

- Variable interpolation and templating across tasks and examples under `examples/`
- Tests that need small deterministic helpers without external dependencies

## How to author a plugin

1. Create a new module under `src/opentaskpy/plugins/<family>/`.
2. Export a callable that accepts a plugin configuration dict and returns a value or raises a descriptive exception.
3. Add unit tests under `tests/` covering expected inputs and errors.

## Example usage

Example — using `lookup.http_json` (pseudo-config)

```yaml
someVar: !lookup.http_json
  url: "https://api.example.com/data"
  path: "items[0].id"
```

## Notes

- Keep plugins deterministic when possible to make tests reliable.
- Avoid long-running IO in plugins used by unit tests; mock external calls in tests.
- Plugins should validate their input and raise clear exceptions for missing fields or bad responses.
