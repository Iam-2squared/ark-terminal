"""Offline regression: V3 blocked reason must surface, no transport re-run/order."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import hashlib
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import launcher_automatic_bridge_v4 as bridge


class TransportReasonForwarding(unittest.TestCase):
    def test_blocked_reason_is_not_swallowed_by_prefix_filter(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            probe=root/"Prepare-No11AutomaticLiveTransportV3.ps1"
            probe.write_text("# mock original physical transport; never executed\n",encoding="utf-8")
            engine=root/"engine"
            (engine/"windows").mkdir(parents=True)
            (engine/"windows"/"Read-No11BrokerSnapshot.ps1").write_text(
                "# mock broker library; never executed\n",encoding="utf-8")
            private=root/"private"
            private.mkdir()
            settings=root/"settings.json"
            settings.write_text("{}",encoding="utf-8")
            binding={
                "transportProbe":str(probe),
                "transportProbeSha256":hashlib.sha256(probe.read_bytes()).hexdigest(),
                "engine":str(engine),
                "settings":str(settings),
            }
            # This is the exact contract emitted by V3's catch block.
            fake=SimpleNamespace(returncode=2,
                stdout=("AUTOMATIC_TRANSPORT=BLOCKED|NO11_AUTO_TRANSPORT_EXCEL_NOT_READY\n"
                        "ORDER_TRIGGER_WRITTEN_TO_ONE=False\n"
                        "ORDER_SENT=False\n"),
                stderr="")
            lines=StringIO()
            with patch.object(bridge.subprocess,"run",return_value=fake) as subprocess_run:
                with redirect_stdout(lines):
                    with self.assertRaisesRegex(
                        ValueError,"NO11_AUTOSTART_PHYSICAL_TRANSPORT_SETUP_FAILED"):
                        bridge.capture_transport(binding,{},{"privateRoot":str(private)},"2026-11-06")
            self.assertEqual(subprocess_run.call_count,1)
            text=lines.getvalue()
            self.assertIn("AUTOMATIC_TRANSPORT=BLOCKED|NO11_AUTO_TRANSPORT_EXCEL_NOT_READY",text)
            self.assertIn("ORDER_TRIGGER_WRITTEN_TO_ONE=False",text)
            self.assertIn("ORDER_SENT=False",text)
            self.assertNotIn("AUTOMATIC_TRANSPORT=CREATED",text)
            self.assertNotIn("TRADE_LAUNCHED=True",text)


if __name__=="__main__":
    unittest.main(verbosity=2)
