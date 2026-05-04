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
    "extract-texture-disc-root",
    "extract-egame-car",
    "preview-egame-car",
    "extract-egame-shop-textures"
  ]
}
```

### `health-check`

Arguments: none.

Returns Python executable/version, dependency availability, and whether `bchunk` is discoverable on `PATH`. Missing optional dependencies are reported in `data`; this command should not fail simply because a parser dependency is missing.

Current dependencies checked:

- Required for Swift backend readiness:
  - `pycdlib`
  - `PIL.Image` / Pillow
  - `lzsslib`
- Optional or legacy UI/helper paths:
  - `tkinter`
  - `customtkinter`
  - `colorama`
  - `lzstring`
  - `elftools` / pyelftools

The command returns JSON even when required modules are missing. `data.bheReady` is `false` and `data.missingRequiredDependencies` lists each unavailable required module.

This check is intentionally truthful about the current app boundary: Q's Factory bundles the Python source bridge and pinned Python packages under `Contents/Resources/backend/vendor`, but it does not yet bundle the Python runtime itself.

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

For Road Trip / HG2 / HG3 sources, `scan-iso` returns the same safe e-Game file listing as `scan-egame-disc-root`, using ISO records for sector and offset metadata where available. Export/preview is claimed only for supported car body rows; replacement validation and source writes are not supported.

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

Supported e-Game car body rows report `support: "exportable"` and `canExtract: true`. Other e-Game rows report `support: "scan-only"` or `support: "unsupported"` with a truthful `unsupportedReason`.

### `scan-egame-disc-root <folder-path>`

Reads a mounted Road Trip / HG2 / HG3 volume or extracted disc root containing `SYSTEM.CNF` and the expected e-Game folder layout.

This command does not import BHE CPK/APT parser internals and does not require `pycdlib`. It maps known `*.BIN` files into the shared Swift table model:

- car bodies and part bins as `model` / `part`
- course and activity bins as `course`
- field bins as `field`
- shop bins as `shop`

Model export is claimed only for supported car body rows through `extract-egame-car`. Shop texture export is claimed only for supported HG2 `SHOP/Txx.BIN` rows through `extract-egame-shop-textures`. Other e-Game rows remain scan-only.

Each e-Game entry may include optional metadata for Swift:

- `descriptor`
- `modelDescription`
- `expectedExportOutputs`
- `supportReason`
- `unsupportedReason`
- `sectionNames`
- `partSectionNames`
- `supportedOperations`

### `extract-egame-car <disc-root-or-iso> <entry-id> --output-folder <folder>`

Exports one Road Trip / HG2 / HG3 car body entry to a user-selected folder.

Supported entry IDs:

- `egame:/CAR0/Qxx.BIN` through `egame:/CAR4/Qxx.BIN`
- `egame:/CARS/Qxx.BIN`

The backend reads the selected mounted disc root or ISO read-only and writes only inside the requested output folder. It returns a typed manifest:

```json
{
  "operationID": "extract-egame-car",
  "sourceModified": false,
  "patchedCopyWritten": false,
  "entryIDs": ["egame:/CAR0/Q00.BIN"],
  "outputRoot": "/path/out/Q01",
  "primaryPreviewPath": "/path/out/Q01/Q00-0-0-body.obj",
  "files": [
    {"path": "/path/out/Q01/Q00.png", "kind": "texture", "role": "diffuse", "previewable": true},
    {"path": "/path/out/Q01/Q00-0-0-body.obj", "kind": "model", "role": "body", "previewable": true}
  ],
  "overwrittenFiles": [],
  "warnings": []
}
```

`sourceModified` and `patchedCopyWritten` must stay `false` for this command.

### `preview-egame-car <disc-root-or-iso> <entry-id> --output-folder <folder>`

Writes the same safe OBJ/MTL/PNG preview assets as `extract-egame-car`, but marks `operationID` as `preview-egame-car`. The app may point this at a temporary preview cache. `sourceModified` and `patchedCopyWritten` must stay `false`.

### `extract-egame-shop-textures <disc-root-or-iso> <entry-id> --output-folder <folder>`

Exports decoded PNG textures from supported Road Trip / HG2 town shop entries.

Supported entry IDs:

- `egame:/SHOP/T00.BIN` through `egame:/SHOP/T20.BIN`

Unsupported shop/game-data rows return structured errors or scan-only metadata. The backend reads the selected mounted disc root or ISO read-only and writes only inside the requested output folder. The manifest shape matches the other safe export commands:

```json
{
  "operationID": "extract-egame-shop-textures",
  "sourceModified": false,
  "patchedCopyWritten": false,
  "entryIDs": ["egame:/SHOP/T04.BIN"],
  "outputRoot": "/path/out/Mushroom Road",
  "primaryPreviewPath": "/path/out/Mushroom Road/T04-00.png",
  "files": [
    {"path": "/path/out/Mushroom Road/T04-00.png", "kind": "texture", "role": "texture-00", "previewable": true}
  ],
  "overwrittenFiles": [],
  "warnings": []
}
```

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

## Packaging Prep

Current builds bundle Python source under `Contents/Resources/backend` and pinned Python packages under `Contents/Resources/backend/vendor`. They do not bundle Python itself.

Distribution needs a signed, notarized, self-contained helper/runtime. Preferred paths:

- PyInstaller or equivalent frozen backend helper that keeps `bhe_json.py` as the Swift-facing command boundary.
- Bundled Python framework or app-private virtual environment with pinned wheels for the required parser modules.

Every nested helper, runtime framework, executable, dynamic library, and bundled Python extension must be signed as part of the app bundle, then verified under the hardened runtime and notarized distribution build.

`bchunk` is not bundled in this phase. Bundling it requires license review because common `bchunk` distributions are GPL-licensed. Until that review is complete, Q's Factory should only detect installed/user-provided `bchunk` and show explicit conversion guidance.

Any dependency help UI must be explicit and non-mutating:

- no silent `sudo`
- no shell-string execution
- no hidden Homebrew/pip/system mutation
- any future install helper must show exactly what it will run and use `Process` arguments rather than a single shell command string

## Credits

Created by catsandsoup.

The current app wraps and preserves the existing Python parser work under `choroq/`. Keep source comments and attribution intact when moving code across the Swift/backend boundary.

Existing e-Game mesh and texture research is credited in the parser comments and README, including Xentax/ZenHAX-derived notes, Acewell's BMS script notes, and killercracker's 3DS Max script work.
