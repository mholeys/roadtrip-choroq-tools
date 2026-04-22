# Fresh Codex Handoff Prompt

You are taking over Q's Factory in `/Users/monty/Documents/GitHub/roadtrip-choroq-tools`.

The user wants the native SwiftUI macOS app, not the old blank Xcode template. Work inside `Q's Factory/Q's Factory.xcodeproj` and keep the real source files in `Sources/ChoroQBHEApp` wired into that Xcode target.

## Current State

- The Xcode project now builds the real app UI.
- `Q's Factory/Q's Factory/Q_s_FactoryApp.swift` is the active Xcode app entry point.
- The target references these existing Swift folders:
  - `Sources/ChoroQBHEApp/Models`
  - `Sources/ChoroQBHEApp/Services`
  - `Sources/ChoroQBHEApp/Stores`
  - `Sources/ChoroQBHEApp/Views`
- The blank template `ContentView.swift` in the Xcode app folder was deleted to avoid conflicting with the real `ContentView`.
- `script/build_and_run.sh` builds/runs the Xcode scheme using `/tmp/qfactory-derived`.
- The SwiftPM target still builds, but the Xcode project is the user's visible app path.

## What Was Implemented

- `choroq/bhe/bhe_json.py` now uses a versioned JSON envelope:
  - `protocolVersion`
  - `backendVersion`
  - `status`
  - `data` or `error`
- Added backend commands:
  - `version`
  - `health-check`
  - `list-supported-types`
  - `scan-iso`
  - `scan-disc-root`
  - `preview-texture`
  - `preview-texture-disc-root`
  - `extract-texture`
  - `extract-texture-disc-root`
- Swift now rejects newer backend protocol versions.
- Swift can export supported APT textures through `NSSavePanel`.
- Swift tracks whether the source is an ISO or mounted disc root and routes preview/export calls accordingly.
- Xcode app can resolve `choroq/bhe/bhe_json.py` from the source checkout via `#filePath`, so the previous "Expected choroq/bhe/bhe_json.py" error should be fixed for development builds.
- Xcode actor-isolation warnings were fixed by changing the app target's `SWIFT_DEFAULT_ACTOR_ISOLATION` to `nonisolated`; `BHEWorkspaceStore` remains explicitly `@MainActor`.
- BHE mounted folders can be scanned if they contain `SYSTEM.CNF` and `DATA/*.CPK`.
- `/Volumes/ROAD_TRIP_ADVENTURE` is recognized as Road Trip / Choro-Q HG2, but the app returns a structured "HG2/HG3 Backend Not Wired Yet" error because the current bridge only maps BHE CPK/APT content.

## Verification Commands That Passed

```sh
python3 -m py_compile choroq/bhe/bhe_json.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest python_tests/test_bhe_json.py
swift build --product ChoroQBHEApp
./script/build_and_run.sh --verify
```

Manual backend check:

```sh
python3 choroq/bhe/bhe_json.py scan-disc-root /Volumes/ROAD_TRIP_ADVENTURE
```

This currently returns a structured HG2/HG3-not-wired error, not a malformed-folder error.

## Important Docs

Read these before changing architecture:

- `BACKEND_CONTRACT.md`
- `docs/QS_FACTORY_STATUS_AND_ROADMAP.md`
- `docs/MAC_APP_INTERACTION_DESIGN.md`
- `docs/SWIFTIFICATION.md`

## Current Known Issues

- Road Trip / HG2 / HG3 source scanning is not implemented in Swift backend yet.
- Python runtime/dependencies are still not bundled in the app.
- `health-check` exists but no Swift diagnostics/settings UI calls it yet.
- `bchunk` is not bundled or invoked; BIN/CUE handling is still guidance-only.
- App sandbox/signing/packaging strategy is documented but not fully implemented.
- The current BHE bridge may still require Python modules not in the original short list, including `lzsslib`.
- Real game assets such as `roadtrip01.iso` and mounted volumes must stay local fixtures, not public repo test fixtures.

## Next Best Task

Implement the e-Game / Road Trip / HG2 mounted disc scanner.

Suggested approach:

1. Add a new Python bridge command, likely `scan-egame-disc-root <folder-path>`.
2. Reuse logic from `choroq/egame/moddingui/main.py`, especially the game ID map and path patterns around lines ~209-300.
3. Map HG2/HG3 folders/files into the same Swift `BHEEntry`/container model initially, even if names stay generic:
   - `CAR*`
   - `CARS`
   - `COURSE`
   - `ACTION`
   - `FLD`
   - `SHOP`
4. Mark supported model/texture extraction honestly:
   - if preview is not implemented, set `support` to `read-only` or `unknown`
   - do not claim write support
5. Add Swift routing for `BHESourceKind` if a separate source kind is needed, e.g. `.egameDiscRoot`.
6. Keep `BACKEND_CONTRACT.md` updated.
7. Verify against `/Volumes/ROAD_TRIP_ADVENTURE`.

## Do Not Do Yet

- Do not implement direct ISO mutation.
- Do not bundle real game assets.
- Do not smear Python internals into Swift views.
- Do not replace the working SwiftUI source structure just because the Xcode project exists.
- Do not remove the BHE flow while adding HG2/HG3.

## User Pain Points To Address First

1. The visible Xcode app must not be blank.
2. Opening the mounted Road Trip volume should produce useful HG2 scan results, not a dead-end error.
3. Python dependency failures should become a diagnostics view with recovery instructions.
4. BIN/CUE conversion should eventually be a guided native helper flow, with bchunk bundling/license implications handled deliberately.
