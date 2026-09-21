import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .models import Brief, Settings


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def uid() -> str:
    return uuid4().hex[:16]


def dump(value) -> str:
    return json.dumps(value, ensure_ascii=False)


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = path
        with self.connect() as c:
            if c.execute("PRAGMA user_version").fetchone()[0] > 2:
                raise RuntimeError("Database was created by a newer version of Locus")
            if c.execute("PRAGMA user_version").fetchone()[0] == 1:
                backup = path.with_suffix(".v1.backup.sqlite3")
                if not backup.exists():
                    with sqlite3.connect(backup) as target:
                        c.backup(target)
                    backup.chmod(0o600)
            c.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, brief TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft', reason TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    active_seconds REAL NOT NULL DEFAULT 0, rounds INTEGER NOT NULL DEFAULT 0,
                    settings_snapshot TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL, key TEXT NOT NULL, payload TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'pending', error TEXT NOT NULL DEFAULT '',
                    UNIQUE(job_id, kind, key)
                );
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    url TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL, error TEXT NOT NULL DEFAULT '', fetched_at TEXT NOT NULL,
                    content_hash TEXT NOT NULL DEFAULT '', UNIQUE(job_id, url)
                );
                CREATE TABLE IF NOT EXISTS candidates (
                    id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
                    value TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'unreviewed'
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    at TEXT NOT NULL, level TEXT NOT NULL, message TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS tasks_job_state ON tasks(job_id,state);
                CREATE INDEX IF NOT EXISTS events_job ON events(job_id,id);
                CREATE TABLE IF NOT EXISTS search_runs (
                    id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    task_id TEXT NOT NULL, engine TEXT NOT NULL, status TEXT NOT NULL,
                    result_count INTEGER NOT NULL, seconds REAL NOT NULL, error TEXT NOT NULL,
                    at TEXT NOT NULL
                );
                PRAGMA user_version=2;
            """)
            c.execute("INSERT OR IGNORE INTO settings VALUES(1,?)", (dump(Settings().model_dump()),))
        path.chmod(0o600)

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.path, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        try:
            with c:
                yield c
        finally:
            c.close()

    def settings(self) -> Settings:
        with self.connect() as c:
            return Settings.model_validate_json(
                c.execute("SELECT value FROM settings WHERE id=1").fetchone()[0]
            )

    def save_settings(self, settings: Settings):
        with self.connect() as c:
            c.execute("UPDATE settings SET value=? WHERE id=1", (settings.model_dump_json(),))

    def create(self, brief: Brief) -> dict:
        job_id, stamp = uid(), now()
        with self.connect() as c:
            c.execute(
                "INSERT INTO jobs(id,name,brief,created_at,updated_at) VALUES(?,?,?,?,?)",
                (job_id, brief.name, brief.model_dump_json(), stamp, stamp),
            )
        self.event(job_id, "Поиск создан. Модель запускается только после нажатия «Начать».")
        return self.job(job_id)

    def job(self, job_id: str) -> dict:
        with self.connect() as c:
            row = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                raise KeyError(job_id)
            result = dict(row)
            result["brief"] = Brief.model_validate_json(result["brief"]).model_dump()
            result["settings_snapshot"] = json.loads(result["settings_snapshot"])
            result["stats"] = {
                "queries": c.execute(
                    "SELECT COUNT(*) FROM tasks WHERE job_id=? AND kind='search' AND state IN ('done','failed','running')",
                    (job_id,),
                ).fetchone()[0],
                "pages": c.execute(
                    "SELECT COUNT(*) FROM tasks WHERE job_id=? AND kind='fetch' AND state IN ('done','failed','running')",
                    (job_id,),
                ).fetchone()[0],
                "sources": c.execute(
                    "SELECT COUNT(*) FROM sources WHERE job_id=? AND status='read'", (job_id,)
                ).fetchone()[0],
                "candidates": c.execute(
                    "SELECT COUNT(*) FROM candidates WHERE job_id=?", (job_id,)
                ).fetchone()[0],
            }
            return result

    def jobs(self) -> list[dict]:
        with self.connect() as c:
            ids = [r[0] for r in c.execute("SELECT id FROM jobs ORDER BY created_at DESC")]
        return [self.job(i) for i in ids]

    def update(self, job_id: str, **values):
        allowed = {"brief", "status", "reason", "active_seconds", "rounds", "settings_snapshot"}
        if not set(values).issubset(allowed):
            raise ValueError("Invalid job fields")
        values["updated_at"] = now()
        with self.connect() as c:
            c.execute(
                f"UPDATE jobs SET {','.join(k + '=?' for k in values)} WHERE id=?", (*values.values(), job_id)
            )

    def event(self, job_id: str, message: str, level: str = "info"):
        with self.connect() as c:
            c.execute(
                "INSERT INTO events(job_id,at,level,message) VALUES(?,?,?,?)",
                (job_id, now(), level, message[:2000]),
            )

    def enqueue(self, job_id: str, kind: str, key: str, payload: dict) -> bool:
        with self.connect() as c:
            return bool(
                c.execute(
                    "INSERT OR IGNORE INTO tasks(id,job_id,kind,key,payload) VALUES(?,?,?,?,?)",
                    (uid(), job_id, kind, key, dump(payload)),
                ).rowcount
            )

    def task(self, job_id: str, kind: str | None = None) -> dict | None:
        with self.connect() as c:
            sql = "SELECT * FROM tasks WHERE job_id=? AND state='pending'"
            args = [job_id]
            if kind:
                sql += " AND kind=?"
                args.append(kind)
            row = c.execute(sql + " ORDER BY rowid LIMIT 1", args).fetchone()
            if not row:
                return None
            c.execute("UPDATE tasks SET state='running' WHERE id=?", (row["id"],))
            result = dict(row)
            result["payload"] = json.loads(result["payload"])
            return result

    def finish_task(self, task_id: str, state: str = "done", error: str = ""):
        with self.connect() as c:
            c.execute("UPDATE tasks SET state=?,error=? WHERE id=?", (state, error[:1000], task_id))

    def detail(self, job_id: str) -> dict:
        result = self.job(job_id)
        with self.connect() as c:
            result["sources"] = [
                dict(r)
                for r in c.execute(
                    "SELECT id,url,title,status,error,fetched_at,content_hash FROM sources WHERE job_id=? ORDER BY rowid DESC",
                    (job_id,),
                )
            ]
            result["candidates"] = [
                dict(r) | {"value": json.loads(r["value"])}
                for r in c.execute("SELECT * FROM candidates WHERE job_id=? ORDER BY rowid", (job_id,))
            ]
            result["events"] = [
                dict(r)
                for r in c.execute(
                    "SELECT * FROM events WHERE job_id=? ORDER BY id DESC LIMIT 150", (job_id,)
                )
            ]
            result["queries"] = [
                dict(r) | {"payload": json.loads(r["payload"])}
                for r in c.execute(
                    "SELECT * FROM tasks WHERE job_id=? AND kind='search' ORDER BY rowid", (job_id,)
                )
            ]
            result["search_runs"] = [
                dict(r) for r in c.execute("SELECT * FROM search_runs WHERE job_id=? ORDER BY at", (job_id,))
            ]
        return result

    def record_search(self, job_id, task_id, attempts):
        with self.connect() as c:
            for a in attempts:
                c.execute(
                    "INSERT INTO search_runs VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        uid(),
                        job_id,
                        task_id,
                        a["engine"],
                        a["status"],
                        a["result_count"],
                        a["seconds"],
                        a.get("error", ""),
                        a["at"],
                    ),
                )

    def recover(self):
        with self.connect() as c:
            running = [r[0] for r in c.execute("SELECT id FROM jobs WHERE status IN ('running','queued')")]
            c.execute(
                "UPDATE jobs SET status='paused',reason='Приложение было закрыто. Можно продолжить.' WHERE status IN ('running','queued')"
            )
            c.execute("UPDATE tasks SET state='pending' WHERE state='running'")
        for job_id in running:
            self.event(job_id, "Прогресс восстановлен. Автоматический запуск модели отключён.")
