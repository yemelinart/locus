import json
import math
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
            if c.execute("PRAGMA user_version").fetchone()[0] > 5:
                raise RuntimeError("Database was created by a newer version of Locus")
            version = c.execute("PRAGMA user_version").fetchone()[0]
            if version in {1, 2, 3, 4}:
                backup = path.with_suffix(f".v{version}.backup.sqlite3")
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
                CREATE TABLE IF NOT EXISTS candidate_audits (
                    candidate_id TEXT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
                    revision INTEGER NOT NULL, value TEXT NOT NULL, model TEXT NOT NULL, at TEXT NOT NULL,
                    PRIMARY KEY(candidate_id, revision)
                );
                CREATE TABLE IF NOT EXISTS link_decisions (
                    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    left_id TEXT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
                    right_id TEXT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
                    revision INTEGER NOT NULL, status TEXT NOT NULL, at TEXT NOT NULL,
                    PRIMARY KEY(job_id,left_id,right_id)
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
                CREATE TABLE IF NOT EXISTS revisions (
                    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    number INTEGER NOT NULL, at TEXT NOT NULL, brief TEXT NOT NULL,
                    previous_assessments TEXT NOT NULL DEFAULT '[]',
                    PRIMARY KEY(job_id, number)
                );
            """)
            for table, column, definition in [
                ("sources", "links", "TEXT NOT NULL DEFAULT '[]'"),
                ("sources", "url_aliases", "TEXT NOT NULL DEFAULT '[]'"),
                ("jobs", "activity", "TEXT NOT NULL DEFAULT '{}'"),
                ("jobs", "revision", "INTEGER NOT NULL DEFAULT 1"),
                ("candidates", "review_revision", "INTEGER NOT NULL DEFAULT 1"),
                ("tasks", "revision", "INTEGER NOT NULL DEFAULT 1"),
            ]:
                if column not in {r[1] for r in c.execute(f"PRAGMA table_info({table})")}:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            c.execute(
                "INSERT OR IGNORE INTO revisions(job_id,number,at,brief) SELECT id,1,created_at,brief FROM jobs"
            )
            c.execute("PRAGMA user_version=5")
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
        with self.connect() as c:
            c.execute(
                "INSERT INTO revisions(job_id,number,at,brief) VALUES(?,1,?,?)",
                (job_id, stamp, brief.model_dump_json()),
            )
        self.event(job_id, "Поиск создан. Модель запускается только после нажатия «Начать».")
        return self.job(job_id)

    def job(self, job_id: str) -> dict:
        with self.connect() as c:
            row = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                raise KeyError(job_id)
            result = dict(row)
            result["activity"] = json.loads(result["activity"])
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
        allowed = {
            "brief",
            "status",
            "reason",
            "active_seconds",
            "rounds",
            "settings_snapshot",
            "revision",
            "activity",
        }
        if not set(values).issubset(allowed):
            raise ValueError("Invalid job fields")
        values["updated_at"] = now()
        with self.connect() as c:
            c.execute(
                f"UPDATE jobs SET {','.join(k + '=?' for k in values)} WHERE id=?", (*values.values(), job_id)
            )

    def activity(self, job_id, phase, target="", url=""):
        self.update(job_id, activity=dump({"phase": phase, "target": target[:500], "url": url, "at": now()}))

    def save_audit(self, candidate_id, revision, value, model):
        with self.connect() as c:
            c.execute(
                "INSERT OR REPLACE INTO candidate_audits VALUES(?,?,?,?,?)",
                (candidate_id, revision, dump(value), model, now()),
            )

    def event(self, job_id: str, message: str, level: str = "info"):
        with self.connect() as c:
            c.execute(
                "INSERT INTO events(job_id,at,level,message) VALUES(?,?,?,?)",
                (job_id, now(), level, message[:2000]),
            )
        self.sync_archive(job_id)

    def sync_archive(self, job_id):
        from .archive import sync

        try:
            sync(self, job_id)
        except (OSError, ValueError):
            # A rebuildable folder must not stop the durable research worker.
            message = "Local archive could not be updated. Database findings are preserved; check folder permissions before exporting."
            with self.connect() as c:
                latest = c.execute(
                    "SELECT message FROM events WHERE job_id=? AND level='warning' ORDER BY id DESC LIMIT 1",
                    (job_id,),
                ).fetchone()
                if not latest or latest[0] != message:
                    c.execute(
                        "INSERT INTO events(job_id,at,level,message) VALUES(?,?,'warning',?)",
                        (job_id, now(), message),
                    )

    def continue_research(self, job_id, brief, additional_budget=None):
        from .models import Budget

        previous = self.detail(job_id)
        if previous["status"] in {"running", "queued"}:
            raise ValueError("Pause research before changing criteria")
        if additional_budget:
            brief.budget = Budget(
                minutes=math.ceil(previous["active_seconds"] / 60) + additional_budget.minutes,
                queries=previous["stats"]["queries"] + additional_budget.queries,
                pages=previous["stats"]["pages"] + additional_budget.pages,
                rounds=previous["rounds"] + additional_budget.rounds,
            )
        revision = previous["revision"] + 1
        stamp = now()
        with self.connect() as c:
            c.execute(
                "UPDATE jobs SET name=?,brief=?,revision=?,status='paused',reason=?,updated_at=? WHERE id=?",
                (
                    brief.name,
                    brief.model_dump_json(),
                    revision,
                    "Criteria updated. Ready to continue.",
                    stamp,
                    job_id,
                ),
            )
            c.execute(
                "INSERT INTO revisions VALUES(?,?,?,?,?)",
                (
                    job_id,
                    revision,
                    stamp,
                    brief.model_dump_json(),
                    dump(
                        [
                            {"id": x["id"], "status": x["status"], "assessment": x["assessment"]}
                            for x in previous["candidates"]
                        ]
                    ),
                ),
            )
            c.execute(
                "UPDATE tasks SET state='superseded',error='Superseded by updated criteria' WHERE job_id=? AND state='pending'",
                (job_id,),
            )
        self.event(
            job_id,
            f"Критерии сохранены: версия {revision}. Прежние находки сохранены, обоснованность пересчитана.",
        )
        return self.detail(job_id)

    def enqueue(self, job_id: str, kind: str, key: str, payload: dict) -> bool:
        with self.connect() as c:
            revision = c.execute("SELECT revision FROM jobs WHERE id=?", (job_id,)).fetchone()[0]
            if kind == "review":
                from .verification import AUDIT_METHOD

                key = AUDIT_METHOD + ":" + key
            if kind in {"search", "review", "analyze"}:
                key = f"r{revision}:" + key
            inserted = c.execute(
                "INSERT OR IGNORE INTO tasks(id,job_id,kind,key,payload,revision) VALUES(?,?,?,?,?,?)",
                (uid(), job_id, kind, key, dump(payload), revision),
            ).rowcount
            if not inserted:
                inserted = c.execute(
                    "UPDATE tasks SET state='pending',error='',payload=?,revision=? WHERE job_id=? AND kind=? AND key=? AND state='superseded'",
                    (dump(payload), revision, job_id, kind, key),
                ).rowcount
            return bool(inserted)

    def task(self, job_id: str, kind: str | None = None) -> dict | None:
        with self.connect() as c:
            sql = "SELECT * FROM tasks WHERE job_id=? AND state='pending'"
            args = [job_id]
            if kind:
                sql += " AND kind=?"
                args.append(kind)
            order = (
                "COALESCE(json_extract(payload,'$.priority'),0) DESC, rowid" if kind == "fetch" else "rowid"
            )
            if kind == "fetch":
                from urllib.parse import urlsplit

                counts = {}
                for source in c.execute("SELECT url FROM sources WHERE job_id=?", (job_id,)):
                    host = urlsplit(source["url"]).hostname
                    counts[host] = counts.get(host, 0) + 1
                pending = c.execute(sql + " ORDER BY " + order + " LIMIT 1000", args).fetchall()

                def priority(row):
                    payload = json.loads(row["payload"])
                    return payload.get("priority", 0) - 5 * counts.get(
                        urlsplit(payload.get("url", "")).hostname, 0
                    )

                row = max(pending, key=priority) if pending else None
            else:
                row = c.execute(sql + " ORDER BY " + order + " LIMIT 1", args).fetchone()
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
                    "SELECT id,url,title,status,error,fetched_at,content_hash,links,url_aliases FROM sources WHERE job_id=? ORDER BY rowid DESC",
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
            result["revisions"] = [
                dict(r)
                | {
                    "brief": json.loads(r["brief"]),
                    "previous_assessments": json.loads(r["previous_assessments"]),
                }
                for r in c.execute("SELECT * FROM revisions WHERE job_id=? ORDER BY number DESC", (job_id,))
            ]
            audits = {}
            for row in c.execute(
                "SELECT a.* FROM candidate_audits a JOIN candidates x ON x.id=a.candidate_id WHERE x.job_id=? ORDER BY a.revision",
                (job_id,),
            ):
                audits[row["candidate_id"]] = json.loads(row["value"]) | {
                    "revision": row["revision"],
                    "model": row["model"],
                    "at": row["at"],
                }
        from .evidence import assess, conclusion
        from .linkage import build_linkage

        for source in result["sources"]:
            source["links"] = json.loads(source["links"])
            source["url_aliases"] = json.loads(source["url_aliases"])
        with self.connect() as c:
            decisions = [dict(r) for r in c.execute("SELECT * FROM link_decisions WHERE job_id=?", (job_id,))]

        sources = {s["id"]: s for s in result["sources"]}
        for candidate in result["candidates"]:
            candidate["verification"] = audits.get(candidate["id"])
            candidate["assessment"] = assess(
                candidate, sources.get(candidate["source_id"], {}), result["brief"], result["revision"]
            )
        result["linkage"] = build_linkage(result, decisions)
        result["conclusion"] = conclusion(result)
        return result

    def review_link(self, job_id, left_id, right_id, status):
        detail = self.detail(job_id)
        if detail["status"] in {"running", "queued"}:
            raise ValueError("Pause research before linking records")
        left_id, right_id = sorted((left_id, right_id))
        if not any(
            p["left_id"] == left_id and p["right_id"] == right_id for p in detail["linkage"]["proposals"]
        ):
            raise ValueError("No current source-backed link proposal for these records")
        if status not in {"confirmed", "rejected", "unreviewed"}:
            raise ValueError("Invalid link decision")
        with self.connect() as c:
            c.execute(
                "INSERT OR REPLACE INTO link_decisions VALUES(?,?,?,?,?,?)",
                (job_id, left_id, right_id, detail["revision"], status, now()),
            )
        self.event(job_id, "User reviewed a source link: " + status)
        return self.detail(job_id)

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
