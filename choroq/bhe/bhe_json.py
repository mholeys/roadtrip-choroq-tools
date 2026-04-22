from __future__ import annotations

import contextlib
import json
import re
import shutil
import sys
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any


PROTOCOL_VERSION = 1
BACKEND_VERSION = "0.4.0"
SECTOR_SIZE = 2048
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class BHEJSONError(Exception):
    def __init__(
        self,
        title: str,
        explanation: str,
        suggestion: str | None = None,
        technical_details: str | None = None,
        related_entry_id: str | None = None,
        safe_to_retry: bool = True,
    ):
        super().__init__(technical_details or explanation)
        self.title = title
        self.explanation = explanation
        self.suggestion = suggestion
        self.technical_details = technical_details
        self.related_entry_id = related_entry_id
        self.safe_to_retry = safe_to_retry

    def to_json(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "explanation": self.explanation,
            "suggestion": self.suggestion,
            "technicalDetails": self.technical_details,
            "relatedEntryID": self.related_entry_id,
            "safeToRetry": self.safe_to_retry,
            "originalISOModified": False,
            "patchedCopyWritten": False,
        }


@dataclass(frozen=True)
class GameInfo:
    title: str
    variant: str


@dataclass(frozen=True)
class PS2BootInfo:
    elf_name: str

    def valid(self) -> bool:
        return bool(self.elf_name)


GAME_VERSIONS: dict[str, GameInfo] = {
    "SLPS_019.04": GameInfo("Combat Choro-Q", "JP"),
    "SLES_516.03": GameInfo("Shin Combat Choro-Q", "EUR"),
    "SLPS_250.26": GameInfo("Shin Combat Choro-Q", "JP"),
    "SLKA_250.47": GameInfo("Shin Combat Choro-Q", "KOR"),
    "SLUS_206.06": GameInfo("Shin Combat Choro-Q", "US"),
    "SLES_502.52": GameInfo("Choro-Q HG1", "EUR"),
    "SLUS_202.25": GameInfo("Choro-Q HG1", "US"),
    "SLPS_250.15": GameInfo("Choro-Q HG1", "JP"),
    "SLES_531.40": GameInfo("Choro-Q HG4", "EUR"),
    "SLUS_209.30": GameInfo("Choro-Q HG4", "US"),
    "SLPM_653.26": GameInfo("Choro-Q HG4", "JP"),
    "SLPM_657.24": GameInfo("Choro Q Works", "JP"),
}

EGAME_VERSIONS: dict[str, GameInfo] = {
    "SLES_513.56": GameInfo("Road Trip Adventure / Choro-Q HG2", "EUR"),
    "SLPM_621.04": GameInfo("Choro-Q HG2", "JP"),
    "SLKA_150.08": GameInfo("Choro-Q HG2", "KOR"),
    "SLUS_203.98": GameInfo("Everywhere Road Trip / Choro-Q HG2", "US"),
    "SLPM 62355": GameInfo("Choro-Q HG2", "JP"),
    "SLPM 62761": GameInfo("Choro-Q HG2", "JP"),
    "SLES_519.11": GameInfo("Choro-Q HG3", "EUR"),
    "SLPM_622.44": GameInfo("Choro-Q HG3", "JP"),
    "SLPM_625.95": GameInfo("Choro-Q HG3", "JP"),
    "SLPM_627.71": GameInfo("Choro-Q HG3", "JP"),
}


CPK_PATH_RE = re.compile(r"^/DATA/[A-Z_0-9]{1,10}\.CPK(?:;[0-9]+)?$")
EGAME_HG2_BOOT_IDS = {
    "SLES_513.56",
    "SLPM_621.04",
    "SLKA_150.08",
    "SLUS_203.98",
    "SLPM 62355",
    "SLPM 62761",
}
EGAME_HG3_BOOT_IDS = {
    "SLES_519.11",
    "SLPM_622.44",
    "SLPM_625.95",
    "SLPM_627.71",
}
EGAME_HG2_REQUIRED_FOLDERS = {
    "CAR0",
    "CAR1",
    "CAR2",
    "CAR3",
    "CAR4",
    "CARS",
    "ACTION",
    "COURSE",
    "FLD",
    "ITEM",
    "SHOP",
    "SOUND",
    "SYS",
}
EGAME_HG3_REQUIRED_FOLDERS = {"CARS", "COURSE", "ITEM", "SOUND", "SYS"}
EGAME_SCAN_FOLDERS = {"CAR0", "CAR1", "CAR2", "CAR3", "CAR4", "CARS", "COURSE", "ACTION", "FLD", "SHOP"}
HG2_COURSE_NAMES_EUR = {
    "C00": "Peach Raceway",
    "C01": "Peach Raceway II",
    "C02": "Temple Raceway",
    "C03": "Ninja Temple Raceway",
    "C04": "Desert Raceway",
    "C05": "Night Glow Raceway",
    "C06": "Snow Mountain Raceway",
    "C07": "Miner 49er Raceway",
    "C08": "Slick Track",
    "C09": "Oval Raceway",
    "C10": "River Raceway",
    "C11": "Snow Mountain Raceway",
    "C12": "Lava Run Raceway",
    "C13": "Sunny Beach Raceway",
    "C14": "Lagoon Raceway",
    "C18": "Tin Raceway (Day)",
    "C19": "Tin Raceway (Night)",
    "C20": "Endurance Run",
    "A00": "Treasure Hunting Maze",
    "A01": "Sliding Door Race",
    "A02": "Highway Race",
    "A03": "Rock Climbing",
    "A04": "Drag Race",
    "A05": "Golf",
    "A06": "Roulette",
    "A07": "Figure 8",
    "A08": "Football",
    "A09": "Rainbow Jump",
    "A10": "Tunnel Race",
    "A11": "Obstacle Course",
    "A12": "Which-way? Race",
    "A13": "Volcano Course",
    "A14": "Curling",
    "A15": "Barrel Dodging",
    "A16": "Cloud Hill",
    "A17": "Ski Jumping",
    "A18": "Fishing",
    "A19": "Beach Flag",
    "A20": "Single Lap Race",
}


