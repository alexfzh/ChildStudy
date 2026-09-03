"""SQLite 数据库自动备份脚本（审计 P2#8）。

功能：WAL checkpoint(TRUNCATE) 合并写前日志回主库 → 拷贝到 data/backups/ → 仅保留最近 N 份。
用法：
    cd backend
    python scripts/backup_db.py            # 默认保留 7 份
    python scripts/backup_db.py --keep 14  # 保留 14 份
可作定时任务（cron / Windows 任务计划）每日执行。备份文件位于 data/backups/，已被 .gitignore 忽略。
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / "data" / "childstudy.db"
BACKUP_DIR = BACKEND_DIR / "data" / "backups"


def backup(keep: int = 7) -> Path | None:
    if not DB_PATH.exists():
        print(f"[skip] 数据库不存在：{DB_PATH}", file=sys.stderr)
        return None

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # 1) WAL checkpoint(TRUNCATE)：把 -wal 数据合并回主库文件，确保拷贝完整
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
    except Exception as exc:  # 即便 checkpoint 失败也继续拷贝（可能略有未落盘数据）
        print(f"[warn] WAL checkpoint 失败，继续拷贝：{exc}", file=sys.stderr)

    # 2) 拷贝主库
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = BACKUP_DIR / f"childstudy-{ts}.db"
    shutil.copy2(DB_PATH, dst)
    print(f"[ok] 已备份：{dst}")

    # 3) 清理旧备份，仅保留最近 keep 份
    files = sorted(
        BACKUP_DIR.glob("childstudy-*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in files[keep:]:
        old.unlink()
        print(f"[ok] 删除旧备份：{old}")

    return dst


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ChildStudy SQLite 备份")
    parser.add_argument("--keep", type=int, default=7, help="保留最近 N 份备份（默认 7）")
    args = parser.parse_args()
    backup(args.keep)
