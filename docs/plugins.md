# Lookup Plugins — built-in plugin index and guidance

Plugins are small, reusable helpers that can be referenced in task payloads to compute values at runtime (for example: lookups, templating helpers). Plugins live under `src/opentaskpy/plugins/` and are intentionally lightweight.

## Table of contents

- [Lookup Plugins — built-in plugin index and guidance](#lookup-plugins--built-in-plugin-index-and-guidance)
  - [Table of contents](#table-of-contents)
  - [Built-in plugins](#built-in-plugins)
  - [How to write a plugin](#how-to-write-a-plugin)
  - [Notes](#notes)

## Built-in plugins

- `lookup.file` — read a value from a local file
- `lookup.http_json` — fetch JSON over HTTP and extract a value
- `lookup.random_number` — generate a random number (useful for tests)

These are primarily included for demonstration purposes, it is not likely these will be useful in production.

## How to write a plugin

1. Create a new module in your own configuration under a director named `plugins`. Plugins are auto discovered if they live under your configuration directory.
2. Write a function that performs the task you need to return the appropirate result, optionally taking arguments from the Jinja template.

## Notes

- Plugins should be very simple and return almost immediately. These are often going to be called on every task execution, unless using lazy loading, meaning slow calls will slow down startup times of everything.
- Plugins should validate their input and raise clear exceptions for missing fields or bad responses.