def main(argv: list[str]) -> int:
    try:
        if not argv:
            raise BHEJSONError(
                "Command Required",
                "Choose a BHE JSON command to run.",
                "Use version, health-check, list-supported-types, scan-iso, preview-texture, or extract-texture.",
                "No command argument was supplied.",
            )

        command = argv[0]
        if command == "version":
            if len(argv) != 1:
                raise BHEJSONError(
                    "Version Arguments Invalid",
                    "The version command does not accept arguments.",
                    "Run version without extra arguments.",
                    "Usage: version",
                )
            result = backend_version()
        elif command == "health-check":
            if len(argv) != 1:
                raise BHEJSONError(
                    "Health Check Arguments Invalid",
                    "The health-check command does not accept arguments.",
                    "Run health-check without extra arguments.",
                    "Usage: health-check",
                )
            result = health_check()
        elif command == "list-supported-types":
            if len(argv) != 1:
                raise BHEJSONError(
                    "Supported Types Arguments Invalid",
                    "The list-supported-types command does not accept arguments.",
                    "Run list-supported-types without extra arguments.",
                    "Usage: list-supported-types",
                )
            result = list_supported_types()
        elif command == "scan-iso":
            if len(argv) != 2:
                raise BHEJSONError(
                    "ISO Path Required",
                    "The scan command needs one ISO path.",
                    "Run scan-iso with a PlayStation 2 ISO path.",
                    "Usage: scan-iso <iso-path>",
                )
            result = scan_iso(Path(argv[1]))
        elif command == "scan-disc-root":
            if len(argv) != 2:
                raise BHEJSONError(
                    "Disc Root Path Required",
                    "The mounted disc scan command needs one folder path.",
                    "Run scan-disc-root with a mounted PlayStation 2 disc volume or extracted disc root.",
                    "Usage: scan-disc-root <folder-path>",
                )
            result = scan_disc_root(Path(argv[1]))
        elif command == "scan-egame-disc-root":
            if len(argv) != 2:
                raise BHEJSONError(
                    "e-Game Disc Root Path Required",
                    "The e-Game mounted disc scan command needs one folder path.",
                    "Run scan-egame-disc-root with a mounted Road Trip / HG2 / HG3 disc volume or extracted disc root.",
                    "Usage: scan-egame-disc-root <folder-path>",
                )
            result = scan_egame_disc_root(Path(argv[1]))
        elif command == "preview-texture":
            result = _run_preview_texture(argv[1:])
        elif command == "preview-texture-disc-root":
            result = _run_preview_texture_disc_root(argv[1:])
        elif command == "extract-texture":
            result = _run_extract_texture(argv[1:])
        elif command == "extract-texture-disc-root":
            result = _run_extract_texture_disc_root(argv[1:])
        else:
            raise BHEJSONError(
                "Unknown Command",
                f"'{command}' is not a supported BHE JSON command.",
                "Use version, health-check, list-supported-types, scan-iso, scan-disc-root, preview-texture, or extract-texture.",
                f"Unknown command: {command}",
            )

        print(json.dumps(_ok(result), ensure_ascii=False, separators=(",", ":")))
        return 0
    except BHEJSONError as error:
        print(json.dumps(_error(error), ensure_ascii=False, separators=(",", ":")))
        return 2
    except SystemExit as error:
        json_error = BHEJSONError(
            "Parser Stopped",
            "The BHE parser stopped before the command could finish. Your original ISO was not modified.",
            "Try a different supported ISO or inspect the technical details.",
            f"SystemExit: {error.code}",
            safe_to_retry=False,
        )
        print(json.dumps(_error(json_error), ensure_ascii=False, separators=(",", ":")))
        return 2
    except Exception as error:
        json_error = BHEJSONError(
            "BHE Command Failed",
            "The BHE command could not finish. Your original ISO was not modified.",
            "Check that the selected file is a supported Choro-Q Barnhouse Effect ISO.",
            f"{type(error).__name__}: {error}",
        )
        print(json.dumps(_error(json_error), ensure_ascii=False, separators=(",", ":")))
        return 2


def _ok(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "backendVersion": BACKEND_VERSION,
        "status": "ok",
        "data": data,
    }


def _error(error: BHEJSONError) -> dict[str, Any]:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "backendVersion": BACKEND_VERSION,
        "status": "error",
        "error": error.to_json(),
    }


def _run_preview_texture(argv: list[str]) -> dict[str, Any]:
    if len(argv) != 4 or argv[2] != "--output":
        raise BHEJSONError(
            "Preview Arguments Required",
            "Texture preview generation needs an ISO path, an entry identifier, and an output PNG path.",
            "Run preview-texture with an entry ID from scan-iso and an --output path.",
            "Usage: preview-texture <iso-path> <entry-id> --output <png-path>",
        )
    return preview_texture(Path(argv[0]), argv[1], Path(argv[3]))


def _run_preview_texture_disc_root(argv: list[str]) -> dict[str, Any]:
    if len(argv) != 4 or argv[2] != "--output":
        raise BHEJSONError(
            "Preview Arguments Required",
            "Texture preview generation needs a disc root path, an entry identifier, and an output PNG path.",
            "Run preview-texture-disc-root with an entry ID from scan-disc-root and an --output path.",
            "Usage: preview-texture-disc-root <folder-path> <entry-id> --output <png-path>",
        )
    return preview_texture_disc_root(Path(argv[0]), argv[1], Path(argv[3]))


def _run_extract_texture(argv: list[str]) -> dict[str, Any]:
    if len(argv) != 4 or argv[2] != "--output":
        raise BHEJSONError(
            "Extraction Arguments Required",
            "Texture extraction needs an ISO path, an entry identifier, and an output PNG path.",
            "Run extract-texture with an entry ID from scan-iso and an --output path ending in .png.",
            "Usage: extract-texture <iso-path> <entry-id> --output <png-path>",
        )
    return extract_texture(Path(argv[0]), argv[1], Path(argv[3]))


def _run_extract_texture_disc_root(argv: list[str]) -> dict[str, Any]:
    if len(argv) != 4 or argv[2] != "--output":
        raise BHEJSONError(
            "Extraction Arguments Required",
            "Texture extraction needs a disc root path, an entry identifier, and an output PNG path.",
            "Run extract-texture-disc-root with an entry ID from scan-disc-root and an --output path ending in .png.",
            "Usage: extract-texture-disc-root <folder-path> <entry-id> --output <png-path>",
        )
    return extract_texture_disc_root(Path(argv[0]), argv[1], Path(argv[3]))


def backend_version() -> dict[str, Any]:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "backendVersion": BACKEND_VERSION,
        "readOnly": True,
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
        ],
    }


