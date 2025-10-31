# Open Task Framework — Overview

This folder contains human- and agent-oriented documentation for the Open Task Framework (OTF). Use these docs to understand core concepts, the package layout, how plugins and handlers are structured, and concrete examples for using built-in handlers.

## Table of contents

- [Architecture](./architecture.md)
- [Remote handlers](./remotehandlers.md)
- [Task handlers](./taskhandlers.md)
- [Plugins](./plugins.md)
- [Lookup plugins](./plugins/lookup.md)
- [Usage](./usage.md)

## Files in this docs folder

- `architecture.md` — high-level architecture and component responsibilities
- `remotehandlers.md` — built-in remote handlers, usage notes and examples
- `taskhandlers.md` — execution/transfer/batch task flow and responsibility mapping
- `plugins.md` — index of built-in plugins and how to author new ones
- `plugins/lookup.md` — details for the lookup plugin family
- `usage.md` — copy-and-paste examples for common tasks and CI/test commands

## Quick start

1. Read `architecture.md` to understand the components.
2. Use `usage.md` to run unit tests and a local quick example.
3. Inspect `src/opentaskpy/remotehandlers` and `src/opentaskpy/plugins` for concrete handler implementations and examples.

If you want additional docs (diagrams, developer onboarding checklist, or API docs), tell me which and I will add them.
