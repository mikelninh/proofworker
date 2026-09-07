import json
import tempfile
import unittest
from pathlib import Path

from proofworker.engine import verify

ROOT = Path(__file__).resolve().parents[1]

class EngineTests(unittest.TestCase):
    def test_inline_pass(self):
        spec={"task":"x","deliverable":"tests passed; rollback ready","criteria":[
            {"id":"C1","text":"tests","checks":[{"type":"text_contains","value":"tests passed"}]},
            {"id":"C2","text":"rollback","checks":[{"type":"text_contains","value":"rollback"}]}
        ]}
        r=verify(spec, ROOT)
        self.assertEqual(r["verdict"],"pass")
        self.assertEqual(r["score"],100)

    def test_command_is_unknown_without_permission(self):
        spec={"criteria":[{"id":"C1","text":"run","checks":[{"type":"command","argv":["python","--version"]}]}]}
        r=verify(spec, ROOT, allow_exec=False)
        self.assertEqual(r["verdict"],"unknown")

    def test_path_escape_becomes_unknown(self):
        spec={"criteria":[{"id":"C1","text":"escape","checks":[{"type":"file_exists","path":"../secret"}]}]}
        r=verify(spec, ROOT)
        self.assertEqual(r["verdict"],"unknown")

class GoldenCases(unittest.TestCase):
    def run_case(self, name, allow_exec=False):
        p=ROOT/"examples"/name/"spec.json"
        spec=json.loads(p.read_text())
        return verify(spec,p.parent,allow_exec=allow_exec)

    def test_golden_01_pass(self):
        self.assertEqual(self.run_case("golden_01_code",True)["verdict"],"pass")

    def test_golden_02_fail(self):
        self.assertEqual(self.run_case("golden_02_research")["verdict"],"fail")

    def test_golden_03_pass(self):
        self.assertEqual(self.run_case("golden_03_data")["verdict"],"pass")

if __name__ == "__main__":
    unittest.main()