def health_check() -> dict[str, Any]:
    dependency_specs = [
        ("tkinter", "tkinter", True),
        ("customtkinter", "customtkinter", False),
        ("Pillow", "PIL.Image", False),
        ("colorama", "colorama", False),
        ("lzstring", "lzstring", False),
        ("lzsslib", "lzsslib", False),
        ("pyelftools", "elftools", False),
        ("pycdlib", "pycdlib", False),
    ]
    dependencies = [
        {
            "name": name,
            "module": module,
            "available": _module_available(module),
            "requiredForBHE": required_for_bhe,
        }
        for name, module, required_for_bhe in dependency_specs
    ]
    return {
        "pythonExecutable": sys.executable,
        "pythonVersion": sys.version.split()[0],
        "dependencies": dependencies,
        "bchunk": {
            "available": shutil.which("bchunk") is not None,
            "path": shutil.which("bchunk"),
        },
    }


def list_supported_types() -> dict[str, Any]:
    return {
        "sourceTypes": [
            {
                "extension": "iso",
                "role": "scan",
                "support": "supported",
                "notes": "Read-only scan through pycdlib. The original ISO is not modified.",
            },
            {
                "extension": "bin/cue",
                "role": "conversion-helper",
                "support": "planned-helper",
                "notes": "Use bchunk to convert a BIN/CUE pair to a data-track ISO, then scan the converted ISO.",
            },
            {
                "extension": "folder",
                "role": "mounted-volume",
                "support": "supported",
                "notes": "Read-only scan of mounted volumes or extracted disc roots. Barnhouse Effect roots use SYSTEM.CNF and DATA/*.CPK. Road Trip / HG2 / HG3 roots use the e-Game folder layout.",
            },
        ],
        "entryTypes": [
            {
                "kind": "texture",
                "format": "APT",
                "operations": ["scan", "preview-texture", "extract-texture"],
                "readOnly": True,
                "writable": False,
            },
            {
                "kind": "apt",
                "format": "APT container",
                "operations": ["scan"],
                "readOnly": True,
                "writable": False,
            },
            {
                "kind": "model",
                "format": "PBL/MPD/HPD/MPC/e-Game BIN",
                "operations": ["scan"],
                "readOnly": True,
                "writable": False,
            },
            {
                "kind": "lzs",
                "format": "LZS",
                "operations": ["scan"],
                "readOnly": True,
                "writable": False,
            },
            {
                "kind": "text",
                "format": "TOC/FONT",
                "operations": ["scan"],
                "readOnly": True,
                "writable": False,
            },
        ],
        "writeSupport": {
            "originalISOModification": False,
            "patchedCopyWriting": False,
            "replacementValidation": False,
        },
    }


def scan_iso(iso_path: Path) -> dict[str, Any]:
    _validate_iso_path(iso_path)
    pycdlib = _import_pycdlib()

    iso = pycdlib.PyCdlib()
    try:
        with contextlib.redirect_stdout(sys.stderr):
            iso.open(str(iso_path), "rb")
            cnf = _read_system_cnf_lightweight(iso)
            if cnf.elf_name in EGAME_VERSIONS:
                return _scan_egame_iso_open(iso, iso_path, cnf)

            game_info = _game_info(cnf)
            CPK = _import_cpk_runtime()
            cpk_records = _find_cpk_records(iso)
            containers: list[dict[str, Any]] = []
            entries: list[dict[str, Any]] = []

            for cpk_name, iso_record_path, record in cpk_records:
                container, container_entries = _scan_cpk(iso, CPK, cpk_name, iso_record_path, record)
                containers.append(container)
                entries.extend(container_entries)

        texture_count = sum(1 for entry in entries if entry["kind"] == "texture")
        return {
            "iso": {
                "id": cnf.elf_name,
                "isoName": iso_path.name,
                "gameTitle": game_info.title,
                "variant": game_info.variant,
                "sourceFamily": "bhe",
                "cpkCount": len(containers),
                "textureCount": texture_count,
            },
            "containers": containers,
            "entries": entries,
        }
    finally:
        with contextlib.suppress(Exception):
            iso.close()


def scan_disc_root(root_path: Path) -> dict[str, Any]:
    _validate_disc_root_path(root_path)
    cnf = _read_system_cnf_from_root(root_path)
    if cnf.elf_name in EGAME_VERSIONS:
        return scan_egame_disc_root(root_path)

    game_info = _game_info(cnf)
    _pycdlib, CPK, _PS2Cnf = _import_runtime()

    with contextlib.redirect_stdout(sys.stderr):
        cpk_files = _find_cpk_files(root_path)
        if not cpk_files:
            raise BHEJSONError(
                "BHE CPK Files Not Found",
                "The selected disc root is a recognized Barnhouse Effect game, but DATA/*.CPK files were not found.",
                "Choose the mounted disc volume itself or a complete extracted disc root.",
                f"Path: {root_path}",
                safe_to_retry=True,
            )
        containers: list[dict[str, Any]] = []
        entries: list[dict[str, Any]] = []

        for cpk_name, cpk_path in cpk_files:
            with cpk_path.open("rb") as file:
                cpk_data = BytesIO(file.read())
            container, container_entries = _scan_cpk_data(CPK, cpk_name, 0, 0, cpk_data)
            containers.append(container)
            entries.extend(container_entries)

    texture_count = sum(1 for entry in entries if entry["kind"] == "texture")
    return {
            "iso": {
                "id": cnf.elf_name,
                "isoName": root_path.name,
                "gameTitle": game_info.title,
                "variant": game_info.variant,
                "sourceFamily": "bhe",
                "cpkCount": len(containers),
                "textureCount": texture_count,
            },
        "containers": containers,
        "entries": entries,
    }


def scan_egame_disc_root(root_path: Path) -> dict[str, Any]:
    _validate_disc_root_path(root_path)
    cnf = _read_system_cnf_from_root(root_path)
    game_info = _egame_game_info(cnf)
    _validate_egame_folder_layout(root_path, cnf)

    containers: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []
    for folder_name, folder_path in _egame_scan_folders(root_path):
        folder_entries = [_egame_entry(root_path, folder_name, path, cnf, game_info) for path in _egame_matching_files(root_path, folder_path, cnf)]
        if not folder_entries:
            continue
        container = {
            "id": f"egame:{folder_name}",
            "name": folder_name,
            "entryCount": len(folder_entries),
            "textureCount": 0,
            "sector": -1,
            "support": "read-only",
        }
        containers.append(container)
        entries.extend(folder_entries)

    return {
        "iso": {
            "id": cnf.elf_name,
            "isoName": root_path.name,
            "gameTitle": game_info.title,
            "variant": game_info.variant,
            "sourceFamily": "egame",
            "cpkCount": len(containers),
            "textureCount": 0,
        },
        "containers": containers,
        "entries": entries,
    }


