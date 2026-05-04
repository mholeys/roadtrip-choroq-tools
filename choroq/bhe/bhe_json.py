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
VENDOR_ROOT = REPO_ROOT / "vendor"
if VENDOR_ROOT.is_dir() and str(VENDOR_ROOT) not in sys.path:
    sys.path.insert(0, str(VENDOR_ROOT))
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


@dataclass(frozen=True)
class EGameEntryInfo:
    kind: str
    format_name: str
    display_name: str
    descriptor: str
    model_description: str | None
    support: str
    support_reason: str
    can_extract: bool
    expected_export_outputs: list[dict[str, Any]]
    section_names: list[dict[str, Any]]


@dataclass(frozen=True)
class BHEExportedFile:
    path: str
    kind: str
    role: str
    previewable: bool

    def to_json(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "kind": self.kind,
            "role": self.role,
            "previewable": self.previewable,
        }


@dataclass(frozen=True)
class BHEExportManifest:
    operation_id: str
    source_modified: bool
    patched_copy_written: bool
    entry_ids: list[str]
    output_root: str
    primary_preview_path: str | None
    files: list[BHEExportedFile]
    overwritten_files: list[str]
    warnings: list[str]

    def to_json(self) -> dict[str, Any]:
        return {
            "operationID": self.operation_id,
            "sourceModified": self.source_modified,
            "patchedCopyWritten": self.patched_copy_written,
            "entryIDs": self.entry_ids,
            "outputRoot": self.output_root,
            "primaryPreviewPath": self.primary_preview_path,
            "files": [file.to_json() for file in self.files],
            "overwrittenFiles": self.overwritten_files,
            "warnings": self.warnings,
        }


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
EGAME_SCAN_FOLDERS = {"CAR0", "CAR1", "CAR2", "CAR3", "CAR4", "CARS", "COURSE", "ACTION", "FLD", "SHOP", "ITEM", "SOUND", "SYS"}
EGAME_CONTAINER_DISPLAY_NAMES = {
    "ROOT": "Disc Root",
    "CAR0": "Car Bay 1 (CAR0)",
    "CAR1": "Car Bay 2 (CAR1)",
    "CAR2": "Car Bay 3 (CAR2)",
    "CAR3": "Car Bay 4 (CAR3)",
    "CAR4": "Car Bay 5 (CAR4)",
    "CARS": "Shared Car Parts",
    "COURSE": "Race Courses",
    "ACTION": "Activity Courses",
    "FLD": "World Fields",
    "SHOP": "Town Shops",
    "ITEM": "Item Graphics",
    "SOUND": "Sounds",
    "SYS": "System Graphics",
}
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
HG3_COURSE_NAMES_EUR = {
    "C00": "Lake Side Castle",
    "C01": "Sunset Volcano",
    "C02": "Hot Sand Ruin",
    "C03": "Asian Miracle",
    "C04": "Jungle Beat",
    "C05": "Rainy Mansion",
    "C06": "Snow Palace Mountain",
    "C07": "Splash Highway",
    "C08": "Disco King's Cave",
    "C09": "Two-Tone Factory",
    "C10": "Heaven's Rainbow",
    "C11": "Space Trip",
    "C12": "Grunge Garden",
    "C13": "Scratch Mountain",
    "C14": "Echo Forest",
    "C15": "Noice City",
    "C16": "Live House",
    "C17": "Ending",
    "A00": "Beginners",
    "A01": "Speed Boat",
    "A02": "Balloon Hover",
    "A03": "The Fisher",
    "A04": "Jungle Heli",
    "A05": "Let's Side Jet",
    "A06": "Drag",
    "A07": "Water Drag",
    "A08": "Aqua Drag",
    "A09": "Soccer",
}
HG2_FIELD_NAMES_EUR = {
    "011": "Lighthouse",
    "012": "Ruins",
    "013": "Sandpolis",
    "023": "My City",
    "103": "Chestnut Canyon",
    "111": "UFO",
    "113": "Fuji City",
    "202": "Underwater Temple",
    "203": "White Mountain",
    "210": "Mushroom Road",
    "211": "Docks",
    "213": "Windmills",
    "220": "Bridge",
    "223": "Peach Town",
    "233": "Papaya Island",
}
HG2_OCEAN_FIELD_IDS = {
    "000",
    "001",
    "002",
    "010",
    "031",
    "100",
    "101",
    "122",
    "123",
    "131",
    "132",
    "133",
    "231",
    "300",
    "302",
    "303",
    "311",
    "312",
    "313",
    "320",
    "322",
    "323",
    "331",
    "332",
    "333",
}
HG2_SHOP_NAMES_EUR = {
    "T00": "Peach Town",
    "T01": "Fuji City",
    "T02": "Sandpolis",
    "T03": "Chestnut Canyon",
    "T04": "Mushroom Road",
    "T05": "White Mountain",
    "T06": "Papaya Island",
    "T07": "Cloud Hill",
    "T08": "My City",
    "T09": "Windmills",
    "T10": "Bridge",
    "T11": "UFO",
    "T12": "Ruins",
    "T13": "Lighthouse",
    "T14": "Field 022",
    "T15": "Field 110",
    "T16": "Field 120",
    "T17": "Field 202",
    "T18": "Field 212",
    "T19": "Field 221",
    "T20": "Field 232",
}
EGAME_DESCRIPTOR_BY_KIND = {
    "model": "Contains different parts for each car body, including body, lights, spoilers, jets, stickers, and texture data.",
    "part": "Contains shared car part, wheel, tire, or upgrade part data.",
    "course": "Contains a track or event map with textures, mesh data, minimap data, and map or event objects.",
    "field": "Contains one Road Trip world field region with world geometry and local textures.",
    "shop": "Contains textures for town shop and interior data.",
    "graphics": "Contains system, item, map, score, title, font, icon, or menu graphics data.",
    "sound": "Contains music, sound-bank, sequenced audio, driver, or PlayStation ADPCM audio data.",
}
HG2_CAR_SECTION_NAMES = [
    {"index": 0, "names": ["body", "front/back-lights", "brake-lights"]},
    {"index": 1, "names": ["lp-body", "lp-lights"]},
    {"index": 2, "names": ["spoiler"]},
    {"index": 3, "names": ["spoiler 2"]},
    {"index": 4, "names": ["jets"]},
    {"index": 5, "names": ["stickers"]},
    {"index": 6, "names": ["texture"]},
]
HG3_CAR_SECTION_NAMES = [
    {"index": 0, "names": ["body", "unknown", "brake-lights", "front/back-lights", "front/back-lights-black"]},
    {"index": 1, "names": ["lp-body", "null", "lp-lights", "lp-front/back-lights", "lp-front/back-lights-black"]},
    {"index": 2, "names": ["spoiler 1"]},
    {"index": 3, "names": ["f1 setup/spoiler"]},
    {"index": 4, "names": ["boat cover"]},
    {"index": 5, "names": ["hovercraft cover"]},
    {"index": 6, "names": ["stickers"]},
]
EGAME_CAR_EXPORT_OUTPUTS = [
    {"kind": "texture", "extension": "png", "role": "diffuse", "previewable": True},
    {"kind": "model", "extension": "obj", "role": "car section mesh", "previewable": True},
    {"kind": "material", "extension": "mtl", "role": "OBJ material", "previewable": False},
]
EGAME_SHOP_TEXTURE_EXPORT_OUTPUTS = [
    {"kind": "texture", "extension": "png", "role": "shop texture", "previewable": True},
]
EGAME_SCAN_ONLY_REASON_BY_KIND = {
    "part": "No safe JSON export command is wired for shared car part BIN files yet.",
    "course": "No safe JSON export command is wired for course or activity BIN files yet.",
    "field": "No safe JSON export command is wired for field BIN files yet.",
    "shop": "Only HG2 town shop texture BIN rows named T00.BIN through T20.BIN can export PNG textures in this build.",
    "graphics": "Graphics are identified and scanned, but no safe JSON texture export command is wired for this container yet.",
    "sound": "Sound assets are identified and scanned, but no safe JSON audio conversion command is wired yet.",
}


