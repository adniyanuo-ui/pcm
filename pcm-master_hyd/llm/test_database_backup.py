import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.test import SimpleTestCase

from llm.management.commands.backup_sqlite_database import backup_sqlite_database


class SqliteBackupTests(SimpleTestCase):
    def test_creates_consistent_copy_and_rotates_only_managed_backups(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "db.sqlite3"
            backups = root / "backups"
            with sqlite3.connect(source) as connection:
                connection.execute("CREATE TABLE patient (id INTEGER PRIMARY KEY, name TEXT)")
                connection.execute("INSERT INTO patient(name) VALUES ('虚构患者')")

            start = datetime(2026, 9, 7, tzinfo=timezone.utc)
            unrelated = backups / "manual-export.sqlite3"
            backups.mkdir()
            unrelated.write_text("保留", encoding="utf-8")
            for offset in range(3):
                backup_sqlite_database(
                    source,
                    backups,
                    keep=2,
                    timestamp=start + timedelta(seconds=offset),
                )

            managed = sorted(backups.glob("db-before-migrate-*.sqlite3"))
            self.assertEqual(len(managed), 2)
            self.assertTrue(unrelated.is_file())
            with sqlite3.connect(managed[-1]) as connection:
                self.assertEqual(
                    connection.execute("SELECT name FROM patient").fetchone()[0],
                    "虚构患者",
                )
            self.assertEqual(oct(managed[-1].stat().st_mode & 0o777), "0o600")

    def test_missing_database_is_first_deploy_noop(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertIsNone(
                backup_sqlite_database(root / "missing.sqlite3", root / "backups")
            )
            self.assertFalse((root / "backups").exists())

    def test_rejects_unsafe_retention_value(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "db.sqlite3"
            source.touch()
            with self.assertRaisesRegex(ValueError, "1—50"):
                backup_sqlite_database(source, root / "backups", keep=0)