def _scan_egame_iso_open(iso, iso_path: Path, cnf) -> dict[str, Any]:
    game_info = _egame_game_info(cnf)
    facade = iso.get_iso9660_facade()
    folders = {
        _strip_iso_version(dirname).strip("/").upper()
        for dirname, _dirlist, _filelist in iso.walk(iso_path="/")
        if dirname != "/"
    }
    _validate_egame_folder_names(folders, cnf, iso_path)

    records_by_folder: dict[str, list[tuple[str, Any]]] = {folder: [] for folder in EGAME_SCAN_FOLDERS}
    for dirname, _dirlist, filelist in iso.walk(iso_path="/"):
        folder_name = _strip_iso_version(dirname).strip("/").upper()
        if folder_name not in EGAME_SCAN_FOLDERS:
            continue
        for filename in filelist:
            record_path = f"{dirname}/{filename}"
            relative_path = _strip_iso_version(record_path).upper()
            if _egame_entry_metadata(relative_path, cnf) is None:
                continue
            try:
                record = facade.get_record(record_path)
            except Exception:
                record = facade.get_record(relative_path)
            records_by_folder[folder_name].append((relative_path, record))

    containers: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []
    for folder_name in sorted(records_by_folder):
        records = sorted(records_by_folder[folder_name], key=lambda item: (int(item[1].orig_extent_loc), item[0]))
        if not records:
            continue
        containers.append(
            {
                "id": f"egame:{folder_name}",
                "name": folder_name,
                "entryCount": len(records),
                "textureCount": 0,
                "sector": -1,
                "support": "read-only",
            }
        )
        for relative_path, record in records:
            entries.append(_egame_iso_entry(folder_name, relative_path, record, cnf))

    return {
        "iso": {
            "id": cnf.elf_name,
            "isoName": iso_path.name,
            "gameTitle": game_info.title,
            "variant": game_info.variant,
            "sourceFamily": "egame",
            "cpkCount": len(containers),
            "textureCount": 0,
        },
        "containers": containers,
        "entries": entries,
    }


def preview_texture(iso_path: Path, entry_id: str, output_path: Path) -> dict[str, Any]:
    _validate_iso_path(iso_path)
    if not output_path.name.lower().endswith(".png"):
        raise BHEJSONError(
            "PNG Output Required",
            "Texture previews must be written to a PNG file.",
            "Choose an output path ending in .png.",
            f"Output path: {output_path}",
            related_entry_id=entry_id,
        )

    pycdlib, CPK, PS2Cnf = _import_runtime()
    image = _load_texture_image(iso_path, entry_id, pycdlib, CPK, PS2Cnf)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, "PNG")
    return {
        "entryID": entry_id,
        "pngPath": str(output_path),
        "width": image.size[0],
        "height": image.size[1],
        "hasAlpha": _image_has_alpha(image),
        "originalISOModified": False,
        "patchedCopyWritten": False,
    }


def preview_texture_disc_root(root_path: Path, entry_id: str, output_path: Path) -> dict[str, Any]:
    _validate_disc_root_path(root_path)
    if not output_path.name.lower().endswith(".png"):
        raise BHEJSONError(
            "PNG Output Required",
            "Texture previews must be written to a PNG file.",
            "Choose an output path ending in .png.",
            f"Output path: {output_path}",
            related_entry_id=entry_id,
        )

    _pycdlib, CPK, PS2Cnf = _import_runtime()
    image = _load_texture_image_from_disc_root(root_path, entry_id, CPK, PS2Cnf)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, "PNG")
    return {
        "entryID": entry_id,
        "pngPath": str(output_path),
        "width": image.size[0],
        "height": image.size[1],
        "hasAlpha": _image_has_alpha(image),
        "originalISOModified": False,
        "patchedCopyWritten": False,
    }


def extract_texture(iso_path: Path, entry_id: str, output_path: Path) -> dict[str, Any]:
    _validate_iso_path(iso_path)
    if output_path.exists() and output_path.is_dir():
        raise BHEJSONError(
            "PNG Output Required",
            "Texture extraction needs a PNG output file path, not a directory.",
            "Choose a destination file ending in .png.",
            f"Output path: {output_path}",
            related_entry_id=entry_id,
        )
    if not output_path.name.lower().endswith(".png"):
        raise BHEJSONError(
            "PNG Output Required",
            "Extracted textures must be written to a PNG file.",
            "Choose an output path ending in .png.",
            f"Output path: {output_path}",
            related_entry_id=entry_id,
        )

    pycdlib, CPK, PS2Cnf = _import_runtime()
    image = _load_texture_image(iso_path, entry_id, pycdlib, CPK, PS2Cnf)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    overwrote_existing = output_path.exists()
    image.save(output_path, "PNG")
    return {
        "entryID": entry_id,
        "pngPath": str(output_path),
        "width": image.size[0],
        "height": image.size[1],
        "hasAlpha": _image_has_alpha(image),
        "overwroteExisting": overwrote_existing,
        "originalISOModified": False,
        "patchedCopyWritten": False,
    }


def extract_texture_disc_root(root_path: Path, entry_id: str, output_path: Path) -> dict[str, Any]:
    _validate_disc_root_path(root_path)
    _validate_png_output_path(output_path, entry_id, "Texture extraction needs a PNG output file path, not a directory.")

    _pycdlib, CPK, PS2Cnf = _import_runtime()
    image = _load_texture_image_from_disc_root(root_path, entry_id, CPK, PS2Cnf)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    overwrote_existing = output_path.exists()
    image.save(output_path, "PNG")
    return {
        "entryID": entry_id,
        "pngPath": str(output_path),
        "width": image.size[0],
        "height": image.size[1],
        "hasAlpha": _image_has_alpha(image),
        "overwroteExisting": overwrote_existing,
        "originalISOModified": False,
        "patchedCopyWritten": False,
    }


