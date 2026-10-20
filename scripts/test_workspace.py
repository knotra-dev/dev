from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import workspace


class WorkspaceTest(unittest.TestCase):
    def test_dev_stops_only_its_engine_when_desktop_exits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            shutil.copy(Path(__file__).with_name("dev.sh"), root / "scripts/dev.sh")
            (root / "repos/engine/bin").mkdir(parents=True)
            (root / "repos/desktop").mkdir()
            stubs = root / "stubs"
            stubs.mkdir()
            engine = root / "repos/engine/bin/knotra"
            engine.write_text(
                f"#!{sys.executable}\n"
                "import os, signal, time\n"
                "from pathlib import Path\n"
                "signal.signal(signal.SIGTERM, lambda *_: exit(0))\n"
                "Path(os.environ['TEST_ENGINE_PID']).write_text(str(os.getpid()))\n"
                "while True: time.sleep(0.01)\n"
            )
            engine.chmod(0o755)
            frontend = stubs / "bun"
            frontend.write_text(
                f"#!{sys.executable}\n"
                "import os, time\n"
                "from pathlib import Path\n"
                "for _ in range(500):\n"
                "    if Path(os.environ['TEST_ENGINE_PID']).exists(): exit(0)\n"
                "    time.sleep(0.01)\n"
                "exit(1)\n"
            )
            frontend.chmod(0o755)
            pid_file = root / "engine.pid"
            env = dict(
                os.environ,
                PATH=str(stubs) + os.pathsep + os.environ["PATH"],
                TEST_ENGINE_PID=str(pid_file),
            )
            subprocess.run(
                ["bash", str(root / "scripts/dev.sh")], check=True, env=env, timeout=10
            )
            with self.assertRaises(ProcessLookupError):
                os.kill(int(pid_file.read_text()), 0)

    def test_bootstrap_preserves_existing_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            engine = root / "repos/engine"
            engine.mkdir(parents=True)
            edited = engine / "edited.txt"
            edited.write_text("local work")
            with patch("workspace.subprocess.run") as run:
                workspace.bootstrap(
                    root, {"engine": {"url": "unused", "commit": "unused"}}
                )
                run.assert_not_called()
            self.assertEqual(edited.read_text(), "local work")

    def test_lock_refuses_dirty_product_checkout(self):
        with patch("workspace.git", return_value=" M source.go"):
            with self.assertRaisesRegex(ValueError, "commit or stash engine"):
                workspace.current(Path("unused"), clean=True)

    def test_new_checkout_uses_locked_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("workspace.subprocess.run") as run:
                workspace.bootstrap(root, {"engine": {"url": "repo", "commit": "abc"}})
            self.assertEqual(
                run.call_args_list[0].args[0],
                ["git", "clone", "repo", str(root / "repos/engine")],
            )
            self.assertEqual(
                run.call_args_list[1].args[0][-3:], ["checkout", "--detach", "abc"]
            )


if __name__ == "__main__":
    unittest.main()
