# Choro-Q BHE Mac App Interaction Design

## Product Framing

The native Mac app is a Choro-Q Barnhouse Effect archive workbench. It helps people open a legally obtained PlayStation 2 ISO, browse the game's CPK containers, inspect known asset formats, preview APT textures with transparency, export PNGs, validate replacement art, and eventually create patched ISO copies without touching the original disc image.

The app should feel like a careful preservation and modding tool, not an admin panel or a parser debugger. The game content is the hero: file structure, textures, offsets, dimensions, palette data, support state, exports, and patch results. The interface should respect the original Python reverse-engineering work by making it safer, clearer, and more Mac-native.

## Users

Primary users:

- Choro-Q fans who want to browse game assets and extract textures.
- Modders who understand image formats and need safe replacement workflows.
- Reverse engineers who need offsets, sectors, identifiers, and unsupported-file visibility.
- The original developer, who should recognize the existing parser knowledge without seeing internal scaffolding in the UI.

Secondary users:

- Non-technical fans who may only want to open an ISO and export PNGs.
- Contributors who need a clear boundary between SwiftUI presentation and Python binary-format logic.

## User Expectations

When opening a Mac asset or modding tool, people expect:

- Native file dialogs, menus, toolbar actions, keyboard shortcuts, search, and contextual menus.
- A stable sidebar/table/inspector workflow instead of a wizard.
- Dense metadata in tables, with sortable and filterable columns.
- Clear disabled states that explain why an action is unavailable.
- Batch operations for exports, with progress and completion history.
- A way to reveal exported or patched files in Finder.
- Recoverable errors in plain language, with technical details available on demand.

When opening a game ISO, people expect:

- The app to identify the game and region before presenting assets.
- Opening to be read-only unless they explicitly create a patched copy.
- CPK containers to appear as the main library structure.
- Unsupported and compressed entries to remain inspectable, not silently disappear.
- Slow scans to show progress and remain cancelable when possible.
- The original ISO to remain unchanged by default.

## Safety Principles

Texture replacement must feel safe, reversible, and inspectable.

- Never mutate the original ISO by default.
- Use "Create Patched Copy..." as the normal write path.
- Show a preflight summary before writing: original ISO, destination copy, entry name, container, offset, dimensions, format, palette size, and expected byte size.
- Validate dimensions, color format, palette size, color count, converted byte size, and compression status before enabling patch creation.
- Treat compressed, unknown, oversized, or partially understood entries as read-only unless validation explicitly supports them.
- Record every operation in an operation log.
- Offer "Reveal in Finder" after extraction or patch creation.
- Hide direct in-place writes behind a future advanced setting and require a destructive confirmation if ever implemented.

## HIG Interpretation

This app is a productivity utility on macOS. It should use the platform's power instead of a custom game-like shell.

- Use `NavigationSplitView` for sidebar plus asset table, with an inspector for selection details.
- Use `Table` for dense entries and metadata.
- Keep the sidebar native: source-list rows, one icon, one title, one short detail line.
- Put frequently used commands in the toolbar and every toolbar command in the menu bar.
- Keep contextual menus as a secondary path for selection-specific actions.
- Use semantic colors, system fonts, system materials, and SF Symbols.
- Do not over-tint. Accent only primary actions or meaningful status affordances.
- Do not put Liquid Glass on table rows or content cards. Let system toolbar/sidebar chrome handle the navigation layer.
- Prefer clear labels for actions with risk or ambiguity. "Replace in Patched Copy..." is better than "Replace".
- Use ellipses for actions that need another choice before completion.
- Use confirmation dialogs for writes and destructive closes with pending operations.

## Q's Factory Theme Direction

The app should feel like a cheerful toy-car service garage without copying PlayStation 2 UI literally.

- Use native macOS structure first: split view, sidebar, toolbar, search, table, inspector, forms, sheets, and menus.
- Use Q's Factory blue as the primary accent color.
- Use hazard yellow only for caution or needs-review states.
- Keep neutral system surfaces as the base UI in both Light and Dark Mode.
- Express the theme through terminology such as Garage, Service Bay, Part Specs, Inspect, and Extract.
- Prefer SF Symbols that match the workbench metaphor: `wrench.and.screwdriver`, `car`, `road.lanes`, `storefront`, `shippingbox`, and `photo`.
- Do not add heavy textures, repeated hazard stripes, custom dialogue boxes, or novelty controls.

## Window And Navigation Model

Recommended main window:

1. Sidebar: ISO summary and CPK containers.
2. Detail: searchable, filterable table of entries for the selected container.
3. Inspector: selected entry preview, metadata, validation state, and action buttons.
4. Bottom status or operation strip: current scan/export/patch progress and last completed operation.