def _load_texture_image(iso_path: Path, entry_id: str, pycdlib, CPK, PS2Cnf):
    iso = pycdlib.PyCdlib()
    try:
        with contextlib.redirect_stdout(sys.stderr):
            iso.open(str(iso_path), "rb")
            _read_system_cnf(iso, PS2Cnf)
            cpk_records = _find_cpk_records(iso)

            for cpk_name, iso_record_path, record in cpk_records:
                cpk_data = BytesIO()
                iso.get_file_from_iso_fp(cpk_data, iso_path=iso_record_path)
                cpk = CPK.read_cpk(cpk_data, 0)

                for index, subtype in enumerate(cpk.subfile_types):
                    if subtype != b"APT\0":
                        continue
                    cpk.read_subfile(cpk_data, index)
                    textures = cpk.subfiles.get(index, ("APT", []))[1]
                    for texture_index, texture in enumerate(textures):
                        texture_id = _texture_entry_id(cpk_name, index, texture_index, texture.name)
                        if texture_id != entry_id:
                            continue
                        image = texture.get_image()
                        if image is None:
                            raise BHEJSONError(
                                "Preview Unavailable",
                                "The selected texture could not be decoded into an image.",
                                "Choose another supported APT texture.",
                                f"APTexture.get_image() returned None for {entry_id}.",
                                related_entry_id=entry_id,
                                safe_to_retry=False,
                            )
                        return image

        raise BHEJSONError(
            "Texture Not Found",
            "The requested texture entry was not found in the ISO scan results.",
            "Refresh the ISO scan and try the preview again.",
            f"Entry ID: {entry_id}",
            related_entry_id=entry_id,
            safe_to_retry=True,
        )
    finally:
        with contextlib.suppress(Exception):
            iso.close()


def _load_texture_image_from_disc_root(root_path: Path, entry_id: str, CPK, _PS2Cnf):
    with contextlib.redirect_stdout(sys.stderr):
        _read_system_cnf_from_root(root_path)
        cpk_files = _find_cpk_files(root_path)

        for cpk_name, cpk_path in cpk_files:
            cpk_data = BytesIO(cpk_path.read_bytes())
            cpk = CPK.read_cpk(cpk_data, 0)

            for index, subtype in enumerate(cpk.subfile_types):
                if subtype != b"APT\0":
                    continue
                cpk.read_subfile(cpk_data, index)
                textures = cpk.subfiles.get(index, ("APT", []))[1]
                for texture_index, texture in enumerate(textures):
                    texture_id = _texture_entry_id(cpk_name, index, texture_index, texture.name)
                    if texture_id != entry_id:
                        continue
                    image = texture.get_image()
                    if image is None:
                        raise BHEJSONError(
                            "Preview Unavailable",
                            "The selected texture could not be decoded into an image.",
                            "Choose another supported APT texture.",
                            f"APTexture.get_image() returned None for {entry_id}.",
                            related_entry_id=entry_id,
                            safe_to_retry=False,
                        )
                    return image

    raise BHEJSONError(
        "Texture Not Found",
        "The requested texture entry was not found in the disc-root scan results.",
        "Refresh the disc-root scan and try the preview again.",
        f"Entry ID: {entry_id}",
        related_entry_id=entry_id,
        safe_to_retry=True,
    )


def _module_available(module_name: str) -> bool:
    try:
        __import__(module_name)
        return True
    except Exception:
        return False


def _case_insensitive_child(parent: Path, expected_name: str) -> Path | None:
    expected = expected_name.lower()
    try:
        for child in parent.iterdir():
            if child.name.lower() == expected:
                return child
    except OSError:
        return None
    return None


def _validate_iso_path(iso_path: Path) -> None:
    if not iso_path.exists() or not iso_path.is_file():
        raise BHEJSONError(
            "ISO Not Found",
            "The selected ISO path does not point to a readable file. Your original ISO was not modified.",
            "Choose an existing PlayStation 2 ISO file.",
            f"Path: {iso_path}",
        )


def _validate_disc_root_path(root_path: Path) -> None:
    if not root_path.exists() or not root_path.is_dir():
        raise BHEJSONError(
            "Disc Root Not Found",
            "The selected disc root path does not point to a readable folder. Your original files were not modified.",
            "Choose a mounted PlayStation 2 disc volume or extracted disc root.",
            f"Path: {root_path}",
        )
    if _case_insensitive_child(root_path, "SYSTEM.CNF") is None:
        raise BHEJSONError(
            "SYSTEM.CNF Not Found",
            "The selected folder does not contain a PlayStation 2 SYSTEM.CNF file.",
            "Choose the mounted disc volume itself, not a parent folder.",
            f"Path: {root_path}",
        )
    data_dir = _case_insensitive_child(root_path, "DATA")
    if data_dir is not None and not data_dir.is_dir():
        raise BHEJSONError(
            "DATA Is Not A Folder",
            "The selected folder has an item named DATA, but it is not a folder.",
            "Choose the mounted disc volume itself, not a parent folder.",
            f"Path: {root_path}",
        )


def _validate_png_output_path(output_path: Path, entry_id: str, directory_message: str) -> None:
    if output_path.exists() and output_path.is_dir():
        raise BHEJSONError(
            "PNG Output Required",
            directory_message,
            "Choose a destination file ending in .png.",
            f"Output path: {output_path}",
            related_entry_id=entry_id,
        )
    if not output_path.name.lower().endswith(".png"):
        raise BHEJSONError(
            "PNG Output Required",
            "Extracted textures must be written to a PNG file.",
            "Choose an output path ending in .png.",
            f"Output path: {output_path}",
            related_entry_id=entry_id,
        )


def _import_runtime():
    try:
        import pycdlib
        from choroq.bhe.bhe_cpk import CPK
        from choroq.bhe.moddingui.common import PS2Cnf
    except Exception as error:
        raise BHEJSONError(
            "Python Dependencies Missing",
            "The Python BHE parser dependencies are not available to this Python runtime.",
            "Install the project Python dependencies, then try again.",
            f"{type(error).__name__}: {error}",
            safe_to_retry=True,
        ) from error
    return pycdlib, CPK, PS2Cnf


def _import_pycdlib():
    try:
        import pycdlib
    except Exception as error:
        raise BHEJSONError(
            "Python ISO Dependency Missing",
            "The Python ISO reader dependency is not available to this Python runtime.",
            "Install pycdlib in the configured Python environment, then try again.",
            f"{type(error).__name__}: {error}",
            safe_to_retry=True,
        ) from error
    return pycdlib


