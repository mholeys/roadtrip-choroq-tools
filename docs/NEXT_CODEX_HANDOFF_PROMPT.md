# Q's Factory Handoff For Next Codex Instance

## Current Direction

`Q's Factory/Q's Factory.xcodeproj` is the canonical and final macOS app project. Do not work through the old SwiftPM app path. Do not add linked Swift groups that point outside the Xcode project.

The active Swift source tree is:

- `Q's Factory/Q's Factory/Q_s_FactoryApp.swift`
- `Q's Factory/Q's Factory/Models/BHEModels.swift`
- `Q's Factory/Q's Factory/Services/BHEBackendClient.swift`
- `Q's Factory/Q's Factory/Stores/BHEWorkspaceStore.swift`
- `Q's Factory/Q's Factory/Views/*.swift`

The old SwiftPM app was removed:

- `Package.swift` was deleted.
- `Sources/ChoroQBHEApp` was deleted.
- `.swiftpm` and `.build` were removed as old SwiftPM/Xcode package artifacts.
- `script/build_and_run 2.sh` was removed because it built the old SwiftPM app.

## What Was Fixed In This Pass

- Moved the real SwiftUI app code into `Q's Factory/Q's Factory`.
- Removed the Xcode project’s linked `../Sources/ChoroQBHEApp/...` groups.
- Removed the template `Item.swift`; the old template `ContentView.swift` was already deleted.
- Kept the Xcode app target as the only active Swift app target.
- Updated the backend client to prefer the bundled app resource backend:
  - `Contents/Resources/backend/choroq/bhe/bhe_json.py`
  - no signed app fallback to the source checkout path
  - source checkout fallback only remains for non-app development contexts
- Added Swift backend diagnostics models and commands:
  - `version`
  - `health-check`
  - `list-supported-types`
- Added `BackendDiagnosticsView` and a Help menu item: `Backend Diagnostics...`.
- Hardened the Xcode `Copy Python Backend` build phase:
  - copies backend files into the app bundle
  - excludes `__pycache__`, `*.pyc`, and `.DS_Store`
  - declares copied UI helper paths as script inputs
  - attempts to strip removable extended attributes from copied backend files
- Verified the Xcode scheme builds and signs:

```sh
xcodebuild -project "Q's Factory/Q's Factory.xcodeproj" -scheme "Q's Factory" -configuration Debug -derivedDataPath /tmp/qfactory-xcode-canonical-clean build
./script/build_and_run.sh --verify
```

Both succeeded.

## Current Backend State

The Python bridge remains:

- `choroq/bhe/bhe_json.py`

It is copied into:

- `Q's Factory.app/Contents/Resources/backend/choroq/bhe/bhe_json.py`

The bridge uses protocol version `1` and backend version `0.4.0`.

Implemented commands:

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

Current write safety:

- Original ISO modification: not implemented.
- Patched-copy writing: not implemented.
- Replacement validation: not implemented.
- Texture preview/export writes PNGs only to app temp or user-selected output paths.

## Known Runtime Facts

On this machine, running the bundled bridge from the built app resources reports:

- Python: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3`
- `pycdlib`: available
- Pillow, customtkinter, colorama, lzstring, pyelftools: available
- `lzsslib`: unavailable, currently optional in `health-check`
- `bchunk`: available at `/opt/homebrew/bin/bchunk`

The app still does not bundle a Python runtime or wheel environment. It uses the system/developer Python unless `CHOROQ_BHE_PYTHON` is set. Distribution still needs a bundled/frozen backend runtime.

## Important User Concern

The user saw Xcode showing linked groups like `../Sources/ChoroQBHEApp/Views`. That is now fixed in `project.pbxproj`. If Xcode still displays them, close and reopen `Q's Factory/Q's Factory.xcodeproj`; the navigator is stale.

## BIN/CUE And bchunk

Current app behavior:

- ISO: scan directly.
- Folder/mounted volume: scan via `scan-disc-root` or e-Game read-only scan.
- BIN/CUE: guidance only. It does not run `bchunk` yet.

Established command:

```sh
bchunk "<image.bin>" "<image.cue>" "<basename>"
hdiutil attach "<basename>01.iso"
```

Recommended next implementation:

1. Add a native conversion sheet when the user opens `.bin` or `.cue`.
2. Detect the matching pair.
3. Detect bundled/user-provided/Homebrew `bchunk`.
4. Run `bchunk` with `Process` arguments, never a shell command string.
5. Mount the generated `01.iso` with `hdiutil attach`.
6. Prompt the user to open the mounted volume or open the generated ISO.

Do not copy the user’s game BIN/CUE files into the repo.

## Next Highest-Value Work

1. Add a real source import/drop target for ISO, mounted folders, BIN, and CUE in `ContentView`.
2. Add the BIN/CUE conversion sheet and helper-process client.
3. Add Settings or Diagnostics UI for choosing an external Python/backend path during development.
4. Package a self-contained Python backend runtime or freeze the bridge as a helper executable.
5. Add security-scoped bookmarks for reopened sources.
6. Add batch texture export for BHE containers.
7. Add e-Game/Road Trip model extraction and then Quick Look or SceneKit preview for exported OBJ/USDZ.
8. Add fixture strategy:
   - public tests use synthetic/legal fixtures
   - local manual tests can use the user’s real ISO/BIN/CUE files, but those assets should not be committed.

## Build Command

Use only:

```sh
./script/build_and_run.sh --verify
```

or:

```sh
xcodebuild -project "Q's Factory/Q's Factory.xcodeproj" -scheme "Q's Factory" -configuration Debug -derivedDataPath /tmp/qfactory-derived build
```

Do not use `swift build`.