The app should start with an empty state focused on "Open ISO...". It should not preload sample content. If the ISO parser is unavailable in a development build, the empty state remains honest: describe the outcome people are working toward and show unavailable actions as disabled.

Suggested sidebar groups:

- Library: current ISO summary, all entries, textures, models, text, unsupported.
- Containers: one row per CPK.
- Operations: running operation and recent completed operations, if space allows.

The inspector can be hidden from the toolbar or View menu. When hidden, the table should remain usable and selection should persist.

## Toolbar Model

Toolbar items should be grouped by task:

- Library: Open ISO, Close ISO.
- Export: Extract Selected, Extract Container Textures.
- Patch: Validate Replacement, Create Patched Copy.
- View: Search, filters, preview background, Toggle Inspector.

Keep the default toolbar monochrome. Use system symbols without custom circular borders. Add help text to every icon button and every disabled toolbar action.

## Menu Bar Model

File:

- Open ISO...
- Open Recent
- Close ISO
- Export Selected Texture...
- Export All Textures in Container...
- Reveal Last Export in Finder

Edit:

- Copy Name
- Copy Offset
- Copy Identifier
- Standard copy/paste where replacement workflows later support pasted images or paths.

View:

- Show/Hide Sidebar
- Show/Hide Inspector
- Preview Background: Checkerboard, Black, White
- Zoom In, Zoom Out, Actual Size, Fit
- Show Unsupported Entries
- Show Compressed Entries

Operations:

- Validate Replacement...
- Replace in Patched Copy...
- Verify ISO
- Export Operation Log...

Window:

- Standard macOS window behavior.

Help:

- User Guide
- Supported Formats
- Safety Notes

## Contextual Menu Model

Contextual menus are selection accelerators only. They should not be the only route to a core action.

Entry table contextual menu:

- Extract Selected Texture...
- Validate Replacement...
- Replace in Patched Copy...
- Reveal Last Export in Finder
- Copy Name
- Copy Offset
- Copy Identifier
- Show Original Location

Container sidebar contextual menu:

- Extract All Textures in Container...
- Copy Container Name
- Show Unsupported Entries in Container

Unsupported or compressed entries should still have copy and inspection actions, but patch/export actions should be disabled with help text.

## Button And Action Matrix

| Action | Visible Label | SF Symbol | Menu Location | Shortcut | Enabled When | Confirmation | Progress | Context Menu |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Open ISO | Open ISO... | `opticaldiscdrive` | File | Command-O | No blocking scan operation | No | Scan progress | No |
| Close ISO | Close ISO | `xmark.circle` | File | Command-W when app owns one window, otherwise none | ISO open | Confirm only if operations pending | No | No |
| Extract Selected | Extract Selected Texture... | `square.and.arrow.down` | File | Shift-Command-E | Texture selected and extractable | Overwrite confirmation only | Export progress | Yes |
| Extract Container | Export All Textures in Container... | `tray.and.arrow.down` | File | Option-Command-E | Container selected and has extractable textures | Confirm destination and overwrite policy | Batch progress | Sidebar and table |
| Validate Replacement | Validate Replacement... | `checkmark.shield` | Operations | Command-Option-V | Replaceable texture selected | No | Validation progress if slow | Yes |
| Replace In Patched Copy | Create Patched Copy... | `doc.badge.plus` | Operations | Command-Option-R | Replacement validated | Always confirm summary | Patch progress | Yes |
| Reveal Export | Reveal in Finder | `finder` | File | Command-R only if not conflicting in final key map | Last export or patch exists | No | No | Yes |
| Show Original Location | Show Original Location | `location.viewfinder` | View or contextual | None | Entry selected | No | No | Yes |
| Copy Name | Copy Name | `doc.on.doc` | Edit | Shift-Command-C | Entry selected | No | No | Yes |
| Copy Offset | Copy Offset | no icon after first copy group item | Edit | Option-Command-C | Entry selected | No | No | Yes |
| Copy Identifier | Copy Identifier | no icon after first copy group item | Edit | Control-Command-C | Entry selected | No | No | Yes |
| Toggle Inspector | Show/Hide Inspector | `sidebar.right` | View | Option-Command-I | Always | No | No | No |
| Toggle Preview Background | Preview Background | `checkerboard.rectangle` | View | None | Texture selected | No | No | No |
| Zoom In | Zoom In | `plus.magnifyingglass` | View | Command-Plus | Preview visible | No | No | No |
| Zoom Out | Zoom Out | `minus.magnifyingglass` | View | Command-Minus | Preview visible | No | No | No |
| Fit Preview | Zoom to Fit | `arrow.up.left.and.arrow.down.right` | View | Command-0 | Preview visible | No | No | No |
| Search | Search | `magnifyingglass` | View | Command-F | Entries loaded | No | No | No |
| Show Unsupported | Show Unsupported Entries | `questionmark.square` | View | None | Entries loaded | No | Table refresh | No |
| Show Compressed | Show Compressed Entries | `archivebox` | View | None | Entries loaded | No | Table refresh | No |
| Export Operation Log | Export Operation Log... | `doc.text` | Operations | None | Operation log has entries | Save panel overwrite confirmation | Export progress | No |

