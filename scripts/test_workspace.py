from pathlib import Path
import json
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
        for name in workspace.NAMES:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                repo = root / "repos" / name
                repo.mkdir(parents=True)
                edited = repo / "edited.txt"
                edited.write_text("local work")
                with patch("workspace.subprocess.run") as run:
                    workspace.bootstrap(
                        root, {name: {"url": "unused", "commit": "unused"}}
                    )
                    run.assert_not_called()
                self.assertEqual(edited.read_text(), "local work")

    def test_lock_validates_docs_repository_and_revision(self):
        entries = {
            name: {
                "url": f"https://github.com/knotra-dev/{name}.git",
                "commit": "a" * 40,
            }
            for name in workspace.NAMES
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / "repos.lock.json"
            lock.write_text(json.dumps(entries))
            self.assertEqual(workspace.read_lock(root), entries)
            for field, value, message in (
                (
                    "url",
                    "https://github.com/other/docs.git",
                    "unexpected repository URL: docs",
                ),
                ("commit", "abc", "lock requires a full commit SHA: docs"),
            ):
                with self.subTest(field=field):
                    invalid = dict(entries, docs=dict(entries["docs"], **{field: value}))
                    lock.write_text(json.dumps(invalid))
                    with self.assertRaisesRegex(ValueError, message):
                        workspace.read_lock(root)
            del entries["docs"]
            lock.write_text(json.dumps(entries))
            with self.assertRaisesRegex(
                ValueError, "lock must contain engine, desktop and docs"
            ):
                workspace.read_lock(root)

    def test_lock_refuses_dirty_product_checkout(self):
        with patch("workspace.git", return_value=" M source.go"):
            with self.assertRaisesRegex(ValueError, "commit or stash engine"):
                workspace.current(Path("unused"), clean=True)

    def test_lock_refuses_dirty_docs_checkout(self):
        with patch(
            "workspace.git",
            side_effect=["", "a" * 40, "", "a" * 40, " M page.mdx"],
        ):
            with self.assertRaisesRegex(ValueError, "commit or stash docs"):
                workspace.current(Path("unused"), clean=True)

    def test_current_includes_docs_revision(self):
        with patch("workspace.git", return_value="a" * 40):
            entries = workspace.current(Path("unused"))
        self.assertEqual(set(entries), {"engine", "desktop", "docs"})
        self.assertEqual(
            entries["docs"],
            {"url": "https://github.com/knotra-dev/docs.git", "commit": "a" * 40},
        )

    def test_new_checkout_uses_locked_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = {
                name: {
                    "url": f"https://github.com/knotra-dev/{name}.git",
                    "commit": "a" * 40,
                }
                for name in workspace.NAMES
            }
            with patch("workspace.subprocess.run") as run:
                workspace.bootstrap(root, entries)
            self.assertEqual(run.call_count, len(entries) * 2)
            for index, (name, entry) in enumerate(entries.items()):
                with self.subTest(name=name):
                    self.assertEqual(
                        run.call_args_list[index * 2].args[0],
                        ["git", "clone", entry["url"], str(root / "repos" / name)],
                    )
                    self.assertEqual(
                        run.call_args_list[index * 2 + 1].args[0][-3:],
                        ["checkout", "--detach", entry["commit"]],
                    )


if __name__ == "__main__":
    unittest.main()
