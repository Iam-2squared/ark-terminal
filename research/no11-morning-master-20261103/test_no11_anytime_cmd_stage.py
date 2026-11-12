"""Offline source/command staging regressions; never Trade or broker API calls."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import stage_no11_anytime_cmd as stage

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
COMMIT = "4e6f87480424685524088083ea88768065360834"


def git_bytes(name):
    full = ("research/no11-morning-master-20261103/" + name)
    return subprocess.check_output(["git", "show", "HEAD:" + full], cwd=REPO)


class StagedDirectCmd(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ark-cmd-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = self.root / "store"
        self.store.mkdir()
        self.src = self.root / "inputs"
        self.src.mkdir()
        self.target = self.root / "staging"
        self.python = Path(sys.executable) if os.name == "nt" else self.root / "python.exe"
        if os.name != "nt":
            self.python.write_bytes(b"CI_DUMMY_PYTHON_EXE")
        for name in stage.FILES:
            (self.src / name).write_bytes(git_bytes(name))
        (self.src / stage.MODULE).write_bytes((HERE / stage.MODULE).read_bytes())
        self.settings = self.store / "settings.json"
        self.binding = self.store / "automatic-inputs.json"
        self.settings.write_text(json.dumps({
            "schemaId": "ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1",
            "sameDayApprovalRequired": True,
            "automaticOrderAuthorization": False,
            "orderTransmission": False,
            "normalMaxPositions": 3,
        }), encoding="utf-8")
        self.binding.write_text(json.dumps({
            "schemaId": "ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1",
            "orderTransmission": False,
            "python": str(self.python),
        }), encoding="utf-8")

    def prepare(self):
        return stage.plan(self.src, self.store, self.python,
                          self.target, commit=COMMIT)

    def original_store(self):
        return {p.name: p.read_bytes() for p in self.store.iterdir() if p.is_file()}

    def test_staging_only_writes_external_staged_bundle(self):
        original = self.original_store()
        runner = self.prepare()
        self.assertEqual(self.original_store(), original)
        self.assertTrue(stage.verify(runner.parent))
        self.assertEqual(set(p.name for p in runner.parent.iterdir()), {
            *stage.ALL_MODULES, stage.MANIFEST, stage.RUNNER,
        })
        rec = json.loads((runner.parent / stage.MANIFEST).read_text())
        self.assertFalse(rec["orderTransmission"])
        self.assertFalse(rec["tradeStarted"])
        self.assertTrue(rec["afterHoursApplyOnly"])
        self.assertEqual(rec["sourceGitBlobs"], stage.FILES)

    def test_direct_cmd_starts_python_not_powershell_and_prompts_on_apply(self):
        script = stage.command(self.python, self.store).decode("ascii")
        self.assertTrue(script.startswith("@echo off\r\n"))
        self.assertIn('"%~dp0stage_no11_anytime_cmd.py" --verify "%~dp0."', script)
        self.assertIn('"%~dp0install_no11_anytime_preopen.py" --store ', script)
        self.assertIn('if /I "%~1"=="probe" goto CHECK', script)
        self.assertIn('if /I "%~1"=="audit" goto CHECK', script)
        self.assertIn('if /I "%~1"=="apply" goto CHECK', script)
        self.assertIn("choice /C YN /N /M", script)
        self.assertIn("--probe-gate", script)
        self.assertNotIn("powershell.exe", script.lower())
        self.assertNotIn("Start-Process", script)
        self.assertNotIn("taskkill", script.lower())
        self.assertNotIn("Stop-Process", script)

    def test_modified_pinned_source_blocks_before_staging(self):
        p = self.src / stage.INSTALL
        p.write_bytes(p.read_bytes() + b"\n# tampered\n")
        original = self.original_store()
        with self.assertRaisesRegex(ValueError, "MODULE_PIN"):
            self.prepare()
        self.assertEqual(original, self.original_store())
        self.assertFalse(self.target.exists())

    def test_changed_bundle_or_settings_fail_closed(self):
        runner = self.prepare()
        p = runner.parent / stage.INSTALL
        before = p.read_bytes()
        p.write_bytes(before + b"#tampered\n")
        with self.assertRaisesRegex(ValueError, "BUNDLE_SOURCE_CHANGED"):
            stage.verify(runner.parent)
        p.write_bytes(before)
        self.settings.write_bytes(self.settings.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "LOCAL_INSTALL_CHANGED_RESTAGE"):
            stage.verify(runner.parent)

    def test_changed_runner_and_symlink_sidecar_block(self):
        runner = self.prepare()
        runner.write_bytes(runner.read_bytes() + b"echo tampered\r\n")
        with self.assertRaisesRegex(ValueError, "BUNDLE_RUNNER_CHANGED"):
            stage.verify(runner.parent)

    def test_cmd_metacharacters_block_not_escaped(self):
        with self.assertRaisesRegex(ValueError, "UNSAFE_WINDOWS_CMD_PATH"):
            stage.cmd_path(self.root / "some&path")
        with self.assertRaisesRegex(ValueError, "UNSAFE_WINDOWS_CMD_PATH"):
            stage.cmd_path(self.root / "bang!bad")
        with self.assertRaisesRegex(ValueError, "UNSAFE_WINDOWS_CMD_PATH"):
            stage.cmd_path(self.root / "quote%PATH%")

    def test_only_staged_cli_modes_and_no_order_enable(self):
        self.assertEqual(stage.FILES[stage.INSTALL],
                         stage.git_blob(git_bytes(stage.INSTALL)))
        self.assertFalse(set(stage.FILES).intersection({
            "Start-No11UnifiedLauncher.ps1", "no11_broker_execution_service.py",
            "Invoke-No11MsiiOrder.ps1"}))

    @unittest.skipUnless(os.name == "nt", "real Windows CMD only")
    def test_real_windows_cmd_direct_probe_no_orders(self):
        runner = self.prepare()
        proc = subprocess.run(["cmd.exe", "/d", "/c", str(runner), "probe"],
                              capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(proc.returncode, 0, proc.stdout[-1000:] + proc.stderr[-1000:])
        self.assertIn("NO11_CMD_STAGE_BUNDLE=VERIFIED", proc.stdout)
        self.assertIn("NO11_GATE_PROBE=READ_ONLY", proc.stdout)
        self.assertIn("TRADE_STARTED=False", proc.stdout)
        self.assertIn("ORDER_TRANSMISSION=False", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
