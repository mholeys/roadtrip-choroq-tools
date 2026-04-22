# Q's Factory Status And Roadmap

Last updated: 2026-04-20.

## Canonical Project

`Q's Factory/Q's Factory.xcodeproj` is the only active Swift/macOS app project.

The active app source lives inside the Xcode project folder:

- `Q's Factory/Q's Factory/Q_s_FactoryApp.swift`
- `Q's Factory/Q's Factory/Models`
- `Q's Factory/Q's Factory/Services`
- `Q's Factory/Q's Factory/Stores`
- `Q's Factory/Q's Factory/Views`

The old SwiftPM app path has been removed:

- `Package.swift`
- `Sources/ChoroQBHEApp`
- `.swiftpm`
- `.build`
- `script/build_and_run 2.sh`

## Already Implemented

- Native SwiftUI macOS app structure:
  - `NavigationSplitView`
  - sidebar source list
  - searchable `Table`
  - inspector panel
  - toolbar actions
  - menu commands
  - `NSOpenPanel` and `NSSavePanel`
- Central Swift backend protocol and process adapter:
  - `BHEBackendClient`
  - `ProcessBHEBackendClient`
  - typed backend response models
  - structured backend error mapping
- Bundled backend lookup:
  - signed app builds prefer `Contents/Resources/backend/choroq/bhe/bhe_json.py`
  - signed app builds no longer fall back to `../choroq/bhe/bhe_json.py`
- Xcode build phase copies the Python backend into app resources.
- Python bridge:
  - versioned JSON envelope
  - stdout reserved for JSON
  - stderr for diagnostics
  - read-only source access
- Backend commands:
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
- BHE APT texture workflow:
  - scan
  - preview to temporary PNG
  - export to user-selected PNG
- Road Trip / HG2 / HG3 scan workflow:
  - ISO and mounted folder scans return read-only e-Game entries for recognized folders/files
  - model/course/field/shop assets are visible but not extractable yet
- BIN/CUE handling:
  - detects `.bin` and `.cue`
  - presents bchunk conversion guidance
  - does not modify source files
- Backend diagnostics UI:
  - Help > Backend Diagnostics...
  - shows backend version, Python path/version, dependency status, bchunk status, and capability/write-support status

## Partially Implemented

- Python dependencies are checked but not bundled.
- `bchunk` is detected by the Python health check but not invoked by the app.
- Mounted folder scans are implemented, but UX should more clearly guide users toward mounted volumes after conversion.
- Texture export works for individual supported APT textures; batch export is not wired.
- Operation log and Verify ISO commands are visible but not implemented.
- Replacement validation and patched-copy writing are visible as disabled/future workflows only.

## Not Implemented

- Bundled Python runtime.
- Bundled Python package environment.
- Frozen helper executable.
- Bundled `bchunk`.
- Native BIN/CUE conversion sheet.
- Automatic ISO mounting via `hdiutil`.
- Security-scoped bookmarks for persistent file access.
- e-Game model extraction.
- Native 3D preview or Quick Look integration.
- Replacement validation.
- Patched-copy ISO creation.
- Public synthetic ISO fixtures.
- End-to-end UI tests with local real assets.

## Runtime And Dependency Requirements

Current Python modules observed across the project:

- `tkinter`
- `customtkinter`
- `PIL.Image` / Pillow
- `colorama`
- `lzstring`
- `lzsslib`
- `elftools` / pyelftools
- `pycdlib`

The known old failure:

```text
The Python BHE parser dependencies are not available to this Python runtime.
Install the project Python dependencies, then try again.
Details: ModuleNotFoundError: No module named 'pycdlib'
```

Current mitigation:

- `health-check` surfaces dependency availability.
- `Backend Diagnostics...` exposes that in the app.
- The app now runs the bundled bridge script from app resources, avoiding sandbox-denied source-checkout paths.

Remaining packaging gap:

- normal users still need a Python runtime and packages unless a bundled runtime/frozen helper is added.

## Packaging Recommendation

Short term:

- Keep copying the Python backend into `Contents/Resources/backend`.
- Keep `CHOROQ_BHE_PYTHON` for development.
- Add a visible backend diagnostics/settings surface for runtime override.

Distribution target:

- Bundle a self-contained Python runtime or freeze the backend bridge into a signed helper executable.
- Install parser dependencies into that bundled runtime.
- Sign nested helper code and the app with Developer ID for distribution outside the Mac App Store.
- Notarize and staple the final app.
- Keep App Sandbox enabled if possible, but add user-selected read/write entitlements before implementing exports/conversion workflows that write outside app containers.

`bchunk`:

- Safe to invoke technically when run as explicit `Process` arguments.
- Do not shell out with a single command string.
- Legal/distribution review is required before bundling because common `bchunk` packages are GPL-licensed.
- Recommended sequence:
  1. support installed/user-provided `bchunk`
  2. add native guided conversion
  3. consider bundling only after license and distribution obligations are settled

## UX Recommendation

Primary app flow should be:

1. User opens or drops ISO, mounted folder, BIN, or CUE.
2. ISO scans directly.
3. Mounted folders scan as disc roots.
4. BIN/CUE opens a conversion helper sheet.
5. Inspector shows preview and metadata for selected entries.
6. Extractable entries use native save/export panels.
7. Read-only/unsupported/compressed entries remain visible with clear disabled actions and recovery text.

The app should continue using:

- native sidebar/table/inspector layout
- standard toolbar and menu commands
- clear empty states
- structured error dialogs
- source safety language that distinguishes read-only scan, PNG export, and future write workflows

## Verification

Passed in this pass:

```sh
xcodebuild -project "Q's Factory/Q's Factory.xcodeproj" -scheme "Q's Factory" -configuration Debug -derivedDataPath /tmp/qfactory-xcode-canonical-clean build
./script/build_and_run.sh --verify
python3 "/tmp/qfactory-xcode-canonical-clean/Build/Products/Debug/Q's Factory.app/Contents/Resources/backend/choroq/bhe/bhe_json.py" version
python3 "/tmp/qfactory-xcode-canonical-clean/Build/Products/Debug/Q's Factory.app/Contents/Resources/backend/choroq/bhe/bhe_json.py" health-check
```

The backend `version` and `health-check` commands returned valid protocol-versioned JSON from the built app bundle.

Note: macOS continues to attach `com.apple.provenance` extended attributes to copied backend files even after `xattr -cr`. Codesigning still succeeded. Treat this as a packaging validation item, not a current build blocker.

## Roadmap

1. Add drag/drop source import and better mounted-volume empty states.
2. Add native BIN/CUE conversion sheet with `bchunk` discovery.
3. Add `hdiutil attach` helper flow and post-mount source selection.
4. Bundle/freeze the Python backend runtime.
5. Add security-scoped bookmarks for reopened user sources and export folders.
6. Add batch texture extraction.
7. Add e-Game model extraction.
8. Add Quick Look or SceneKit model preview.
9. Add fixture-based backend contract tests.
10. Add UI tests for source import, diagnostics, preview, and extraction.