## Tooltip And Help Text Matrix

| Control | Help Text |
| --- | --- |
| Open ISO | Choose a PlayStation 2 ISO for a supported Choro-Q Barnhouse Effect game. |
| Close ISO | Close the current ISO and clear the asset browser. |
| Extract Selected | Export the selected texture as a PNG without modifying the ISO. |
| Extract Container | Export every supported texture in the selected CPK container. |
| Validate Replacement | Check whether a PNG can replace the selected texture safely. |
| Create Patched Copy | Write the validated replacement into a new ISO copy. The original ISO is not modified. |
| Reveal in Finder | Show the most recent export or patched ISO in Finder. |
| Toggle Inspector | Show or hide the preview and metadata inspector. |
| Preview Background | Change the transparency background behind texture previews. |
| Show Unsupported Entries | Include entries whose format is not fully understood. |
| Show Compressed Entries | Include compressed entries that are not currently editable. |
| Copy Offset | Copy the selected entry's hexadecimal offset. |
| Copy Identifier | Copy the stable entry identifier used by operation logs. |

Disabled help should explain the condition, not the implementation. Example: "Select a supported APT texture to export it as PNG."

## Data Display Model

Entry table columns:

- Name
- Type
- Container
- Format
- Dimensions
- Palette
- Support
- Compression
- Size
- Sector
- Offset
- Identifier, hidden by default or shown in inspector

Support state must use icon plus text:

- Supported: `checkmark.circle`, "Supported"
- Read-only: `eye`, "Read-only"
- Compressed: `archivebox`, "Compressed"
- Risky: `exclamationmark.triangle`, "Needs Review"
- Unknown: `questionmark.circle`, "Unknown"

Do not communicate support by color alone. Risk rows can use symbols and secondary explanatory text in the inspector rather than row tinting.

## Preview And Media Model

Texture preview:

- Actual decoded PNG preview when available.
- Checkerboard background by default for alpha.
- Background switcher: Checkerboard, Black, White.
- Fit, Actual Size, Zoom In, Zoom Out.
- Dimensions and palette remain visible near the preview.
- Missing preview uses a polished empty preview surface: "Preview unavailable" plus a reason.

Image sources:

- Decoded APT textures generated by Python.
- User-selected replacement PNGs during validation.
- Bundled app icon assets for Finder/application identity only.
- No fake or hardcoded game art in the asset browser.

The provided Choro-Q images can inform mood and icon work, but the app should not hardcode them into the main browser unless they become licensed/bundled resources with a clear purpose.

## Error Model

Every operation error should be structured:

- Short title.
- Plain-language explanation.
- Suggested fix.
- Technical details disclosure.
- Related ISO, container, or entry identifier when applicable.
- Safe-to-retry flag.
- Original-ISO-modified flag.
- Patched-copy-written flag.

Examples:

```json
{
  "title": "Replacement PNG Is Too Large",
  "explanation": "The converted texture data is larger than the selected APT slot.",
  "suggestion": "Use the original dimensions, palette size, and color format, then validate again.",
  "technicalDetails": "Converted size 33792 bytes exceeds slot size 32768 bytes.",
  "relatedEntryID": "BODY.CPK:3:cart_0",
  "safeToRetry": true,
  "originalISOModified": false,
  "patchedCopyWritten": false
}
```

Errors should appear as alerts for blocking failures and as operation-log entries for batch failures. The status bar should summarize the latest result in one sentence.

## Progress Model

Long operations need progress:

- Scan ISO: indeterminate until container count is known, then determinate by CPK.
- Generate preview: small inline spinner in inspector.
- Extract selected: determinate if conversion size is known, otherwise one-step progress.
- Extract container: determinate by entry count.
- Validate replacement: quick status, with spinner only if conversion takes noticeable time.
- Create patched copy: determinate by bytes copied plus patch step.
- Export log: one-step progress.

