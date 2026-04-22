# Q's Factory SwiftUI Status And Roadmap

Last updated: 2026-04-19.

## Current State Audit

### Already Implemented

- Functional SwiftUI app code exists under `Sources/ChoroQBHEApp`.
- The `Q's Factory.xcodeproj` app target now references the real Swift source folders:
  - `Sources/ChoroQBHEApp/Models`
  - `Sources/ChoroQBHEApp/Services`
  - `Sources/ChoroQBHEApp/Stores`
  - `Sources/ChoroQBHEApp/Views`
- `Q's Factory/Q's Factory/Q_s_FactoryApp.swift` now launches the real asset-browser UI instead of the blank SwiftData template.
- Main UI uses native macOS patterns:
  - `NavigationSplitView`
  - sidebar source list
  - searchable `Table`
  - inspector pane
  - toolbar actions
  - menu commands
  - native open/save panels
- Python process launching is centralized in `ProcessBHEBackendClient`.
- Backend entrypoint is centralized in `choroq/bhe/bhe_json.py`.
- The Python bridge now returns a versioned JSON envelope for success and error responses.
- Supported BHE ISO scanning is read-only.
- Supported APT textures can be scanned, previewed, and exported as PNG.
- Preview PNGs are written to a temporary app preview directory.
- Texture exports use an `NSSavePanel` and call the backend `extract-texture` command.
- Structured errors report whether the original ISO or patched copy was modified; both are currently false.
- The source picker accepts ISO, BIN, CUE, and folders:
  - ISO opens the scan flow.
  - BIN/CUE shows conversion guidance.
  - folders scan mounted BHE or Road Trip / HG2 / HG3 disc roots.

### Partially Implemented

- The app has an interaction design document, but not all described interactions are implemented.
- The UI exposes disabled patch/validation actions to establish the workflow, but the backend has no write path.
- BIN/CUE handling is guidance-only. The app does not bundle or invoke `bchunk` yet.
- Mounted folder / mounted volume scanning now exists for BHE-style disc roots containing `SYSTEM.CNF` and `DATA/*.CPK`.
- Road Trip / HG2 / HG3 ISOs and mounted volumes now produce read-only scan results for known e-Game folders and `*.BIN` files. The app does not yet preview or extract those model/course assets.
- `health-check` reports Python dependency and `bchunk` availability, but the Swift UI does not yet surface that as a diagnostics panel.
- The SwiftPM product still builds, but the project direction should now use the Xcode scheme as the primary app path.

### Not Yet Implemented

- Bundled Python runtime.
- Bundled Python packages.
- Bundled `bchunk`.
- e-Game / Road Trip / HG2 / HG3 preview and extraction operations.
- Batch texture extraction.
- Model extraction from the native app.
- In-app 3D model preview.
- Quick Look integration for extracted OBJ files.
- Replacement validation.
- Patched-copy ISO writing.
- Operation log persistence/export.
- Backend fixture tests using legal synthetic ISO data.
- End-to-end UI tests with local real assets.

## Python And Swift Boundary

Swift should only call the Python bridge documented in `BACKEND_CONTRACT.md`. It should not import or depend on Python module internals, parser classes, file offsets calculated outside the backend contract, or Python GUI behavior.

Current Swift boundary:

- `BHEBackendClient` protocol
- `ProcessBHEBackendClient`
- typed Swift models in `BHEModels.swift`
- structured `BHEBackendError` mapping

Current Python boundary:

- `choroq/bhe/bhe_json.py`
- versioned response envelope
- commands:
  - `version`
  - `health-check`
  - `list-supported-types`
- `scan-iso`
- `scan-disc-root`
- `scan-egame-disc-root`
- `preview-texture`
- `preview-texture-disc-root`
- `extract-texture`
- `extract-texture-disc-root`

## Extraction Flow

Current extraction is read-only with respect to the ISO:

1. User opens an ISO.
2. Backend scans `DATA/*.CPK` records.
3. A supported APT texture entry is selected.
4. User chooses `Extract Selected Texture...`.
5. Swift presents `NSSavePanel`.
6. Swift calls `extract-texture <iso> <entry-id> --output <png>`.
7. Python decodes the APT texture and writes the PNG.
8. Swift stores `lastOutputURL` for Reveal in Finder.

There is no ISO mutation and no patched-copy writing in the current implementation.

## Preview Flow

Texture preview is generated lazily when a supported texture is selected:

1. Inspector sees a selected texture.
2. Swift creates a temporary preview output URL.
3. Swift calls `preview-texture`.
4. Python writes a PNG preview.
5. Swift loads the PNG through `NSImage` and displays it over a checkerboard, black, or white background.

Unsupported, risky, compressed, model, text, and unknown entries show explanatory empty states.

## Dependency And Runtime Requirements

The current bridge can run with a configured Python executable through `CHOROQ_BHE_PYTHON`. Without a configured runtime, it falls back to `/usr/bin/env python3`.

Known Python modules involved across the project:

- `tkinter`
- `customtkinter`
- `PIL.Image` / Pillow
- `colorama`
- `lzstring`
- `elftools` / pyelftools
- `pycdlib`

The known real-world failure is preserved as a structured error:

```text
The Python BHE parser dependencies are not available to this Python runtime.
Install the project Python dependencies, then try again.
Details: ModuleNotFoundError: No module named 'pycdlib'
```

This should become a first-class app diagnostics/recovery surface, not a raw error dialog. The health check now also reports `lzsslib`, because the current parser imports can require it.

## BIN/CUE And bchunk Workflow

The app currently recognizes BIN and CUE selections and displays guidance rather than trying to scan them directly.

Established manual workflow:

```sh
bchunk "<image.bin>" "<image.cue>" "<basename>"
hdiutil attach "<basename>01.iso"
```

Example:

```sh
bchunk "Road Trip Adventure (Europe, Australia) (En,Fr,De).bin" "Road Trip Adventure (Europe, Australia) (En,Fr,De).cue" roadtrip
hdiutil attach roadtrip01.iso
```

For this app, the next backend decision is important:

- If the parser continues to use `pycdlib`, the app should open the converted ISO file.
- If the backend adds `scan-disc-root`, the preferred user flow should become selecting the mounted volume or extracted disc root.

## Packaging Analysis

### Python Runtime

Bundling Python is feasible and should be the default for normal users. The app should not depend on the user's shell Python for distribution.

Recommended runtime priority:

1. bundled runtime inside the app bundle
2. user-selected external backend/runtime path for advanced users
3. `CHOROQ_BHE_PYTHON` for development

Recommended packaging direction:

- Build a self-contained backend under `Contents/Resources/backend`.
- Include a pinned Python runtime or a PyInstaller-style backend executable.
- Include wheel-installed dependencies in the bundled environment.
- Keep `bhe_json.py` as the contract entrypoint even if the underlying runtime is frozen.
- Add a Settings diagnostics pane showing backend version, Python path, dependency status, and bchunk status.

### Python Dependencies

The dependencies can be bundled, but GUI-only Python dependencies should be separated from backend dependencies. The native app should not ship `customtkinter` for the Swift UI path unless an upstream parser import still requires it.

Short-term target:

- make `scan-iso`, `preview-texture`, and `extract-texture` require only parser/runtime dependencies
- remove bridge imports that pull in Tk/CustomTkinter paths unnecessarily
- then bundle the smaller backend environment

### bchunk

`bchunk` can be invoked safely as a helper only after the app treats it as untrusted-input processing:

- invoke with explicit arguments, not a shell string
- write to a user-selected destination
- validate output paths
- show progress and errors
- keep original BIN/CUE files unchanged

Bundling needs license review. Package sources identify bchunk as GPL-2.0-or-later / GPL-2+, which is a real distribution constraint for a closed-source app. Prefer these options in order:

1. guide users to install `bchunk` externally during early development
2. support user-provided helper path
3. if bundling, ship source/license notices and make the app's distribution model compatible with GPL obligations

