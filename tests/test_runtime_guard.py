import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "runtime_guard.py"
spec = importlib.util.spec_from_file_location("runtime_guard", SCRIPT_PATH)
runtime_guard = importlib.util.module_from_spec(spec)
sys.modules["runtime_guard"] = runtime_guard
spec.loader.exec_module(runtime_guard)


class MatchHelpersTest(unittest.TestCase):
    def test_match_any_case_insensitive(self):
        self.assertEqual(runtime_guard.match_any("NPM Install now", ["npm install"]), "npm install")
        self.assertEqual(runtime_guard.match_any("npm run build", ["npm install"]), "")

    def test_path_matches_directory_prefix(self):
        self.assertEqual(runtime_guard.path_matches("src/auth/session.ts", ["auth/", "src/auth/"]), "auth/")
        self.assertEqual(runtime_guard.path_matches("src/ui/button.tsx", ["auth/"]), "")

    def test_path_matches_exact_file(self):
        self.assertEqual(runtime_guard.path_matches("package.json", ["package.json"]), "package.json")
        self.assertEqual(runtime_guard.path_matches("frontend/package.json", ["package.json"]), "package.json")


class StateRoundTripTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmpdir.name)
        self.rules = {"state_dir": ".architecture-due-diligence"}

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_load_state_defaults_when_missing(self):
        state = runtime_guard.load_state(self.cwd, self.rules)
        self.assertEqual(state["mode"], "unknown")
        self.assertEqual(state["changed_files"], [])

    def test_save_then_load_round_trip(self):
        state = runtime_guard.default_state()
        state["mode"] = "audit_read_only"
        state["changed_files"] = ["src/x.py"]
        runtime_guard.save_state(self.cwd, self.rules, state)
        loaded = runtime_guard.load_state(self.cwd, self.rules)
        self.assertEqual(loaded["mode"], "audit_read_only")
        self.assertEqual(loaded["changed_files"], ["src/x.py"])


class PreToolUseTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmpdir.name)
        self.rules = runtime_guard.load_rules()
        state = runtime_guard.default_state()
        state["mode"] = "audit_read_only"
        runtime_guard.save_state(self.cwd, self.rules, state)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run(self, payload, capsys=None):
        import io
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            runtime_guard.handle_pre_tool_use(payload, self.rules)
        except SystemExit:
            pass
        finally:
            sys.stdout = old_stdout
        return captured.getvalue()

    def test_audit_mode_denies_write_tool(self):
        out = self._run({"cwd": str(self.cwd), "tool_name": "Write", "tool_input": {"file_path": "a.py"}})
        self.assertIn("deny", out)

    def test_audit_mode_denies_npm_install(self):
        out = self._run({"cwd": str(self.cwd), "tool_name": "Bash", "tool_input": {"command": "npm install lodash"}})
        self.assertIn("deny", out)

    def test_audit_mode_allows_git_status(self):
        out = self._run({"cwd": str(self.cwd), "tool_name": "Bash", "tool_input": {"command": "git status"}})
        self.assertEqual(out, "")

    def test_remediation_mode_asks_on_risky_path(self):
        state = runtime_guard.default_state()
        state["mode"] = "remediation"
        runtime_guard.save_state(self.cwd, self.rules, state)
        out = self._run({"cwd": str(self.cwd), "tool_name": "Edit", "tool_input": {"file_path": "package.json"}})
        self.assertIn("ask", out)

    def test_remediation_mode_allows_ordinary_file(self):
        state = runtime_guard.default_state()
        state["mode"] = "remediation"
        runtime_guard.save_state(self.cwd, self.rules, state)
        out = self._run({"cwd": str(self.cwd), "tool_name": "Edit", "tool_input": {"file_path": "src/util.py"}})
        self.assertEqual(out, "")


class StopHookTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmpdir.name)
        self.rules = runtime_guard.load_rules()

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run_stop(self, payload):
        import io
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            runtime_guard.handle_stop(payload, self.rules)
        except SystemExit:
            pass
        finally:
            sys.stdout = old_stdout
        return captured.getvalue()

    def test_blocks_once_when_unverified_changes_exist(self):
        state = runtime_guard.default_state()
        state["mode"] = "remediation"
        state["changed_files"] = ["src/x.py"]
        runtime_guard.save_state(self.cwd, self.rules, state)

        out = self._run_stop({"cwd": str(self.cwd)})
        self.assertIn("block", out)

        reloaded = runtime_guard.load_state(self.cwd, self.rules)
        self.assertEqual(reloaded["stop_block_count"], 1)

    def test_does_not_block_twice(self):
        state = runtime_guard.default_state()
        state["mode"] = "remediation"
        state["changed_files"] = ["src/x.py"]
        state["stop_block_count"] = 1
        runtime_guard.save_state(self.cwd, self.rules, state)

        out = self._run_stop({"cwd": str(self.cwd)})
        self.assertEqual(out, "")

    def test_allows_when_verification_recorded(self):
        state = runtime_guard.default_state()
        state["mode"] = "remediation"
        state["changed_files"] = ["src/x.py"]
        state["verification_commands"] = ["npm test"]
        runtime_guard.save_state(self.cwd, self.rules, state)

        out = self._run_stop({"cwd": str(self.cwd)})
        self.assertEqual(out, "")

    def test_noop_outside_guard_modes(self):
        state = runtime_guard.default_state()
        state["mode"] = "feature_build"
        state["changed_files"] = ["src/x.py"]
        runtime_guard.save_state(self.cwd, self.rules, state)

        out = self._run_stop({"cwd": str(self.cwd)})
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
