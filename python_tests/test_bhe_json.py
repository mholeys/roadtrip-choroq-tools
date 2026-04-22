import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "choroq" / "bhe" / "bhe_json.py"


class BHEJSONCLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_json_error(self, result):
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["protocolVersion"], 1)
        self.assertIn("backendVersion", payload)
        self.assertEqual(payload["status"], "error")
        self.assertIn("error", payload)
        error = payload["error"]
        self.assertIn("title", error)
        self.assertIn("explanation", error)
        self.assertIn("safeToRetry", error)
        self.assertFalse(error["originalISOModified"])
        self.assertFalse(error["patchedCopyWritten"])
        return error

    def test_missing_command_returns_structured_error(self):
        result = self.run_cli()
        error = self.assert_json_error(result)
        self.assertEqual(error["title"], "Command Required")

    def test_version_returns_protocol_metadata(self):
        result = self.run_cli("version")
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["protocolVersion"], 1)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["data"]["protocolVersion"], 1)
        self.assertIn("scan-iso", payload["data"]["commands"])
        self.assertIn("scan-disc-root", payload["data"]["commands"])
        self.assertIn("scan-egame-disc-root", payload["data"]["commands"])
        self.assertIn("extract-texture", payload["data"]["commands"])

    def test_health_check_reports_dependency_status_without_failing(self):
        result = self.run_cli("health-check")
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertIn("dependencies", payload["data"])
        self.assertIn("bchunk", payload["data"])

    def test_supported_types_reports_read_only_write_state(self):
        result = self.run_cli("list-supported-types")
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertFalse(payload["data"]["writeSupport"]["originalISOModification"])
        self.assertFalse(payload["data"]["writeSupport"]["patchedCopyWriting"])

    def test_unknown_command_returns_structured_error(self):
        result = self.run_cli("not-a-command")
        error = self.assert_json_error(result)
        self.assertEqual(error["title"], "Unknown Command")

    def test_scan_missing_iso_returns_structured_error_before_parser_imports(self):
        result = self.run_cli("scan-iso", "/definitely/missing/choroq.iso")
        error = self.assert_json_error(result)
        self.assertEqual(error["title"], "ISO Not Found")

    def test_preview_argument_validation_returns_structured_error(self):
        result = self.run_cli("preview-texture", "/tmp/game.iso", "BODY.CPK:0:0:cart_0")
        error = self.assert_json_error(result)
        self.assertEqual(error["title"], "Preview Arguments Required")

    def test_extract_argument_validation_returns_structured_error(self):
        result = self.run_cli("extract-texture", "/tmp/game.iso", "BODY.CPK:0:0:cart_0")
        error = self.assert_json_error(result)
        self.assertEqual(error["title"], "Extraction Arguments Required")

    def test_scan_disc_root_missing_folder_returns_structured_error(self):
        result = self.run_cli("scan-disc-root", "/definitely/missing/disc-root")
        error = self.assert_json_error(result)
        self.assertEqual(error["title"], "Disc Root Not Found")

    def test_scan_egame_disc_root_reports_read_only_hg2_entries(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "SYSTEM.CNF").write_text("BOOT2 = cdrom0:\\SLES_513.56;1\n", encoding="utf-8")
            for folder in [
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
            ]:
                (root / folder).mkdir()
            (root / "CAR0" / "Q00.BIN").write_bytes(b"car")
            (root / "COURSE" / "C00.BIN").write_bytes(b"course")
            (root / "ACTION" / "A07.BIN").write_bytes(b"action")
            (root / "SHOP" / "T04.BIN").write_bytes(b"shop")

            result = self.run_cli("scan-egame-disc-root", str(root))

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["data"]["iso"]["sourceFamily"], "egame")
        self.assertEqual(payload["data"]["iso"]["gameTitle"], "Road Trip Adventure / Choro-Q HG2")
        self.assertGreaterEqual(len(payload["data"]["containers"]), 4)
        self.assertTrue(all(entry["support"] == "read-only" for entry in payload["data"]["entries"]))
        self.assertTrue(all(entry["canExtract"] is False for entry in payload["data"]["entries"]))
        self.assertIn("Q01 Body", {entry["name"] for entry in payload["data"]["entries"]})


if __name__ == "__main__":
    unittest.main()