def main(argv: list[str]) -> int:
    try:
        if not argv:
            raise BHEJSONError(
                "Command Required",
                "Choose a BHE JSON command to run.",
                "Use version, health-check, list-supported-types, scan-iso, scan-egame-disc-root, report-missing-gui-assets, preview-texture, extract-texture, extract-egame-car, preview-egame-car, or extract-egame-shop-textures.",
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
        elif command == "report-missing-gui-assets":
            result = _run_report_missing_gui_assets(argv[1:])
        elif command == "preview-texture":
            result = _run_preview_texture(argv[1:])
        elif command == "preview-texture-disc-root":
            result = _run_preview_texture_disc_root(argv[1:])
        elif command == "extract-texture":
            result = _run_extract_texture(argv[1:])
        elif command == "extract-texture-disc-root":
            result = _run_extract_texture_disc_root(argv[1:])
        elif command == "extract-egame-car":
            result = _run_extract_egame_car(argv[1:])
        elif command == "preview-egame-car":
            result = _run_preview_egame_car(argv[1:])
        elif command == "extract-egame-shop-textures":
            result = _run_extract_egame_shop_textures(argv[1:])
        else:
            raise BHEJSONError(
                "Unknown Command",
                f"'{command}' is not a supported BHE JSON command.",
                "Use version, health-check, list-supported-types, scan-iso, scan-disc-root, preview-texture, extract-texture, extract-egame-car, preview-egame-car, or extract-egame-shop-textures.",
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


def _run_extract_egame_car(argv: list[str]) -> dict[str, Any]:
    if len(argv) != 4 or argv[2] != "--output-folder":
        raise BHEJSONError(
            "Car Export Arguments Required",
            "e-Game car export needs a source path, an e-Game car entry identifier, and an output folder.",
            "Run extract-egame-car with an entry ID from scan-egame-disc-root or scan-iso and an --output-folder path.",
            "Usage: extract-egame-car <disc-root-or-iso> <entry-id> --output-folder <folder>",
        )
    return extract_egame_car(Path(argv[0]), argv[1], Path(argv[3]))


def _run_preview_egame_car(argv: list[str]) -> dict[str, Any]:
    if len(argv) != 4 or argv[2] != "--output-folder":
        raise BHEJSONError(
            "Car Preview Arguments Required",
            "e-Game car preview needs a source path, an e-Game car entry identifier, and an output folder.",
            "Run preview-egame-car with an entry ID from scan-egame-disc-root or scan-iso and an --output-folder path.",
            "Usage: preview-egame-car <disc-root-or-iso> <entry-id> --output-folder <folder>",
        )
    return preview_egame_car(Path(argv[0]), argv[1], Path(argv[3]))


def _run_extract_egame_shop_textures(argv: list[str]) -> dict[str, Any]:
    if len(argv) != 4 or argv[2] != "--output-folder":
        raise BHEJSONError(
            "Shop Texture Export Arguments Required",
            "e-Game shop texture export needs a source path, an e-Game shop entry identifier, and an output folder.",
            "Run extract-egame-shop-textures with a supported SHOP/Txx.BIN entry ID from scan-egame-disc-root or scan-iso and an --output-folder path.",
            "Usage: extract-egame-shop-textures <disc-root-or-iso> <entry-id> --output-folder <folder>",
        )
    return extract_egame_shop_textures(Path(argv[0]), argv[1], Path(argv[3]))


def _run_report_missing_gui_assets(argv: list[str]) -> dict[str, Any]:
    if len(argv) < 1 or len(argv) > 2:
        raise BHEJSONError(
            "Missing GUI Report Arguments Required",
            "The missing-GUI report needs a Road Trip / HG2 / HG3 source path and an optional JSON list of represented entry identifiers.",
            "Run report-missing-gui-assets with the source used for the current scan.",
            "Usage: report-missing-gui-assets <disc-root-or-iso> [represented-entry-ids-json]",
        )
    represented_ids: set[str] = set()
    if len(argv) == 2 and argv[1].strip():
        try:
            decoded = json.loads(argv[1])
            if isinstance(decoded, list):
                represented_ids = {str(value) for value in decoded}
        except Exception as error:
            raise BHEJSONError(
                "Represented Entry List Invalid",
                "The represented GUI entry list must be JSON array text.",
                "Pass a JSON array of entry IDs or omit the argument.",
                f"{type(error).__name__}: {error}",
            ) from error
    return report_missing_gui_assets(Path(argv[0]), represented_ids)


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
            "report-missing-gui-assets",
            "preview-texture",
            "preview-texture-disc-root",
            "extract-texture",
            "extract-texture-disc-root",
            "extract-egame-car",
            "preview-egame-car",
            "extract-egame-shop-textures",
        ],
    }