def _import_cpk_runtime():
    try:
        from choroq.bhe.bhe_cpk import CPK
    except Exception as error:
        raise BHEJSONError(
            "Python Dependencies Missing",
            "The Python BHE parser dependencies are not available to this Python runtime.",
            "Install the project Python dependencies, then try again.",
            f"{type(error).__name__}: {error}",
            safe_to_retry=True,
        ) from error
    return CPK


def _read_system_cnf(iso, PS2Cnf):
    cnf_data = BytesIO()
    try:
        iso.get_file_from_iso_fp(cnf_data, iso_path="/SYSTEM.CNF;1")
    except Exception as error:
        raise BHEJSONError(
            "SYSTEM.CNF Not Found",
            "The selected ISO does not expose the PlayStation 2 SYSTEM.CNF file.",
            "Choose a supported Choro-Q PlayStation 2 ISO.",
            f"{type(error).__name__}: {error}",
            safe_to_retry=True,
        ) from error

    cnf_data.seek(0)
    cnf = PS2Cnf(cnf_data)
    if not cnf.valid():
        raise BHEJSONError(
            "Invalid SYSTEM.CNF",
            "The selected ISO has a SYSTEM.CNF file, but it could not be read as a supported PlayStation 2 boot descriptor.",
            "Choose a supported Choro-Q PlayStation 2 ISO.",
            "PS2Cnf.valid() returned false.",
            safe_to_retry=True,
        )
    return cnf


def _read_system_cnf_lightweight(iso) -> PS2BootInfo:
    cnf_data = BytesIO()
    try:
        iso.get_file_from_iso_fp(cnf_data, iso_path="/SYSTEM.CNF;1")
    except Exception as error:
        raise BHEJSONError(
            "SYSTEM.CNF Not Found",
            "The selected ISO does not expose the PlayStation 2 SYSTEM.CNF file.",
            "Choose a supported Choro-Q PlayStation 2 ISO.",
            f"{type(error).__name__}: {error}",
            safe_to_retry=True,
        ) from error

    cnf_data.seek(0)
    cnf = PS2BootInfo(_read_elf_name_from_system_cnf(cnf_data.read().decode("utf-8", errors="replace")))
    if not cnf.valid():
        raise BHEJSONError(
            "Invalid SYSTEM.CNF",
            "The selected ISO has a SYSTEM.CNF file, but it could not be read as a supported PlayStation 2 boot descriptor.",
            "Choose a supported Choro-Q PlayStation 2 ISO.",
            "SYSTEM.CNF did not include a usable BOOT value.",
            safe_to_retry=True,
        )
    return cnf


def _read_system_cnf_from_root(root_path: Path):
    system_cnf_path = _case_insensitive_child(root_path, "SYSTEM.CNF")
    if system_cnf_path is None:
        raise BHEJSONError(
            "SYSTEM.CNF Not Found",
            "The selected folder does not contain the PlayStation 2 SYSTEM.CNF file.",
            "Choose the mounted disc volume itself, not a parent folder.",
            f"Path: {root_path}",
            safe_to_retry=True,
        )

    cnf = PS2BootInfo(_read_elf_name_from_system_cnf(system_cnf_path.read_text(errors="replace")))
    if not cnf.valid():
        raise BHEJSONError(
            "Invalid SYSTEM.CNF",
            "The selected folder has a SYSTEM.CNF file, but it could not be read as a supported PlayStation 2 boot descriptor.",
            "Choose a supported Choro-Q PlayStation 2 disc root.",
            "PS2Cnf.valid() returned false.",
            safe_to_retry=True,
        )
    return cnf


def _read_elf_name_from_system_cnf(text: str) -> str:
    for line in text.splitlines():
        if not line.upper().lstrip().startswith("BOOT"):
            continue
        _key, separator, value = line.partition("=")
        if not separator:
            continue
        boot_path = value.strip().replace("\\", "/")
        if ":" in boot_path:
            boot_path = boot_path.split(":", 1)[1]
        boot_path = boot_path.split(";", 1)[0].strip()
        boot_path = boot_path.strip("/")
        if "/" in boot_path:
            boot_path = boot_path.rsplit("/", 1)[1]
        return boot_path
    return ""


def _game_info(cnf) -> GameInfo:
    game_info = GAME_VERSIONS.get(cnf.elf_name)
    if game_info is None:
        egame_info = EGAME_VERSIONS.get(cnf.elf_name)
        if egame_info is not None:
            raise BHEJSONError(
                "HG2/HG3 Backend Not Wired Yet",
                f"The selected source is recognized as {egame_info.title} ({egame_info.variant}), but this Swift backend currently scans Barnhouse Effect CPK/APT content only.",
                "Keep this source mounted for local testing. The next backend phase should add an e-Game/HG2 scan command that maps CAR, COURSE, ACTION, FLD, SHOP, and related folders into the same Swift asset browser.",
                f"ELF: {cnf.elf_name}",
                safe_to_retry=True,
            )
        raise BHEJSONError(
            "Unsupported Choro-Q ISO",
            "The selected ISO boot identifier is not one of the supported Barnhouse Effect Choro-Q games.",
            "Choose HG1, HG4, Choro Q Works, Combat Choro-Q, or Shin Combat Choro-Q.",
            f"ELF: {cnf.elf_name}",
            safe_to_retry=True,
        )
    return game_info


def _egame_game_info(cnf) -> GameInfo:
    game_info = EGAME_VERSIONS.get(cnf.elf_name)
    if game_info is None:
        raise BHEJSONError(
            "Unsupported e-Game Disc Root",
            "The selected disc root is not a recognized Road Trip / HG2 / HG3 source.",
            "Choose a mounted Road Trip Adventure, Everywhere Road Trip, Choro-Q HG2, or Choro-Q HG3 volume.",
            f"ELF: {cnf.elf_name}",
            safe_to_retry=True,
        )
    return game_info


def _validate_egame_folder_layout(root_path: Path, cnf) -> None:
    folder_names = {
        child.name.upper()
        for child in root_path.iterdir()
        if child.is_dir()
    }
    _validate_egame_folder_names(folder_names, cnf, root_path)


