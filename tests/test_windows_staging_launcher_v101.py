"""Ensure the Windows staging launcher does not silently fall back to Python 3.9."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class WindowsLauncherSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / "iniciar_staging_windows.bat").read_text(encoding="utf-8")

    def test_python_version_explicit(self):
        self.assertIn("3.12 3.11 3.13", self.text)
        self.assertIn("64 bits", self.text)
        self.assertNotIn('py -3 -m pip install', self.text)

    def test_virtual_environment_isolated(self):
        self.assertIn("-m venv", self.text)
        self.assertIn(".venv-staging-", self.text)
        self.assertIn("%VENV_PY%", self.text)

    def test_binary_only_install(self):
        self.assertIn("--only-binary=:all:", self.text)
        self.assertIn("cloud\\requirements.txt", self.text)

    def test_no_data_deletion(self):
        self.assertNotIn("rmdir", self.text.lower())
        self.assertNotIn("runtime\\staging.sqlite3", self.text.lower())

if __name__ == "__main__":
    unittest.main()
