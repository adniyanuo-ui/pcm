"""在迁移前为试用环境创建一致性的 SQLite 数据库副本。"""
from __future__ import annotations

import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


BACKUP_PREFIX = "db-before-migrate-"


def backup_sqlite_database(
    source_path: Path,
    output_dir: Path,
    *,
    keep: int = 7,
    timestamp: datetime | None = None,
) -> Path | None:
    """使用 SQLite backup API 生成一致性副本，并仅轮换本命令生成的旧文件。"""
    source_path = Path(source_path).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    if not 1 <= keep <= 50:
        raise ValueError("保留份数必须在 1—50 之间")
    if not source_path.is_file():
        return None

    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output_dir, 0o700)
    moment = timestamp or datetime.now(timezone.utc)
    filename = f"{BACKUP_PREFIX}{moment.strftime('%Y%m%dT%H%M%S%fZ')}.sqlite3"
    destination = output_dir / filename

    handle = tempfile.NamedTemporaryFile(
        prefix=f".{filename}.", suffix=".tmp", dir=output_dir, delete=False
    )
    temporary_path = Path(handle.name)
    handle.close()
    try:
        source_uri = f"file:{source_path.as_posix()}?mode=ro"
        with sqlite3.connect(source_uri, uri=True) as source:
            with sqlite3.connect(temporary_path) as target:
                source.backup(target)
                integrity = target.execute("PRAGMA integrity_check").fetchone()[0]
                if integrity != "ok":
                    raise RuntimeError(f"SQLite 备份完整性检查失败：{integrity}")
        os.chmod(temporary_path, 0o600)
        temporary_path.replace(destination)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    backups = sorted(output_dir.glob(f"{BACKUP_PREFIX}*.sqlite3"), reverse=True)
    for old_backup in backups[keep:]:
        old_backup.unlink()
    return destination


class Command(BaseCommand):
    help = "在数据库迁移前创建 SQLite 一致性备份"

    def add_arguments(self, parser):
        parser.add_argument("--output-dir", type=Path)
        parser.add_argument("--keep", type=int, default=7)

    def handle(self, *args, **options):
        database = settings.DATABASES["default"]
        if database.get("ENGINE") != "django.db.backends.sqlite3":
            raise CommandError("当前默认数据库不是 SQLite，拒绝使用此备份命令")
        source_path = Path(database["NAME"])
        output_dir = options["output_dir"] or source_path.parent / "backups"
        try:
            backup_path = backup_sqlite_database(
                source_path, output_dir, keep=options["keep"]
            )
        except (OSError, sqlite3.Error, RuntimeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        if backup_path is None:
            self.stdout.write("SQLite 数据库尚不存在，按首次部署继续")
        else:
            self.stdout.write(self.style.SUCCESS(f"SQLite 迁移前备份完成：{backup_path}"))