def _validate_egame_folder_names(folder_names: set[str], cnf, source_path: Path) -> None:
    required = EGAME_HG3_REQUIRED_FOLDERS if cnf.elf_name in EGAME_HG3_BOOT_IDS else EGAME_HG2_REQUIRED_FOLDERS
    missing = sorted(required.difference(folder_names))
    if missing:
        raise BHEJSONError(
            "e-Game Folders Not Found",
            "The selected source is recognized as Road Trip / HG2 / HG3, but expected game folders were not found.",
            "Choose the mounted disc volume itself or a complete extracted disc root.",
            f"Missing folders: {', '.join(missing)}; Path: {source_path}",
            safe_to_retry=True,
        )


def _egame_scan_folders(root_path: Path) -> list[tuple[str, Path]]:
    folders: list[tuple[str, Path]] = []
    for child in root_path.iterdir():
        folder_name = child.name.upper()
        if child.is_dir() and folder_name in EGAME_SCAN_FOLDERS:
            folders.append((folder_name, child))
    folders.sort(key=lambda item: item[0])
    return folders


def _egame_matching_files(root_path: Path, folder_path: Path, cnf) -> list[Path]:
    return [
        path
        for path in sorted(folder_path.iterdir(), key=lambda candidate: candidate.name.upper())
        if path.is_file() and _egame_entry_metadata(_egame_relative_path(root_path, path), cnf) is not None
    ]


def _egame_entry(root_path: Path, folder_name: str, path: Path, cnf, game_info: GameInfo) -> dict[str, Any]:
    relative_path = _egame_relative_path(root_path, path)
    metadata = _egame_entry_metadata(relative_path, cnf)
    if metadata is None:
        kind = "unknown"
        format_name = "e-Game BIN"
        display_name = path.name
    else:
        kind, format_name, display_name = metadata
    file_size = path.stat().st_size
    return {
        "id": f"egame:{relative_path}",
        "containerID": f"egame:{folder_name}",
        "cpkName": folder_name,
        "name": display_name,
        "kind": kind,
        "format": format_name,
        "width": None,
        "height": None,
        "paletteSize": None,
        "sizeBytes": file_size,
        "offsetBytes": -1,
        "sector": -1,
        "support": "read-only",
        "canExtract": False,
        "canReplace": False,
        "compression": "none",
    }


def _egame_iso_entry(folder_name: str, relative_path: str, record, cnf) -> dict[str, Any]:
    metadata = _egame_entry_metadata(relative_path, cnf)
    if metadata is None:
        kind = "unknown"
        format_name = "e-Game BIN"
        display_name = relative_path.rsplit("/", 1)[-1]
    else:
        kind, format_name, display_name = metadata
    sector = int(record.orig_extent_loc)
    return {
        "id": f"egame:{relative_path}",
        "containerID": f"egame:{folder_name}",
        "cpkName": folder_name,
        "name": display_name,
        "kind": kind,
        "format": format_name,
        "width": None,
        "height": None,
        "paletteSize": None,
        "sizeBytes": int(record.data_length),
        "offsetBytes": sector * SECTOR_SIZE,
        "sector": sector,
        "support": "read-only",
        "canExtract": False,
        "canReplace": False,
        "compression": "none",
    }


def _egame_relative_path(root_path: Path, path: Path) -> str:
    return "/" + "/".join(part.upper() for part in path.relative_to(root_path).parts)


def _egame_entry_metadata(relative_path: str, cnf) -> tuple[str, str, str] | None:
    basename = _strip_iso_version(relative_path.rsplit("/", 1)[-1])
    stem = basename.rsplit(".", 1)[0]

    if cnf.elf_name in EGAME_HG2_BOOT_IDS:
        if re.match(r"^/CAR[0-4S]/Q[0-9][0-9]+\.BIN$", relative_path):
            return ("model", "HG2 car BIN", f"{_q_display_name(stem)} Body")
        if relative_path == "/CARS/TIRE.BIN":
            return ("part", "HG2 part BIN", "Tire Parts")
        if relative_path == "/CARS/WHEEL.BIN":
            return ("part", "HG2 part BIN", "Wheel Parts")
        if relative_path == "/CARS/PARTS.BIN":
            return ("part", "HG2 part BIN", "Upgrade Parts")
        if re.match(r"^/COURSE/C[0-9][0-9]\.BIN$", relative_path):
            return ("course", "HG2 course BIN", HG2_COURSE_NAMES_EUR.get(stem, stem))
        if re.match(r"^/ACTION/A[0-9][0-9]\.BIN$", relative_path):
            return ("course", "HG2 activity BIN", HG2_COURSE_NAMES_EUR.get(stem, stem))
        if re.match(r"^/FLD/[0-9][0-9][0-9]\.BIN$", relative_path):
            return ("field", "HG2 field BIN", f"Field {stem}")
        if re.match(r"^/SHOP/T[0-9][0-9]\.BIN$", relative_path):
            return ("shop", "HG2 shop BIN", f"Shop {stem}")

    if cnf.elf_name in EGAME_HG3_BOOT_IDS:
        if re.match(r"^/CARS/Q[0-9][0-9]+\.BIN$", relative_path):
            return ("model", "HG3 car BIN", f"{_q_display_name(stem)} Body")
        if re.match(r"^/COURSE/C[0-9][0-9](L|M|S)?\.BIN$", relative_path):
            return ("course", "HG3 course BIN", stem)
        if re.match(r"^/COURSE/A[0-9][0-9]\.BIN$", relative_path):
            return ("course", "HG3 activity BIN", stem)

    return None


def _q_display_name(stem: str) -> str:
    try:
        return "Q" + str(int(stem[1:]) + 1).zfill(2)
    except Exception:
        return stem


def _find_cpk_records(iso) -> list[tuple[str, str, Any]]:
    facade = iso.get_iso9660_facade()
    records: list[tuple[str, str, Any]] = []

    for dirname, _dirlist, filelist in iso.walk(iso_path="/"):
        for filename in filelist:
            iso_record_path = f"{dirname}/{filename}"
            normalized = _strip_iso_version(iso_record_path)
            if not CPK_PATH_RE.match(normalized):
                continue
            try:
                record = facade.get_record(iso_record_path)
            except Exception:
                record = facade.get_record(normalized)
                iso_record_path = normalized
            cpk_name = _strip_iso_version(filename)
            records.append((cpk_name, iso_record_path, record))

    records.sort(key=lambda item: (item[2].orig_extent_loc, item[0]))
    return records