Sources checked: [SUSE Package Hub bchunk](https://packagehub.suse.com/packages/bchunk/) and [MacPorts bchunk](https://ports.macports.org/port/bchunk/summary/).

### Signing, Notarization, And Sandbox

For distribution outside the Mac App Store, the app should be Developer ID signed, hardened-runtime enabled, notarized, and stapled. Apple documents notarization as the path for Developer ID-distributed macOS software, and hardened runtime affects hosted plug-ins and extra binaries. Source: [Apple notarization documentation](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).

The current Xcode target has App Sandbox enabled with user-selected read-only files. Apple documents that sandboxed apps get broader file access through user-selected files in `NSOpenPanel`/`NSSavePanel`. Source: [Apple App Sandbox configuration](https://developer.apple.com/documentation/xcode/configuring-the-macos-app-sandbox).

Packaging implications:

- A bundled Python runtime and any helper binaries must be signed inside the app bundle.
- If the app writes exports or converted ISO files, it needs user-selected read/write access for those destinations.
- Persistent access to source folders or mounted volumes will need security-scoped bookmarks.
- If `bchunk` is bundled, sign it and test it under the hardened runtime and sandbox.
- If the backend executes external user-selected binaries, treat that as an advanced/debug mode, not the default distribution path.

## UX Analysis

The app should remain a native Mac workbench, not a script launcher.

Recommended primary structure:

- Sidebar:
  - current source summary
  - all entries
  - CPK containers
  - future saved/recent sources
- Detail:
  - searchable/sortable asset table
  - format, dimensions, support, compression, size, sector, offset
- Inspector:
  - preview
  - metadata
  - source safety
  - contextual actions
- Status/progress strip:
  - scan/export/validation state
  - structured error summary

Recommended source import flow:

- drop or open ISO: scan directly; BHE ISOs list CPK/APT assets and Road Trip / HG2 / HG3 ISOs list read-only e-Game parts
- drop or open BIN/CUE: show bchunk conversion helper, then open generated ISO or mounted volume depending on backend support
- drop or open BHE folder/volume: scan it through `scan-disc-root`
- drop or open Road Trip / HG2 / HG3 folder/volume: list known e-Game folders and files as read-only parts, then explain that model preview/extraction is the next backend phase

Recommended model preview direction:

- Start with extracted OBJ reveal and Quick Look.
- Then evaluate `QuickLookPreview`/Quick Look panel for in-app preview.
- Use SceneKit or Model I/O only if the app needs custom 3D inspection controls.

## Development Work Completed In This Pass

- Wired the real SwiftUI source folders into `Q's Factory.xcodeproj`.
- Replaced the blank Xcode template entry point with the real Q's Factory app entry.
- Removed the template `ContentView.swift` that conflicted with the real `ContentView`.
- Updated `script/build_and_run.sh` to build and launch the Xcode scheme.
- Added protocol/backend metadata envelopes to `bhe_json.py`.
- Added backend commands:
  - `version`
  - `health-check`
  - `list-supported-types`
  - `extract-texture`
- Updated Swift decoding to require compatible protocol metadata.
- Added native PNG extraction through `NSSavePanel`.
- Added BIN/CUE and mounted-folder guidance in the source picker.
- Added BHE mounted-folder scan/preview/extract commands and Swift routing for disc-root sources.
- Added read-only Road Trip / HG2 / HG3 mounted-folder scans so `/Volumes/ROAD_TRIP_ADVENTURE` can populate the Swift table with known e-Game parts.
- Applied the Q's Factory native Mac theme through terminology, iconography, source-list rows, inspector sections, accent color, and scan-only empty states.
- Fixed Xcode main-actor isolation warnings by changing the app target's default actor isolation back to `nonisolated`; the store remains explicitly `@MainActor`.
- Fixed development bridge lookup so Xcode-launched builds can find `choroq/bhe/bhe_json.py` from the source checkout.
- Added focused Python tests for the new command envelope and commands.
- Removed extended attributes from app resources so Xcode codesigning can succeed when building outside File Provider-derived paths.

## Verification

Passed:

```sh
python3 -m py_compile choroq/bhe/bhe_json.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest python_tests/test_bhe_json.py
swift build --product ChoroQBHEApp
./script/build_and_run.sh --verify
xcodebuild -project "Q's Factory/Q's Factory.xcodeproj" -scheme "Q's Factory" -configuration Debug -derivedDataPath /tmp/qfactory-derived build
```

Note: Xcode builds should use `/tmp/qfactory-derived` or another non-File-Provider-derived build directory. Building products under the repository's `.build/xcode-derived` path hit codesign rejection from resource-fork/Finder metadata on the generated `.app`.

## Recommended Roadmap

### Phase 1: Stabilize Xcode App Path

- Treat `Q's Factory.xcodeproj` as the primary app.
- Decide whether to keep SwiftPM as a secondary dev target or remove it.
- Add the Python backend files as app resources or a bundled backend product.
- Surface `health-check` in a diagnostics/settings view.

### Phase 2: Runtime Friction Removal

- Build a bundled backend runtime.
- Reduce backend imports so Swift workflows do not require Tk/CustomTkinter.
- Add a backend preference/override UI.
- Keep `CHOROQ_BHE_PYTHON` as dev-only override.

### Phase 3: Source Import

- Implement drag/drop for ISO, BIN, CUE, and folders.
- Expand `scan-disc-root` coverage with more fixture-tested mounted-folder variants.
- Add bchunk helper discovery and optional conversion UI.
- Keep bchunk bundling optional until license/distribution obligations are settled.

### Phase 4: Extraction Workflows

- Add batch container texture extraction.
- Add export queue/progress/cancel.
- Add operation log.
- Add overwrite policy and conflict reporting.

### Phase 5: Preview Expansion

- Add Quick Look/reveal flow for extracted OBJ.
- Evaluate embedded Quick Look or SceneKit model preview.
- Add text/model metadata surfaces based on real parser support.

### Phase 6: Safe Write/Patch

- Implement `validate-replacement`.
- Implement patched-copy writing only; keep direct ISO mutation out of the default UX.
- Add preflight confirmation and post-write verification.
- Add fixture tests before enabling write UI.

## Handoff For Next Codex Instance

Start here:

1. Open `Q's Factory/Q's Factory.xcodeproj`; the app target now uses the real Swift files from `Sources/ChoroQBHEApp`.
2. Build with `./script/build_and_run.sh --verify`; it uses `/tmp/qfactory-derived` to avoid codesign xattr failures.
3. Read `BACKEND_CONTRACT.md` before changing Swift/Python communication.
4. Next best implementation task: add a diagnostics/settings view that calls `health-check` and shows Python dependency status, `CHOROQ_BHE_PYTHON`, and bchunk availability.
5. Next backend task: implement e-Game model extraction/preview for known HG2/HG3 car assets, keeping all new operations read-only until write validation exists.
6. Do not implement ISO write support until replacement validation and fixture tests exist.
7. Treat `roadtrip01.iso` and any user-provided BIN/CUE files as local fixtures only. Do not commit real game assets to a public repo.
