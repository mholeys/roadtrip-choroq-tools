# Q's Factory Backend Contract

This document defines the Swift-facing backend contract for the Q's Factory macOS app.

The SwiftUI app must treat this contract as the stable boundary. Python parser internals can change, but Swift should only depend on the command names, arguments, response envelope, and semantic fields documented here.

## Architecture Boundary

- SwiftUI app: native windows, source import, sidebars, tables, previews, save panels, progress, and user-facing errors.
- Swift backend adapter: launches one backend command process, reads stdout JSON, reads stderr diagnostics, and decodes typed responses.
- Python bridge: `choroq/bhe/bhe_json.py`; the only layer that imports upstream parser internals.
- Vendored parser engine: existing Python modules under `choroq/`.

The current bridge is read-only for ISO content. It can write preview/export PNG files requested by the user, but it does not modify source disc images and does not write patched ISO copies.

## Versioning

Every stdout response is a single JSON object with this envelope:

```json
{
  "protocolVersion": 1,
  "backendVersion": "0.4.0",
  "status": "ok",
  "data": {}
}
```

Errors use the same envelope:

```json
{
  "protocolVersion": 1,
  "backendVersion": "0.4.0",
  "status": "error",
  "error": {
    "title": "Python Dependencies Missing",
    "explanation": "The Python BHE parser dependencies are not available to this Python runtime.",
    "suggestion": "Install the project Python dependencies, then try again.",
    "technicalDetails": "ModuleNotFoundError: No module named 'pycdlib'",
    "relatedEntryID": null,
    "safeToRetry": true,
    "originalISOModified": false,
    "patchedCopyWritten": false
  }
}
```

Swift currently supports protocol version `1`. A backend with a higher protocol version should be rejected until the app knows how to decode it. A backend with the same protocol version but different capabilities should be surfaced through `version`, `health-check`, and `list-supported-types`.

## Commands

### `version`

Arguments: none.

Returns backend metadata and command names.

```json
{
  "protocolVersion": 1,
  "backendVersion": "0.4.0",
  "readOnly": true,
  "commands": [
    "version",
            "health-check",
            "list-supported-types",
            "scan-iso",
            "scan-disc-root",
            "scan-egame-disc-root",
            "preview-texture",
            "preview-texture-disc-root",
            "extract-texture",
            "extract-texture-disc-root"
  ]
}
```

### `health-check`

Arguments: none.

Returns Python executable/version, dependency availability, and whether `bchunk` is discoverable on `PATH`. Missing optional dependencies are reported in `data`; this command should not fail simply because a parser dependency is missing.

Current dependencies checked:

- `tkinter`
- `customtkinter`
- `PIL.Image` / Pillow
- `colorama`
- `lzstring`
- `elftools` / pyelftools
- `pycdlib`

### `list-supported-types`

Arguments: none.

Returns supported source and entry types. Current source support:

- `iso`: supported for read-only scan through `pycdlib`.
- `bin/cue`: planned helper flow; convert to ISO with `bchunk`.
- `folder`: supported mounted-volume/disc-root scan.

Current entry support:

- APT texture entries: scan, preview, extract to PNG.
- APT containers, PBL/MPD/HPD/MPC models, TOC/FONT text, LZS compressed entries, and unknown entries: scan/inspect only.

Write support is currently:

```json
{
  "originalISOModification": false,
  "patchedCopyWriting": false,
  "replacementValidation": false
}
```

### `scan-iso <iso-path>`

Reads a PlayStation 2 ISO in read-only mode.

For Barnhouse Effect sources, returns:

- `iso`: boot ID, ISO name, detected game title, variant, CPK count, texture count.
- `containers`: CPK container summaries.
- `entries`: flattened entries suitable for Swift tables and inspectors.

The bridge opens the ISO with `pycdlib.open(..., "rb")`.

For Road Trip / HG2 / HG3 sources, `scan-iso` returns the same read-only e-Game file listing as `scan-egame-disc-root`, using ISO records for sector and offset metadata where available. No preview, extraction, replacement validation, or write support is claimed for these entries.

### `preview-texture <iso-path> <entry-id> --output <png-path>`

Reads one supported APT texture and writes a preview PNG to the requested path. This is intended for temporary preview caches owned by the app.

The source ISO is not modified.

### `extract-texture <iso-path> <entry-id> --output <png-path>`

Reads one supported APT texture and writes a user-requested PNG export path.

The source ISO is not modified. Existing output files may be overwritten when the user chooses that path through the native save panel.

### `scan-disc-root <folder-path>`

Reads a mounted volume or extracted disc root containing `SYSTEM.CNF`.

For Barnhouse Effect sources, the command scans `DATA/*.CPK` files and returns CPK/APT entries.

For Road Trip / HG2 / HG3 sources, the command delegates to the read-only e-Game scanner and returns known folders/files as generic Swift entries. Current e-Game scanning recognizes:

- `CAR0` through `CAR4`
- `CARS`
- `COURSE`
- `ACTION`
- `FLD`
- `SHOP`

e-Game entries are currently scan-only: `support` is `read-only`, `canExtract` is `false`, and `canReplace` is `false`.

### `scan-egame-disc-root <folder-path>`

Reads a mounted Road Trip / HG2 / HG3 volume or extracted disc root containing `SYSTEM.CNF` and the expected e-Game folder layout.

This command does not import BHE CPK/APT parser internals and does not require `pycdlib`. It maps known `*.BIN` files into the shared Swift table model:

- car bodies and part bins as `model` / `part`
- course and activity bins as `course`
- field bins as `field`
- shop bins as `shop`

No model preview, model extraction, texture preview, replacement validation, or write support is claimed yet.

### `preview-texture-disc-root <folder-path> <entry-id> --output <png-path>`

Disc-root equivalent of `preview-texture` for BHE mounted folders.

### `extract-texture-disc-root <folder-path> <entry-id> --output <png-path>`

Disc-root equivalent of `extract-texture` for BHE mounted folders.

## Stderr

Stdout is reserved for machine-readable JSON. Parser diagnostics and incidental Python output must be redirected to stderr.

## Planned Commands

- `extract-container-textures <iso-path> <container-id> --output <folder>`.
- e-Game model extraction commands for supported HG2/HG3 car assets.
- `validate-replacement <iso-path> <entry-id> <png-path>`.
- `replace-texture-copy <iso-path> <entry-id> <png-path> --output-copy <iso-path>`.
- NDJSON progress for long-running extraction and copy operations.