def _find_cpk_files(root_path: Path) -> list[tuple[str, Path]]:
    data_dir = _case_insensitive_child(root_path, "DATA")
    if data_dir is None or not data_dir.is_dir():
        return []

    cpk_files = [
        (path.name.upper(), path)
        for path in data_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".cpk"
    ]
    cpk_files.sort(key=lambda item: item[0])
    return cpk_files


def _scan_cpk(iso, CPK, cpk_name: str, iso_record_path: str, record) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cpk_sector = int(record.orig_extent_loc)
    cpk_offset = cpk_sector * SECTOR_SIZE
    cpk_data = BytesIO()
    iso.get_file_from_iso_fp(cpk_data, iso_path=iso_record_path)
    return _scan_cpk_data(CPK, cpk_name, cpk_sector, cpk_offset, cpk_data)


def _scan_cpk_data(CPK, cpk_name: str, cpk_sector: int, cpk_offset: int, cpk_data: BytesIO) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    container_id = _container_id(cpk_name, cpk_sector)
    cpk_size = len(cpk_data.getbuffer())
    cpk = CPK.read_cpk(cpk_data, 0)
    entries: list[dict[str, Any]] = []

    for index, subtype in enumerate(cpk.subfile_types):
        entry_position = int(cpk.entry_positions[index])
        next_position = int(cpk.entry_positions[index + 1]) if index + 1 < len(cpk.entry_positions) else cpk_size
        entry_size = max(0, next_position - entry_position)
        entries.append(
            _subfile_entry(
                container_id,
                cpk_name,
                cpk_sector,
                cpk_offset,
                index,
                subtype,
                entry_position,
                entry_size,
            )
        )

        if subtype == b"APT\0":
            try:
                cpk.read_subfile(cpk_data, index)
                textures = cpk.subfiles.get(index, ("APT", []))[1]
            except Exception as error:
                entries[-1]["support"] = "risky"
                entries[-1]["format"] = "APT parse failed"
                entries[-1]["compression"] = "none"
                print(f"Failed to parse APT in {cpk_name} index {index}: {error}", file=sys.stderr)
                continue

            for texture_index, texture in enumerate(textures):
                entries.append(
                    _texture_entry(
                        container_id,
                        cpk_name,
                        cpk_sector,
                        cpk_offset,
                        index,
                        texture_index,
                        texture,
                    )
                )

    texture_count = sum(1 for entry in entries if entry["kind"] == "texture")
    support = "supported" if any(entry["support"] == "supported" for entry in entries) else "read-only"
    container = {
        "id": container_id,
        "name": cpk_name,
        "entryCount": len(entries),
        "textureCount": texture_count,
        "sector": cpk_sector,
        "support": support,
    }
    return container, entries


def _subfile_entry(
    container_id: str,
    cpk_name: str,
    cpk_sector: int,
    cpk_offset: int,
    index: int,
    subtype: bytes,
    entry_position: int,
    entry_size: int,
) -> dict[str, Any]:
    type_name = _subtype_name(subtype)
    support = _subfile_support(subtype)
    compression = "lzs" if subtype == b"LZS\0" else "none"
    return {
        "id": f"{cpk_name}:{index}:{type_name}",
        "containerID": container_id,
        "cpkName": cpk_name,
        "name": f"[{index}] {type_name}",
        "kind": _subfile_kind(subtype),
        "format": type_name,
        "width": None,
        "height": None,
        "paletteSize": None,
        "sizeBytes": entry_size,
        "offsetBytes": cpk_offset + entry_position,
        "sector": cpk_sector + int(entry_position / SECTOR_SIZE),
        "support": support,
        "canExtract": False,
        "canReplace": False,
        "compression": compression,
    }


def _texture_entry(
    container_id: str,
    cpk_name: str,
    cpk_sector: int,
    cpk_offset: int,
    apt_index: int,
    texture_index: int,
    texture,
) -> dict[str, Any]:
    has_data = texture.data not in (None, [])
    width = int(texture.width) if texture.width else None
    height = int(texture.height) if texture.height else None
    support = "supported" if has_data and width and height else "risky"
    return {
        "id": _texture_entry_id(cpk_name, apt_index, texture_index, texture.name),
        "containerID": container_id,
        "cpkName": cpk_name,
        "name": texture.name or f"texture_{texture_index}",
        "kind": "texture",
        "format": str(texture.colour_format),
        "width": width,
        "height": height,
        "paletteSize": int(texture.palette_size) if texture.palette_size else None,
        "sizeBytes": int(texture.total_size),
        "offsetBytes": cpk_offset + int(texture.data_offset),
        "sector": cpk_sector + int(int(texture.data_offset) / SECTOR_SIZE),
        "support": support,
        "canExtract": support == "supported",
        "canReplace": False,
        "compression": "none",
    }


def _container_id(cpk_name: str, sector: int) -> str:
    return f"{cpk_name}@{sector}"


def _texture_entry_id(cpk_name: str, apt_index: int, texture_index: int, texture_name: str) -> str:
    safe_name = texture_name or f"texture_{texture_index}"
    return f"{cpk_name}:{apt_index}:{texture_index}:{safe_name}"


def _strip_iso_version(path: str) -> str:
    return path.split(";", 1)[0]


def _subtype_name(subtype: bytes) -> str:
    if subtype == b"\x03\x18\x00\x00":
        return "TOC"
    try:
        decoded = subtype.decode("ascii").rstrip("\x00").strip()
    except Exception:
        decoded = ""
    if decoded:
        return decoded
    return "0x" + subtype.hex().upper()


def _subfile_kind(subtype: bytes) -> str:
    if subtype == b"APT\0":
        return "apt"
    if subtype == b"LZS\0":
        return "lzs"
    if subtype in (b"PBL\0", b"MPD\0", b"HPD\0", b"MPC\0"):
        return "model"
    if subtype in (b"TOC\0", b"\x03\x18\x00\x00"):
        return "text"
    return "unknown"


def _subfile_support(subtype: bytes) -> str:
    if subtype == b"APT\0":
        return "read-only"
    if subtype == b"LZS\0":
        return "compressed"
    if subtype in (b"PBL\0", b"MPD\0", b"HPD\0", b"MPC\0", b"TOC\0", b"\x03\x18\x00\x00", b"FONT"):
        return "read-only"
    return "unknown"


def _image_has_alpha(image) -> bool:
    if image.mode not in ("RGBA", "LA"):
        return False
    alpha = image.getchannel("A")
    extrema = alpha.getextrema()
    return extrema[0] < 255


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
