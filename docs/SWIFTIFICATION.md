# Choro-Q BHE Swiftification Plan

This document captures the first native macOS direction for the BHE tool. The
goal is not to replace the Python reverse-engineering work. The goal is to put a
Mac-native interface around it, make destructive operations safer, and give the
asset workflow the structure users expect from a desktop utility.

## Product Summary

`roadtrip-choroq-tools` is a Python toolkit for extracting and modifying assets
from PlayStation 2 Choro Q games. The current BHE release focuses on the
Barnhouse Effect games:

- Choro-Q HG1 / Penny Racers
- Choro-Q HG4
- Choro Q Works
- Shin Combat Choro-Q

The BHE workflow opens a PS2 ISO, identifies the game through `SYSTEM.CNF`,
walks `DATA/*.CPK` containers, parses supported subfiles, previews APT textures,
extracts textures as PNG, and replaces compatible texture entries.

## Current Architecture

The current implementation is Python-first:

- `choroq/bhe/bhe_cpk.py`: CPK container parser and subfile dispatch.
- `choroq/bhe/aptexture.py`: APT texture parsing, palette handling, PNG export,
  and image preview generation.
- `bhe_extractor.py`: command-line extraction pipeline for BHE CPK files.
- `choroq/bhe/moddingui/main.py`: CustomTkinter ISO browser and tree/detail UI.
- `choroq/bhe/moddingui/modules/apt_option_handler.py`: extract and replace
  actions for APT texture entries.
- `choroq/bhe/moddingui/modules/preview_handler.py`: Tk canvas texture preview.

The GUI directly owns ISO state, parser calls, tree state, context menus,
warnings, file dialogs, metadata rendering, and replacement writes. This keeps
the implementation compact, but it also makes UX improvements riskier because
UI and mutation logic are tightly coupled.

## Current GUI Pathway

If the current pre-release works as intended, the release path is:

1. Keep the parser/editor logic in Python.
2. Add CustomTkinter controls and right-click actions as new formats become
   understood.
3. Package the Python GUI with PyInstaller / auto-py-to-exe.
4. Ask users to navigate through a tree view and use context menus for actions.

This is a valid pathway for a technical pre-release, but it hides important
actions, gives little batch support, and makes in-place ISO mutation easy to do
by accident.

## Native macOS Direction

The SwiftUI app should become a native shell around the Python asset engine.
Keep Python as the source of truth for binary formats until a parser is stable
enough to port intentionally.

Recommended layers:

1. SwiftUI app: windows, navigation, tables, preview, validation, commands, and
   user-facing state.
2. Swift backend client: typed JSON interface and process execution.
3. Python JSON bridge: command-line adapter that calls existing BHE parser code.
4. Existing Python parsers: CPK, APT, LZS, model, text, and replacement logic.

This separation lets the Mac app iterate on UX without rewriting every binary
format parser.

## MVP Scope

The first useful native release should cover BHE texture browsing and safe
single-texture replacement:

- Open ISO using a native file dialog.
- Detect game title and variant.
- Show CPK containers and supported subfiles.
- Show a sortable texture table with name, type, format, dimensions, palette,
  offset, size, and support status.
- Preview texture alpha on a checkerboard background.
- Extract a selected texture to PNG.
- Validate a replacement PNG before writing.
- Write replacements to a patched ISO copy by default.
- Keep context menus, but expose primary actions in the toolbar and detail pane.

Out of scope for the first SwiftUI pass:

- Full model export UI.
- Compressed-data replacement.
- Bulk patch authoring.
- Porting the Python parsers to Swift.

## JSON Boundary

The Swift app should call a Python bridge that returns structured JSON. The
initial commands can be small:

```text
bhe-json scan-iso <iso-path>
bhe-json preview-texture <iso-path> <entry-id> --output <png-path>
bhe-json extract-texture <iso-path> <entry-id> --output <folder>
bhe-json validate-replacement <iso-path> <entry-id> <png-path>
bhe-json replace-texture <iso-path> <entry-id> <png-path> --output-copy <iso-path>
```

Example scan response:

```json
{
  "iso": {
    "id": "SLUS_209.30",
    "isoName": "CHOROQ_HG4.iso",
    "gameTitle": "Choro-Q HG4",
    "variant": "US",
    "cpkCount": 12,
    "textureCount": 428
  },
  "entries": [
    {
      "id": "3DMAP.CPK:14:10",
      "cpkName": "3DMAP.CPK",
      "name": "kan001",
      "kind": "texture",
      "format": "4",
      "width": 128,
      "height": 64,
      "paletteSize": 16,
      "sizeBytes": 4112,
      "offsetBytes": 12345678,
      "sector": 6028,
      "support": "supported",
      "canExtract": true,
      "canReplace": true
    }
  ]
}
```

The Swift app should treat this contract as stable even while the Python
internals continue changing.

## UX Principles

Follow macOS conventions instead of styling the app like a custom game tool:

- Use `NavigationSplitView` for container navigation and detail inspection.
- Use `Table` for dense sortable asset metadata.
- Use native `fileImporter` and save panels for ISO, PNG, and output selection.
- Use toolbar buttons, menu commands, keyboard shortcuts, and context menus.
- Use semantic colors and system materials so Light Mode, Dark Mode, and
  increased contrast work automatically.
- Use SF Symbols with text labels when the action is not universally obvious.
- Do not communicate support state by color alone; pair status with symbols and
  labels.
- Do not require right-click for essential actions.
- Do not mutate the original ISO by default.

## Roadmap

### Phase 1: Native Shell

- SwiftPM macOS app target.
- Mock backend client.
- Sidebar, table, detail pane, checkerboard preview, toolbar actions.
- Written JSON contract for the Python bridge.

### Phase 2: Python Bridge

- Add `bhe-json` Python entrypoint.
- Implement `scan-iso` from existing CPK/APT code.
- Generate preview PNGs through the current `APTexture.get_image()` path.
- Report parse errors as structured JSON instead of console text.

### Phase 3: Safe Editing

- Implement replacement validation as a separate dry-run command.
- Add patched-copy ISO workflow.
- Add overwrite handling for extraction.
- Add operation log and error recovery.

### Phase 4: Power Workflows

- Batch extraction.
- Search by texture name, format, dimensions, and CPK.
- Duplicate-name warnings.
- Compressed-entry visibility and diagnostics.
- Model/text extraction surfaces when the backend is ready.

## Open Questions

- Which macOS deployment target should the native app support?
- Should the shipped app bundle include Python, or require an external Python
  runtime during early development?
- Should `replace-texture` ever support direct in-place ISO writes, or only copy
  output?
- What should be the stable entry identifier for nested CPK/APT entries when
  compressed data support changes offsets?
- Which BHE game/version should be the first integration fixture?
