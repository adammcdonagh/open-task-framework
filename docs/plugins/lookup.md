# Lookup plugins — details

This document describes the built-in `lookup` plugins and examples of how to use them.

## Table of contents

- [Files to inspect](#files-to-inspect)
- [lookup.file](#lookupfile)
- [lookup.http_json](#lookuphttp_json)
- [lookup.random_number](#lookuprandom_number)
- [Authoring and testing tips](#authoring-and-testing-tips)
- [Example usage](#example-usage)

## Files to inspect

- `src/opentaskpy/plugins/lookup/file.py`
- `src/opentaskpy/plugins/lookup/http_json.py`
- `src/opentaskpy/plugins/lookup/random_number.py`

## lookup.file

- Purpose: read content from a local file and return it (optionally trimmed or parsed).
- Expected config:
  - `path` (string): absolute or repo-relative path to file
  - `mode` (optional): how to interpret content (e.g., `text`, `json`)

## lookup.http_json

- Purpose: GET a JSON payload from a URL and extract a nested value.
- Expected config:
  - `url` (string): HTTP(S) endpoint
  - `path` (string): dot/bracket path into JSON response (e.g., `items[0].id`)
- Notes: Tests should mock HTTP responses. Prefer `requests` mocking.

## lookup.random_number

- Purpose: return a random integer in a configured range. Useful for test fixtures and variance.
- Expected config:
  - `min` (int), `max` (int)

## Authoring and testing tips

- Validate plugin input early — raise informative errors for missing required keys.
- Keep side effects limited: prefer to return data instead of writing to disk.
- Add unit tests that use deterministic seeds for randomness-based plugins.

## Example usage (YAML templating):

```yaml
my_value: !lookup.file
  path: "./examples/variables.json.j2"

api_value: !lookup.http_json
  url: "https://api.example.test/data"
  path: "items[0].name"
```

If you add a new plugin, document it here and add tests under `tests/`.