Progress events should be cancelable where the underlying operation is safe to stop.

## Python Integration Model

SwiftUI owns:

- Windows, navigation, menus, toolbars, dialogs, confirmation flows, file import/export panels, progress presentation, selection, filters, preview display, operation log presentation, and accessibility.

Python owns:

- ISO/CPK/APT parsing, texture conversion, validation, extraction, replacement byte generation, and patched-copy writing.

The boundary is a JSON command interface, ideally a Python CLI entrypoint. Swift should consume only structured JSON or NDJSON, never freeform console logs.

Commands:

- `scan-iso`
- `list-containers`
- `list-entries`
- `preview-texture`
- `extract-texture`
- `extract-container-textures`
- `validate-replacement`
- `replace-texture-copy`

Long commands emit NDJSON events:

- `operation-progress`
- `operation-error`
- `operation-complete`

### JSON Contracts

`scan-iso` request:

```json
{
  "command": "scan-iso",
  "isoPath": "/path/to/game.iso"
}
```

`scan-iso` response:

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
  "containers": [
    {
      "id": "BODY.CPK@4246",
      "name": "BODY.CPK",
      "entryCount": 42,
      "textureCount": 18,
      "sector": 4246,
      "support": "supported"
    }
  ]
}
```

`list-entries` response:

```json
{
  "containerID": "BODY.CPK@4246",
  "entries": [
    {
      "id": "BODY.CPK:3:cart_0",
      "containerID": "BODY.CPK@4246",
      "cpkName": "BODY.CPK",
      "name": "cart_0",
      "kind": "texture",
      "format": "8",
      "width": 256,
      "height": 128,
      "paletteSize": 256,
      "sizeBytes": 33808,
      "offsetBytes": 8704016,
      "sector": 4249,
      "support": "supported",
      "canExtract": true,
      "canReplace": true,
      "compression": "none"
    }
  ]
}
```

`preview-texture` response:

```json
{
  "entryID": "BODY.CPK:3:cart_0",
  "pngPath": "/tmp/choroq-preview/cart_0.png",
  "width": 256,
  "height": 128,
  "hasAlpha": true
}
```

`extract-texture` request:

```json
{
  "command": "extract-texture",
  "isoPath": "/path/to/game.iso",
  "entryID": "BODY.CPK:3:cart_0",
  "destinationFolder": "/Users/example/Exports"
}
```

`extract-container-textures` request:

```json
{
  "command": "extract-container-textures",
  "isoPath": "/path/to/game.iso",
  "containerID": "BODY.CPK@4246",
  "destinationFolder": "/Users/example/Exports",
  "overwrite": "ask"
}
```

`validate-replacement` response:

```json
{
  "entryID": "BODY.CPK:3:cart_0",
  "replacementPath": "/Users/example/cart_0.png",
  "isValid": true,
  "checks": [
    { "id": "dimensions", "label": "Dimensions", "status": "passed", "expected": "256x128", "actual": "256x128" },
    { "id": "format", "label": "Color Format", "status": "passed", "expected": "8 bpp", "actual": "8 bpp" },
    { "id": "palette", "label": "Palette", "status": "passed", "expected": "256 colors", "actual": "248 colors" },
    { "id": "size", "label": "Converted Size", "status": "passed", "expected": "<= 33808 bytes", "actual": "33792 bytes" }
  ],
  "warnings": []
}
```

`replace-texture-copy` request:

```json
{
  "command": "replace-texture-copy",
  "isoPath": "/path/to/original.iso",
  "entryID": "BODY.CPK:3:cart_0",
  "replacementPath": "/Users/example/cart_0.png",
  "outputISOPath": "/Users/example/CHOROQ_HG4_patched.iso",
  "validationToken": "validation-result-id"
}
```

`operation-progress` event:

```json
{
  "event": "operation-progress",
  "operationID": "op-2026-04-19T05-10-00Z",
  "phase": "copying-iso",
  "label": "Creating patched copy",
  "completedUnitCount": 451584000,
  "totalUnitCount": 2147483648
}
```

`operation-error` event:

```json
{
  "event": "operation-error",
  "operationID": "op-2026-04-19T05-10-00Z",
  "error": {
    "title": "CPK Entry Is Compressed",
    "explanation": "This entry uses LZS compression and cannot be replaced safely yet.",
    "suggestion": "Choose an uncompressed APT texture, or export this entry for analysis.",
    "technicalDetails": "Subfile type LZS at BODY.CPK index 22.",
    "relatedEntryID": "BODY.CPK:22:LZS",
    "safeToRetry": false,
    "originalISOModified": false,
    "patchedCopyWritten": false
  }
}
```

## Liquid Glass And Visual Theme Rules

Use Liquid Glass tastefully and only in the navigation/control layer.

- Use system toolbar/sidebar behavior and Regular Liquid Glass where the OS provides it.
- Do not apply glass to `Table` rows, metadata grids, preview surfaces, or content cards.
- Do not stack glass on glass.
- Do not use Clear Liquid Glass for this app's normal utility surfaces.
- Keep tint restrained. A Choro-Q-inspired accent can appear in the app tint, selected controls, and status symbols, not as a full-window color wash.
- Use semantic colors and materials. Any custom accent must live in an asset catalog with Light, Dark, and High Contrast variants.
- The app can carry subtle Choro-Q charm through the app icon, operation names, empty-state warmth, and the content itself, not through toy-like chrome.

## Asset Strategy

- App icon: `defaulticon.png` is the canonical app icon source. Preserve its blue Choro-Q car identity and use it for the app-icon asset pipeline, not as an inline browser decoration.
- Game clip art: treat as reference material unless there is a deliberate, licensed bundled-resource decision.
- Main content imagery: extracted textures and user-selected replacement PNGs.
- Custom colors: define in an asset catalog. Proposed names: `ChoroAccent`, `TextureCheckerLight`, `TextureCheckerDark`, each with appearance variants.
- Custom symbols: use SF Symbols first. Create custom vector symbols only for game-specific concepts SF Symbols cannot express.
- Avoid hardcoding fake preview art, fake thumbnails, or branded sample entries.

## Accessibility Checklist

- Support Light Mode and Dark Mode.
- Verify Increased Contrast and Reduce Transparency.
- Respect Reduce Motion; avoid required animations.
- Use semantic text styles and avoid fixed font sizes.
- Provide VoiceOver labels for icon-only toolbar buttons.
- Pair every status color with a symbol and text.
- Keep disabled actions visible where discoverability matters, with help tags explaining prerequisites.
- Support keyboard navigation through sidebar, table, inspector, and menus.
- Ensure table row selection and context menus have keyboard equivalents.
- Avoid tiny caption-only critical information.
- Make preview zoom controls reachable from View menu and keyboard.
- Preserve text selection for offsets, identifiers, and technical details.

## Current Scaffold Review

Remove or replace:

- Visible "Sample" toolbar item and "Load Sample Session" menu command.
- Automatic sample loading on launch.
- Any UI text containing "mock", "sample", "backend", "bridge", "wired later", or similar implementation language.
- Fake gradient texture preview.
- Status text that explains development state instead of user outcome.
- Replacement language that implies direct in-place mutation.

Rename:

- "Replace" to "Create Patched Copy..." after validation.
- "Validate and Replace" to separate "Validate Replacement..." and "Create Patched Copy...".
- "All Entries" remains acceptable, but sidebar can add "All Assets" if the data model starts including non-entry library views.
- "Inspector" is acceptable as a pane title, but the empty state should say "Select an Entry" or "Open ISO" depending on context.

Hide or disable:

- Export and patch actions until an ISO is open and a supported texture is selected.
- Container export until a container with extractable textures is selected.
- Preview zoom until a decoded preview exists.
- Reveal in Finder until an export or patched copy exists.

Rebuild soon:

- The table should gain search, filters, and persisted sort order.
- The inspector should display real preview PNG output, validation checks, and operation history.
- The Python process client should decode structured JSON and NDJSON progress.
- Operation log should become a first-class model rather than a status string.

## Implementation Phases

Phase 1: Product cleanup and native command shell.

- Remove sample/demo loading from the running app.
- Add empty Open ISO state.
- Add File, Edit, View, Operations, and Help command coverage.
- Add toolbar help tags and safer action labels.
- Keep disabled actions honest and outcome-focused.

Phase 2: Python JSON bridge.

- Add `bhe-json` entrypoint.
- Implement `scan-iso`, `list-containers`, `list-entries`, and `preview-texture`.
- Convert parser failures into structured errors.
- Emit NDJSON progress for scans and batch exports.

Phase 3: Export and preview.

- Generate real preview PNGs.
- Add preview background and zoom controls.
- Add selected-texture export and container batch export.
- Reveal exports in Finder.

Phase 4: Safe patching.

- Implement replacement validation.
- Add validation result UI.
- Add patched-copy write flow with confirmation.
- Record operation log entries.

Phase 5: Power workflows.

- Persistent recent ISOs.
- Saved export destinations.
- Advanced filters and sort presets.
- Unsupported/compressed diagnostics.
- Optional model/text browsing surfaces as the parser matures.
