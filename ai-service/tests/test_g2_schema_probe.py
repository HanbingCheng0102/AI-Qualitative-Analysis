from __future__ import annotations

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


AI_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(AI_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_SERVICE_ROOT))

from tools import g2_schema_probe


class G2ProbeSafetyTests(unittest.TestCase):
    def test_default_mode_never_calls_a_live_provider(self):
        output = io.StringIO()
        with patch.object(
            g2_schema_probe,
            "run_live_probe",
        ) as live, redirect_stdout(output):
            exit_code = g2_schema_probe.main([])

        self.assertEqual(0, exit_code)
        live.assert_not_called()
        self.assertEqual(
            "SKIPPED",
            json.loads(output.getvalue())["outcome"],
        )

    def test_explicit_live_all_calls_each_model_once(self):
        output = io.StringIO()
        with patch.object(
            g2_schema_probe,
            "run_live_probe",
            side_effect=lambda model_key: {
                "model_key": model_key,
                "outcome": "PASS",
            },
        ) as live, redirect_stdout(output):
            exit_code = g2_schema_probe.main(["--live", "--model", "all"])

        self.assertEqual(0, exit_code)
        self.assertEqual(
            ["azure", "llama", "qwen"],
            [call.args[0] for call in live.call_args_list],
        )

    def test_probe_validator_accepts_only_the_approved_branches(self):
        self.assertEqual(
            "ASSIGN_VALID",
            g2_schema_probe.validate_probe_response({
                "decision": {"action": "assign", "cluster_id": 0},
            }),
        )
        self.assertEqual(
            "NEW_VALID",
            g2_schema_probe.validate_probe_response({
                "decision": {
                    "action": "new",
                    "label": "Theme",
                    "summary": "Summary",
                },
            }),
        )
        with self.assertRaises(ValueError):
            g2_schema_probe.validate_probe_response({
                "decision": {"action": "assign", "cluster_id": 1},
            })


@unittest.skipUnless(
    os.environ.get("RUN_G2_LIVE_PROBES") == "1",
    "Set RUN_G2_LIVE_PROBES=1 for manual provider probes.",
)
class G2ProbeLiveTests(unittest.TestCase):
    def test_azure_live(self):
        self.assertEqual(
            "PASS",
            g2_schema_probe.run_live_probe("azure")["outcome"],
        )

    def test_llama_live(self):
        self.assertEqual(
            "PASS",
            g2_schema_probe.run_live_probe("llama")["outcome"],
        )

    def test_qwen_live(self):
        self.assertEqual(
            "PASS",
            g2_schema_probe.run_live_probe("qwen")["outcome"],
        )


if __name__ == "__main__":
    unittest.main()