def health_check() -> dict[str, Any]:
    dependency_specs = [
        ("tkinter", "tkinter", False),
        ("customtkinter", "customtkinter", False),
        ("Pillow", "PIL.Image", True),
        ("colorama", "colorama", False),
        ("lzstring", "lzstring", False),
        ("lzsslib", "lzsslib", True),
        ("pyelftools", "elftools", False),
        ("pycdlib", "pycdlib", True),
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
    missing_required = [
        dependency
        for dependency in dependencies
        if dependency["requiredForBHE"] and not dependency["available"]
    ]
    return {
        "pythonExecutable": sys.executable,
        "pythonVersion": sys.version.split()[0],
        "dependencies": dependencies,
        "bheReady": not missing_required,
        "missingRequiredDependencies": missing_required,
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
                "operations": ["scan", "extract-egame-car", "preview-egame-car"],
                "readOnly": True,
                "writable": False,
            },
            {
                "kind": "shop",
                "format": "HG2 shop BIN",
                "operations": ["scan", "extract-egame-shop-textures"],
                "readOnly": True,
                "writable": False,
            },
            {
                "kind": "graphics",
                "format": "GSL/E3D/ICO/BIN",
                "operations": ["scan"],
                "readOnly": True,
                "writable": False,
            },
            {
                "kind": "sound",
                "format": "VAG/TSQ/TVB/IRX",
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
    root_entries = [_egame_entry(root_path, "ROOT", path, cnf, game_info) for path in _egame_root_files(root_path)]
    if root_entries:
        containers.append(
            {
                "id": "egame:ROOT",
                "name": "ROOT",
                "displayName": EGAME_CONTAINER_DISPLAY_NAMES["ROOT"],
                "entryCount": len(root_entries),
                "textureCount": 0,
                "sector": -1,
                "support": "read-only",
            }
        )
        entries.extend(root_entries)
    for folder_name, folder_path in _egame_scan_folders(root_path):
        folder_entries = [_egame_entry(root_path, folder_name, path, cnf, game_info) for path in _egame_matching_files(root_path, folder_path, cnf)]
        if not folder_entries:
            continue
        container = {
            "id": f"egame:{folder_name}",
            "name": folder_name,
            "displayName": EGAME_CONTAINER_DISPLAY_NAMES.get(folder_name, folder_name),
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

    records_by_folder: dict[str, list[tuple[str, Any]]] = {folder: [] for folder in EGAME_SCAN_FOLDERS | {"ROOT"}}
    for dirname, _dirlist, filelist in iso.walk(iso_path="/"):
        folder_name = _strip_iso_version(dirname).strip("/").upper()
        if folder_name == "":
            folder_name = "ROOT"
        if folder_name not in records_by_folder:
            continue
        for filename in filelist:
            record_path = f"{dirname}/{filename}" if dirname != "/" else f"/{filename}"
            relative_path = _strip_iso_version(record_path).upper()
            if _is_non_game_file(relative_path):
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
                "displayName": EGAME_CONTAINER_DISPLAY_NAMES.get(folder_name, folder_name),
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


def extract_egame_car(source_path: Path, entry_id: str, output_folder: Path) -> dict[str, Any]:
    return _write_egame_car_assets(source_path, entry_id, output_folder, "extract-egame-car")


def preview_egame_car(source_path: Path, entry_id: str, output_folder: Path) -> dict[str, Any]:
    return _write_egame_car_assets(source_path, entry_id, output_folder, "preview-egame-car")


def extract_egame_shop_textures(source_path: Path, entry_id: str, output_folder: Path) -> dict[str, Any]:
    return _write_egame_shop_texture_assets(source_path, entry_id, output_folder)


def report_missing_gui_assets(source_path: Path, represented_ids: set[str]) -> dict[str, Any]:
    if source_path.is_dir():
        scan = scan_egame_disc_root(source_path)
    elif source_path.is_file() and source_path.suffix.lower() == ".iso":
        scan = _scan_egame_iso_for_report(source_path)
    else:
        raise BHEJSONError(
            "Unsupported Source Type",
            "The missing-GUI report needs a mounted Road Trip / HG2 / HG3 disc root or ISO.",
            "Choose the source used for the current scan.",
            f"Path: {source_path}",
            safe_to_retry=True,
        )

    entries = scan["entries"]
    represented = represented_ids or {entry["id"] for entry in entries}
    missing = [
        _missing_gui_asset_from_entry(entry)
        for entry in entries
        if entry["id"] not in represented
    ]
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in missing:
        groups.setdefault(item["guessedRole"], []).append(item)

    return {
        "sourcePath": str(source_path),
        "discoveredFileCount": len(entries),
        "representedEntryCount": len(represented_ids),
        "missingFileCount": len(missing),
        "groups": [
            {"role": role, "count": len(items), "assets": items}
            for role, items in sorted(groups.items())
        ],
        "assets": missing,
    }


def _scan_egame_iso_for_report(source_path: Path) -> dict[str, Any]:
    _validate_iso_path(source_path)
    pycdlib = _import_pycdlib()
    iso = pycdlib.PyCdlib()
    try:
        with contextlib.redirect_stdout(sys.stderr):
            iso.open(str(source_path), "rb")
            cnf = _read_system_cnf_lightweight(iso)
            return _scan_egame_iso_open(iso, source_path, cnf)
    finally:
        with contextlib.suppress(Exception):
            iso.close()


def _missing_gui_asset_from_entry(entry: dict[str, Any]) -> dict[str, Any]:
    extension = entry["id"].rsplit(".", 1)[-1].upper() if "." in entry["id"] else ""
    support = entry.get("support", "unknown")
    supported_operations = entry.get("supportedOperations") or []
    understands = support not in {"unsupported", "unknown"} or bool(supported_operations)
    return {
        "path": entry["id"].removeprefix("egame:"),
        "extension": extension,
        "sizeBytes": entry.get("sizeBytes", 0),
        "guessedRole": _missing_gui_role(entry),
        "pythonUnderstands": understands,
        "availableOperations": supported_operations or ["scan-only"],
        "capability": _missing_gui_capability(entry),
        "missingReason": "Discovered by backend but not present in the current Swift GUI entry list.",
    }


def _missing_gui_role(entry: dict[str, Any]) -> str:
    kind = entry.get("kind", "unknown")
    path = entry.get("id", "")
    if kind == "model":
        return "car assets missing from GUI" if "/CAR" in path or "/CARS/" in path else "city/town/shop assets missing from GUI"
    if kind == "texture" or kind == "shop":
        return "textures missing from GUI"
    if kind == "course":
        return "race/activity course assets missing from GUI"
    if kind == "field":
        return "world/field assets missing from GUI"
    if kind == "graphics":
        return "graphics missing from GUI"
    if kind == "sound":
        return "sounds missing from GUI"
    return "unknown/unclassified files missing from GUI"


def _missing_gui_capability(entry: dict[str, Any]) -> str:
    operations = set(entry.get("supportedOperations") or [])
    if "extract-egame-car" in operations or "extract-egame-shop-textures" in operations:
        return "exportable"
    if entry.get("support") == "scan-only":
        return "scanned only"
    if entry.get("support") == "unsupported":
        return "unsupported"
    return "metadata only"


def _write_egame_car_assets(source_path: Path, entry_id: str, output_folder: Path, operation_id: str) -> dict[str, Any]:
    if output_folder.exists() and not output_folder.is_dir():
        raise BHEJSONError(
            "Output Folder Required",
            "e-Game car export needs a folder path, not a file path.",
            "Choose or create a destination folder for the exported OBJ, MTL, and PNG files.",
            f"Output path: {output_folder}",
            related_entry_id=entry_id,
        )
    _validate_export_output_folder(source_path, output_folder, entry_id)

    relative_path = _egame_car_relative_path(entry_id)
    if relative_path is None:
        raise BHEJSONError(
            "Unsupported e-Game Entry",
            "Only Road Trip / HG2 / HG3 car body BIN entries can be exported as 3D assets in this build.",
            "Select an entry such as egame:/CAR0/Q00.BIN or egame:/CARS/Q00.BIN.",
            f"Entry ID: {entry_id}",
            related_entry_id=entry_id,
        )

    car_data, cnf = _read_egame_entry_bytes(source_path, relative_path)
    metadata = _egame_entry_metadata(relative_path, cnf)
    if metadata is None or metadata.kind != "model" or not metadata.can_extract:
        raise BHEJSONError(
            "Unsupported e-Game Entry",
            "The selected e-Game entry is not a supported car model row.",
            "Select a car body entry from CAR0-CAR4, CARS, or the HG3 CARS folder.",
            f"Entry ID: {entry_id}; relative path: {relative_path}",
            related_entry_id=entry_id,
        )

    output_folder.mkdir(parents=True, exist_ok=True)
    existing_files = {
        str(path)
        for path in output_folder.rglob("*")
        if path.is_file()
    }
    basename = _strip_iso_version(relative_path.rsplit("/", 1)[-1]).rsplit(".", 1)[0]
    version = 3 if cnf.elf_name in EGAME_HG3_BOOT_IDS else 2

    try:
        manifest = _export_egame_car_bytes(
            car_data,
            basename,
            output_folder,
            version,
            entry_id,
            existing_files,
            operation_id,
        )
    except BHEJSONError:
        raise
    except Exception as error:
        raise BHEJSONError(
            "e-Game Car Export Failed",
            "The selected car entry could not be converted to OBJ/MTL/PNG. Your source files were not modified.",
            "Try another car body entry or keep this file as scan-only until the extractor supports its exact layout.",
            f"{type(error).__name__}: {error}",
            related_entry_id=entry_id,
            safe_to_retry=True,
        ) from error

    return manifest.to_json()


def _write_egame_shop_texture_assets(source_path: Path, entry_id: str, output_folder: Path) -> dict[str, Any]:
    if output_folder.exists() and not output_folder.is_dir():
        raise BHEJSONError(
            "Output Folder Required",
            "e-Game shop texture export needs a folder path, not a file path.",
            "Choose or create a destination folder for the exported PNG files.",
            f"Output path: {output_folder}",
            related_entry_id=entry_id,
        )
    _validate_export_output_folder(source_path, output_folder, entry_id)

    relative_path = _egame_shop_relative_path(entry_id)
    if relative_path is None:
        raise BHEJSONError(
            "Unsupported e-Game Shop Entry",
            "Only HG2 town shop texture rows named SHOP/T00.BIN through SHOP/T20.BIN can be exported as PNG textures in this build.",
            "Select a supported shop row from the Town Shops section.",
            f"Entry ID: {entry_id}",
            related_entry_id=entry_id,
        )

    shop_data, cnf = _read_egame_entry_bytes(source_path, relative_path)
    metadata = _egame_entry_metadata(relative_path, cnf)
    if metadata is None or metadata.kind != "shop" or not metadata.can_extract:
        raise BHEJSONError(
            "Unsupported e-Game Shop Entry",
            "The selected e-Game entry is not a supported shop texture row.",
            "Select an HG2 town shop row named T00.BIN through T20.BIN.",
            f"Entry ID: {entry_id}; relative path: {relative_path}",
            related_entry_id=entry_id,
        )

    output_folder.mkdir(parents=True, exist_ok=True)
    existing_files = {
        str(path)
        for path in output_folder.rglob("*")
        if path.is_file()
    }
    basename = _strip_iso_version(relative_path.rsplit("/", 1)[-1]).rsplit(".", 1)[0]

    try:
        manifest = _export_egame_shop_texture_bytes(
            shop_data,
            basename,
            metadata.display_name,
            output_folder,
            entry_id,
            existing_files,
        )
    except BHEJSONError:
        raise
    except Exception as error:
        raise BHEJSONError(
            "e-Game Shop Texture Export Failed",
            "The selected shop entry could not be decoded into PNG textures. Your source files were not modified.",
            "Try another supported town shop row or keep this file as scan-only until the extractor supports its exact layout.",
            f"{type(error).__name__}: {error}",
            related_entry_id=entry_id,
            safe_to_retry=True,
        ) from error

    return manifest.to_json()


def _egame_car_relative_path(entry_id: str) -> str | None:
    if not entry_id.startswith("egame:"):
        return None
    relative_path = _strip_iso_version(entry_id.removeprefix("egame:")).upper()
    if re.match(r"^/CAR[0-4]/Q[0-9][0-9]+\.BIN$", relative_path):
        return relative_path
    if re.match(r"^/CARS/Q[0-9][0-9]+\.BIN$", relative_path):
        return relative_path
    return None


def _egame_shop_relative_path(entry_id: str) -> str | None:
    if not entry_id.startswith("egame:"):
        return None
    relative_path = _strip_iso_version(entry_id.removeprefix("egame:")).upper()
    if re.match(r"^/SHOP/T[0-9][0-9]\.BIN$", relative_path):
        return relative_path
    return None


def _read_egame_entry_bytes(source_path: Path, relative_path: str) -> tuple[bytes, PS2BootInfo]:
    if not source_path.exists():
        raise BHEJSONError(
            "Source Not Found",
            "The selected source path does not exist. Your original files were not modified.",
            "Choose the mounted disc root or ISO used for the current scan.",
            f"Path: {source_path}",
            safe_to_retry=True,
        )
    if source_path.is_dir():
        _validate_disc_root_path(source_path)
        cnf = _read_system_cnf_from_root(source_path)
        _egame_game_info(cnf)
        _validate_egame_folder_layout(source_path, cnf)
        file_path = _case_insensitive_descendant(source_path, relative_path)
        if file_path is None or not file_path.is_file():
            raise BHEJSONError(
                "e-Game Entry Not Found",
                "The selected car entry was not found under the mounted disc root.",
                "Refresh the source scan and try the export again.",
                f"Entry path: {relative_path}; source: {source_path}",
                safe_to_retry=True,
            )
        return file_path.read_bytes(), cnf
    if source_path.is_file() and source_path.suffix.lower() == ".iso":
        _validate_iso_path(source_path)
        pycdlib = _import_pycdlib()
        iso = pycdlib.PyCdlib()
        try:
            with contextlib.redirect_stdout(sys.stderr):
                iso.open(str(source_path), "rb")
                cnf = _read_system_cnf_lightweight(iso)
                _egame_game_info(cnf)
                record_path = _find_egame_iso_record_path(iso, relative_path)
                if record_path is None:
                    raise BHEJSONError(
                        "e-Game Entry Not Found",
                        "The selected car entry was not found inside the ISO.",
                        "Refresh the source scan and try the export again.",
                        f"Entry path: {relative_path}; source: {source_path}",
                        safe_to_retry=True,
                    )
                buffer = BytesIO()
                iso.get_file_from_iso_fp(buffer, iso_path=record_path)
                return buffer.getvalue(), cnf
        finally:
            with contextlib.suppress(Exception):
                iso.close()
    raise BHEJSONError(
        "Unsupported Source Type",
        "e-Game car export needs a mounted disc root or ISO source. Your original files were not modified.",
        "Choose the source used for the current Road Trip / HG2 / HG3 scan.",
        f"Path: {source_path}",
        safe_to_retry=True,
    )


def _case_insensitive_descendant(root_path: Path, relative_path: str) -> Path | None:
    current = root_path
    for part in relative_path.strip("/").split("/"):
        child = _case_insensitive_child(current, part)
        if child is None:
            return None
        current = child
    return current


def _find_egame_iso_record_path(iso, relative_path: str) -> str | None:
    for dirname, _dirlist, filelist in iso.walk(iso_path="/"):
        folder_name = _strip_iso_version(dirname).strip("/").upper()
        if folder_name not in EGAME_SCAN_FOLDERS:
            continue
        for filename in filelist:
            record_path = f"{dirname}/{filename}"
            normalized = _strip_iso_version(record_path).upper()
            if normalized == relative_path:
                return record_path
    return None


def _export_egame_car_bytes(
    car_data: bytes,
    basename: str,
    output_root: Path,
    version: int,
    entry_id: str,
    existing_files: set[str],
    operation_id: str,
) -> BHEExportManifest:
    CarModel, Texture = _import_egame_car_runtime()
    exported_files: list[BHEExportedFile] = []
    warnings: list[str] = []

    mesh_section_names = [
        ["body", "lights", "brake-light"],
        ["lp-body", "lp-lights"],
        ["spoiler"],
        ["spoiler2"],
        ["jets"],
        ["sticker"],
    ]
    mesh_section_names_hg3 = [
        ["body", "unknown", "brake-light", "lights", "lights2"],
        ["lp-body", "null", "lp-lights", "lp-lights-2"],
        ["spoiler"],
        ["f1-spoiler"],
        ["boat-adapter"],
        ["hover-adapter"],
        ["sticker"],
    ]
    if version == 3:
        mesh_section_names = mesh_section_names_hg3

    with contextlib.redirect_stdout(sys.stderr):
        file = BytesIO(car_data)
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        car = CarModel.read_car(file, 0, file_size)

        has_textures = len(car.textures) >= 2
        texture_path = f"{basename}.png"
        if has_textures:
            _address, texture = car.textures[0]
            _clut_address, clut = car.textures[1]
            unswizzled = Texture.unswizzle_bytes(clut)
            texture.palette = unswizzled
            texture.palette_width = clut.width
            texture.palette_height = clut.height
            texture_output = output_root / texture_path
            texture.write_texture_to_png(str(texture_output))
            exported_files.append(
                BHEExportedFile(str(texture_output), "texture", "diffuse", True)
            )
        else:
            warnings.append("No paired texture/CLUT payload was found; exported meshes may have material files only.")

        mesh_count = 0
        for section_index, subfile in enumerate(car.meshes):
            for mesh_index, mesh in enumerate(subfile):
                if (
                    basename not in ["PARTS", "TIRE", "WHEEL", "FASHION"]
                    and section_index < len(mesh_section_names)
                    and mesh_index < len(mesh_section_names[section_index])
                ):
                    role = mesh_section_names[section_index][mesh_index]
                    mesh_stem = f"{basename}-{section_index}-{mesh_index}-{role}"
                else:
                    role = "mesh"
                    mesh_stem = f"{basename}-{section_index}-{mesh_index}"

                obj_path = output_root / f"{mesh_stem}.obj"
                with obj_path.open("w", encoding="utf-8") as fout:
                    mesh.write_mesh_to_type("obj", fout, material=basename)
                exported_files.append(BHEExportedFile(str(obj_path), "model", role, True))
                mesh_count += 1

                if has_textures:
                    mtl_path = output_root / f"{mesh_stem}.mtl"
                    with mtl_path.open("w", encoding="utf-8") as fout:
                        Texture.save_material_file_obj(fout, basename, texture_path)
                    exported_files.append(BHEExportedFile(str(mtl_path), "material", role, False))

        if mesh_count == 0:
            warnings.append("No meshes were decoded from the selected car entry.")

    output_files = [file.path for file in exported_files]
    overwritten_files = sorted(path for path in output_files if path in existing_files)
    primary_preview_path = next((file.path for file in exported_files if file.kind == "model" and file.role == "body"), None)
    if primary_preview_path is None:
        primary_preview_path = next((file.path for file in exported_files if file.kind == "model"), None)

    return BHEExportManifest(
        operation_id=operation_id,
        source_modified=False,
        patched_copy_written=False,
        entry_ids=[entry_id],
        output_root=str(output_root),
        primary_preview_path=primary_preview_path,
        files=exported_files,
        overwritten_files=overwritten_files,
        warnings=warnings,
    )


def _export_egame_shop_texture_bytes(
    shop_data: bytes,
    basename: str,
    display_name: str,
    output_root: Path,
    entry_id: str,
    existing_files: set[str],
) -> BHEExportManifest:
    Shop = _import_egame_shop_runtime()
    exported_files: list[BHEExportedFile] = []
    warnings: list[str] = []

    with contextlib.redirect_stdout(sys.stderr):
        shop = Shop.from_file(BytesIO(shop_data), 0)
        for texture_index, texture in enumerate(shop.textures):
            if texture is None or not getattr(texture, "texture", None):
                warnings.append(f"Skipped texture {texture_index}: no decoded pixel payload.")
                continue
            if not getattr(texture, "width", 0) or not getattr(texture, "height", 0):
                warnings.append(f"Skipped texture {texture_index}: no usable dimensions.")
                continue

            role = f"texture-{texture_index:02d}"
            output_path = output_root / f"{basename}-{texture_index:02d}.png"
            try:
                texture.write_texture_to_png(str(output_path))
            except Exception as error:
                warnings.append(f"Skipped {role}: {type(error).__name__}: {error}")
                continue
            exported_files.append(BHEExportedFile(str(output_path), "texture", role, True))

    if not exported_files:
        raise BHEJSONError(
            "No Shop Textures Exported",
            "The selected shop row was recognized, but no texture payload could be written as a PNG.",
            "Try another supported town shop row or keep this file as scan-only.",
            f"Entry ID: {entry_id}; display name: {display_name}; warnings: {'; '.join(warnings)}",
            related_entry_id=entry_id,
        )

    output_files = [file.path for file in exported_files]
    overwritten_files = sorted(path for path in output_files if path in existing_files)
    return BHEExportManifest(
        operation_id="extract-egame-shop-textures",
        source_modified=False,
        patched_copy_written=False,
        entry_ids=[entry_id],
        output_root=str(output_root),
        primary_preview_path=exported_files[0].path,
        files=exported_files,
        overwritten_files=overwritten_files,
        warnings=warnings,
    )


def _import_egame_car_runtime():
    try:
        from choroq.egame.car import CarModel
        from choroq.egame.texture import Texture
    except Exception as error:
        raise BHEJSONError(
            "Python e-Game Dependencies Missing",
            "The Python e-Game extractor dependencies are not available to this Python runtime.",
            "Install the project Python dependencies, then try again.",
            f"{type(error).__name__}: {error}",
            safe_to_retry=True,
        ) from error
    return CarModel, Texture


def _import_egame_shop_runtime():
    try:
        from choroq.egame.shop import Shop
    except Exception as error:
        raise BHEJSONError(
            "Python e-Game Dependencies Missing",
            "The Python e-Game shop texture extractor dependencies are not available to this Python runtime.",
            "Install the project Python dependencies, then try again.",
            f"{type(error).__name__}: {error}",
            safe_to_retry=True,
        ) from error
    return Shop


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


def _validate_export_output_folder(source_path: Path, output_folder: Path, entry_id: str) -> None:
    if not source_path.exists() or not source_path.is_dir():
        return
    try:
        resolved_source = source_path.resolve()
        resolved_output = output_folder.resolve(strict=False)
    except Exception:
        return
    if resolved_output == resolved_source or resolved_source in resolved_output.parents:
        raise BHEJSONError(
            "Output Folder Is Inside Source",
            "Exports must be written outside the mounted disc root or source fixture folder. Your source files were not modified.",
            "Choose a destination folder outside the opened Road Trip / HG2 / HG3 source.",
            f"Source: {source_path}; output: {output_folder}",
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


def _egame_root_files(root_path: Path) -> list[Path]:
    return [
        path
        for path in sorted(root_path.iterdir(), key=lambda candidate: candidate.name.upper())
        if path.is_file() and not _is_non_game_file(_egame_relative_path(root_path, path))
    ]


def _egame_matching_files(root_path: Path, folder_path: Path, cnf) -> list[Path]:
    return [
        path
        for path in sorted(folder_path.iterdir(), key=lambda candidate: candidate.name.upper())
        if path.is_file() and not _is_non_game_file(_egame_relative_path(root_path, path))
    ]


def _egame_entry(root_path: Path, folder_name: str, path: Path, cnf, game_info: GameInfo) -> dict[str, Any]:
    relative_path = _egame_relative_path(root_path, path)
    metadata = _egame_entry_metadata(relative_path, cnf)
    if metadata is None:
        metadata = _egame_unknown_metadata(path.name)
    file_size = path.stat().st_size
    entry = {
        "id": f"egame:{relative_path}",
        "containerID": f"egame:{folder_name}",
        "cpkName": folder_name,
        "serviceBayName": EGAME_CONTAINER_DISPLAY_NAMES.get(folder_name, folder_name),
        "name": metadata.display_name,
        "kind": metadata.kind,
        "format": metadata.format_name,
        "width": None,
        "height": None,
        "paletteSize": None,
        "sizeBytes": file_size,
        "offsetBytes": -1,
        "sector": -1,
        "support": metadata.support,
        "canExtract": metadata.can_extract,
        "canReplace": False,
        "compression": "none",
        "meshCount": None,
        "textureCount": None,
    }
    entry.update(_egame_metadata_json(metadata))
    return entry


def _egame_iso_entry(folder_name: str, relative_path: str, record, cnf) -> dict[str, Any]:
    metadata = _egame_entry_metadata(relative_path, cnf)
    if metadata is None:
        metadata = _egame_unknown_metadata(relative_path.rsplit("/", 1)[-1])
    sector = int(record.orig_extent_loc)
    entry = {
        "id": f"egame:{relative_path}",
        "containerID": f"egame:{folder_name}",
        "cpkName": folder_name,
        "serviceBayName": EGAME_CONTAINER_DISPLAY_NAMES.get(folder_name, folder_name),
        "name": metadata.display_name,
        "kind": metadata.kind,
        "format": metadata.format_name,
        "width": None,
        "height": None,
        "paletteSize": None,
        "sizeBytes": int(record.data_length),
        "offsetBytes": sector * SECTOR_SIZE,
        "sector": sector,
        "support": metadata.support,
        "canExtract": metadata.can_extract,
        "canReplace": False,
        "compression": "none",
        "meshCount": None,
        "textureCount": None,
    }
    entry.update(_egame_metadata_json(metadata))
    return entry


def _egame_relative_path(root_path: Path, path: Path) -> str:
    return "/" + "/".join(part.upper() for part in path.relative_to(root_path).parts)


def _is_non_game_file(relative_path: str) -> bool:
    return relative_path.rsplit("/", 1)[-1].upper() in {".DS_STORE"}


def _egame_entry_metadata(relative_path: str, cnf) -> EGameEntryInfo | None:
    basename = _strip_iso_version(relative_path.rsplit("/", 1)[-1])
    stem = basename.rsplit(".", 1)[0]
    suffix = basename.rsplit(".", 1)[-1].upper() if "." in basename else ""

    if cnf.elf_name in EGAME_HG2_BOOT_IDS:
        if re.match(r"^/CAR[0-4S]/Q[0-9][0-9]+\.BIN$", relative_path):
            return _egame_metadata("model", "HG2 car BIN", f"{_q_display_name(stem)} Body", True, HG2_CAR_SECTION_NAMES)
        if relative_path == "/CARS/TIRE.BIN":
            return _egame_metadata("part", "HG2 part BIN", "Tire Parts", False, HG2_CAR_SECTION_NAMES)
        if relative_path == "/CARS/WHEEL.BIN":
            return _egame_metadata("part", "HG2 part BIN", "Wheel Parts", False, HG2_CAR_SECTION_NAMES)
        if relative_path == "/CARS/PARTS.BIN":
            return _egame_metadata("part", "HG2 part BIN", "Upgrade Parts", False, HG2_CAR_SECTION_NAMES)
        if re.match(r"^/COURSE/C[0-9][0-9]\.BIN$", relative_path):
            return _egame_metadata("course", "HG2 course BIN", HG2_COURSE_NAMES_EUR.get(stem, stem), False, [])
        if re.match(r"^/ACTION/A[0-9][0-9]\.BIN$", relative_path):
            return _egame_metadata("course", "HG2 activity BIN", HG2_COURSE_NAMES_EUR.get(stem, stem), False, [])
        if re.match(r"^/FLD/[0-9][0-9][0-9]\.BIN$", relative_path):
            if stem in HG2_FIELD_NAMES_EUR:
                return _egame_metadata("field", "HG2 field BIN", f"{HG2_FIELD_NAMES_EUR[stem]} ({stem})", False, [])
            if stem in HG2_OCEAN_FIELD_IDS:
                return _egame_metadata("field", "HG2 field BIN", f"Ocean ({stem})", False, [])
            return _egame_metadata("field", "HG2 field BIN", f"Field {stem}", False, [])
        if re.match(r"^/SHOP/T[0-9][0-9]\.BIN$", relative_path):
            return _egame_metadata("shop", "HG2 shop BIN", HG2_SHOP_NAMES_EUR.get(stem, f"Shop {stem}"), True, [])
        if relative_path == "/SHOP/GARAGE.BIN":
            return _egame_metadata("shop", "HG2 garage/shop BIN", "Garage Shop Data", False, [])
        if relative_path.startswith("/ITEM/") and suffix == "GSL":
            return _egame_metadata("graphics", "HG2 item GSL", f"{stem} Graphics", False, [])
        if relative_path.startswith("/SYS/"):
            if suffix == "GSL":
                return _egame_metadata("graphics", "HG2 system GSL", f"{stem} Graphics", False, [])
            if suffix == "E3D":
                return _egame_metadata("model", "HG2 system E3D", f"{stem} System Model", False, [])
            if suffix == "ICO":
                return _egame_metadata("graphics", "PS2 icon", basename, False, [])
            if basename in {"PUTI.BIN", "OPTION.BIN", "OPTION2.BIN", "COIN.BIN"}:
                return _egame_metadata("graphics", "HG2 system BIN", f"{stem} Graphics", False, [])
        if relative_path.startswith("/SOUND/"):
            if suffix == "VAG":
                role = "Engine / vehicle sound" if stem.endswith(("_L", "_R")) else "Sound effect"
                return _egame_metadata("sound", "PlayStation ADPCM VAG", role + f" ({basename})", False, [])
            if suffix == "TSQ":
                return _egame_metadata("sound", "Sequenced music TSQ", f"{stem} Music Sequence", False, [])
            if suffix == "TVB":
                return _egame_metadata("sound", "Sound bank TVB", f"{stem} Sound Bank", False, [])
            if suffix == "IRX":
                return _egame_metadata("sound", "PS2 sound driver IRX", basename, False, [])
        if suffix == "IRX":
            return _egame_metadata("unknown", "PS2 module IRX", basename, False, [])
        if suffix == "IMG":
            return _egame_metadata("unknown", "PS2 IOP image", basename, False, [])
        if basename == "SYSTEM.CNF":
            return _egame_metadata("text", "PS2 boot config", basename, False, [])
        if basename in EGAME_VERSIONS:
            return _egame_metadata("unknown", "PS2 executable", basename, False, [])

    if cnf.elf_name in EGAME_HG3_BOOT_IDS:
        if re.match(r"^/CARS/Q[0-9][0-9]+\.BIN$", relative_path):
            return _egame_metadata("model", "HG3 car BIN", f"{_q_display_name(stem)} Body", True, HG3_CAR_SECTION_NAMES)
        if re.match(r"^/COURSE/C[0-9][0-9](L|M|S)?\.BIN$", relative_path):
            return _egame_metadata("course", "HG3 course BIN", HG3_COURSE_NAMES_EUR.get(stem, stem), False, [])
        if re.match(r"^/COURSE/A[0-9][0-9]\.BIN$", relative_path):
            return _egame_metadata("course", "HG3 activity BIN", HG3_COURSE_NAMES_EUR.get(stem, stem), False, [])
        if relative_path.startswith("/ITEM/") and suffix == "GSL":
            return _egame_metadata("graphics", "HG3 item GSL", f"{stem} Graphics", False, [])
        if relative_path.startswith("/SYS/") and suffix in {"GSL", "ICO", "BIN"}:
            return _egame_metadata("graphics", f"HG3 system {suffix}", f"{stem} Graphics", False, [])
        if relative_path.startswith("/SOUND/"):
            return _egame_metadata("sound", f"HG3 sound {suffix}", basename, False, [])

    return None


def _egame_metadata(
    kind: str,
    format_name: str,
    display_name: str,
    exportable: bool,
    section_names: list[dict[str, Any]],
) -> EGameEntryInfo:
    if exportable:
        support = "exportable"
        if kind == "shop":
            support_reason = "Supported by extract-egame-shop-textures; source files are read-only and PNG output is written to the selected folder."
            expected_outputs = EGAME_SHOP_TEXTURE_EXPORT_OUTPUTS
        else:
            support_reason = "Supported by extract-egame-car and preview-egame-car; source files are read-only and output is written to the selected folder."
            expected_outputs = EGAME_CAR_EXPORT_OUTPUTS
    else:
        support = "scan-only"
        support_reason = EGAME_SCAN_ONLY_REASON_BY_KIND.get(kind, "No safe JSON export command is wired for this e-Game BIN type yet.")
        expected_outputs = []

    descriptor = EGAME_DESCRIPTOR_BY_KIND.get(kind, "Recognized e-Game entry.")
    return EGameEntryInfo(
        kind=kind,
        format_name=format_name,
        display_name=display_name,
        descriptor=descriptor,
        model_description=descriptor if kind in {"model", "part", "course", "field"} else None,
        support=support,
        support_reason=support_reason,
        can_extract=exportable,
        expected_export_outputs=expected_outputs,
        section_names=section_names,
    )


def _egame_unknown_metadata(display_name: str) -> EGameEntryInfo:
    suffix = display_name.rsplit(".", 1)[-1].upper() if "." in display_name else "binary"
    return EGameEntryInfo(
        kind="unknown",
        format_name=f"Unknown {suffix}",
        display_name=display_name,
        descriptor="Unrecognized e-Game entry.",
        model_description=None,
        support="unsupported",
        support_reason="This file is not recognized by the safe JSON backend scanner.",
        can_extract=False,
        expected_export_outputs=[],
        section_names=[],
    )


def _egame_metadata_json(metadata: EGameEntryInfo) -> dict[str, Any]:
    return {
        "descriptor": metadata.descriptor,
        "modelDescription": metadata.model_description,
        "supportReason": metadata.support_reason,
        "unsupportedReason": None if metadata.can_extract else metadata.support_reason,
        "expectedExportOutputs": metadata.expected_export_outputs,
        "sectionNames": metadata.section_names,
        "partSectionNames": [
            name
            for section in metadata.section_names
            for name in section.get("names", [])
        ],
        "supportedOperations": (
            _egame_supported_operations(metadata)
        ),
    }


def _egame_supported_operations(metadata: EGameEntryInfo) -> list[str]:
    if not metadata.can_extract:
        return ["scan-egame-disc-root"]
    if metadata.kind == "shop":
        return ["scan-egame-disc-root", "extract-egame-shop-textures"]
    return ["scan-egame-disc-root", "extract-egame-car", "preview-egame-car"]


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
