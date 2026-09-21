import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .db import Store, dump
from .engine import Engine, friendly_error
from .models import Brief, Budget, Refinement, Review, Settings
from .providers.local_model import LocalModel

ROOT = Path(__file__).resolve().parents[2]


def create_app(data_dir: Path | None = None, run_worker: bool = True) -> FastAPI:
    folder = data_dir or Path(os.environ.get("LOCUS_DATA_DIR", ROOT / "data"))
    store = Store(folder / "locus.sqlite3")
    engine = Engine(store)

    @asynccontextmanager
    async def lifespan(app):
        if run_worker:
            engine.start()
        yield
        if run_worker:
            await engine.close()

    app = FastAPI(
        title="Locus Local",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.store, app.state.engine = store, engine

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        host = request.url.hostname
        allowed_hosts = {"127.0.0.1", "localhost", "::1"} | ({"testserver"} if not run_worker else set())
        if host not in allowed_hosts:
            return JSONResponse({"detail": "Locus доступен только локально"}, status_code=403)
        origin = request.headers.get("origin")
        allowed_ports = {8420, 5173, int(os.environ.get("LOCUS_PORT", "8420"))}
        if origin:
            p = urlsplit(origin)
            if (
                p.scheme != "http"
                or p.hostname not in {"127.0.0.1", "localhost", "::1"}
                or p.port not in allowed_ports
            ):
                return JSONResponse({"detail": "Внешний сайт не может обращаться к Locus"}, status_code=403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": "Запрос с внешнего сайта отклонён"}, status_code=403)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            if request.headers.get("x-locus-request") != "1":
                return JSONResponse({"detail": "Нет заголовка локального приложения"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        if not request.url.path.startswith("/api/docs"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
            )
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(KeyError)
    async def missing(_, __):
        return JSONResponse({"detail": "Поиск или источник не найден"}, status_code=404)

    @app.get("/api/health")
    async def health():
        return {"app": "locus", "status": "ok", "version": __version__, "local_only": True}

    @app.get("/api/settings")
    async def get_settings():
        return store.settings()

    @app.put("/api/settings")
    async def save_settings(settings: Settings):
        store.save_settings(settings)
        return settings

    @app.get("/api/models")
    async def models():
        return await probe_models(store.settings())

    @app.post("/api/models/probe")
    async def probe_models(settings: Settings):
        try:
            return {"connected": True, "models": await LocalModel(settings).models(), "error": ""}
        except Exception as exc:
            return {"connected": False, "models": [], "error": friendly_error(exc)}

    @app.get("/api/jobs")
    async def jobs():
        return store.jobs()

    @app.post("/api/jobs", status_code=201)
    async def create(brief: Brief):
        return store.create(brief)

    @app.get("/api/jobs/{job_id}")
    async def detail(job_id: str):
        return store.detail(job_id)

    @app.post("/api/jobs/{job_id}/start")
    async def start(job_id: str):
        job = store.job(job_id)
        if job["status"] in {"running", "queued"}:
            return job
        if not store.settings().model:
            raise HTTPException(409, "Сначала выберите локальную модель в настройках")
        store.update(job_id, status="queued", reason="Ожидает свободную локальную модель")
        store.event(job_id, "Поиск добавлен в очередь.")
        return store.job(job_id)

    @app.post("/api/jobs/{job_id}/pause")
    async def pause(job_id: str):
        await engine.pause(job_id)
        return store.job(job_id)

    def editable(job_id):
        job = store.job(job_id)
        if job["status"] in {"running", "queued"}:
            raise HTTPException(409, "Сначала приостановите поиск")
        return job

    @app.put("/api/jobs/{job_id}/budget")
    async def budget(job_id: str, budget: Budget):
        job = editable(job_id)
        brief = Brief.model_validate(job["brief"])
        brief.budget = budget
        store.update(job_id, brief=brief.model_dump_json())
        store.event(job_id, "Бюджет обновлён. Отсчёт учитывает уже выполненную работу.")
        return store.job(job_id)

    @app.post("/api/jobs/{job_id}/refine")
    async def refine(job_id: str, refinement: Refinement):
        job = editable(job_id)
        brief = Brief.model_validate(job["brief"])
        new_context = (brief.context + "\nУточнение пользователя: " + refinement.text).strip()
        if len(new_context) > 6000:
            raise HTTPException(422, "Суммарный контекст превышает 6000 символов")
        brief.context = new_context
        store.update(job_id, brief=brief.model_dump_json(), status="paused", reason="Добавлены уточнения")
        store.event(job_id, "Добавлены новые ориентиры пользователя. Они будут учтены в следующих шагах.")
        return store.job(job_id)

    @app.post("/api/jobs/{job_id}/candidates/{candidate_id}/review")
    async def review(job_id: str, candidate_id: str, review: Review):
        store.job(job_id)
        with store.connect() as c:
            result = c.execute(
                "UPDATE candidates SET status=? WHERE id=? AND job_id=?",
                (review.status, candidate_id, job_id),
            )
            if not result.rowcount:
                raise HTTPException(404, "Кандидат не найден")
        store.event(
            job_id,
            "Пользователь изменил оценку совпадения: "
            + {"confirmed": "подтверждено", "rejected": "отклонено", "unreviewed": "не проверено"}[
                review.status
            ],
        )
        return {"ok": True}

    @app.get("/api/jobs/{job_id}/export")
    async def export(job_id: str, format: str = "md"):
        detail = store.detail(job_id)
        if format == "json":
            return PlainTextResponse(
                dump(detail),
                media_type="application/json",
                headers={"Content-Disposition": f'attachment; filename="locus-{job_id}.json"'},
            )
        source_map = {s["id"]: s for s in detail["sources"]}
        lines = [
            f"# Locus — {detail['name']}",
            "",
            "Исследование публичных источников. Совпадения требуют проверки человеком.",
            "Наличие цитаты не доказывает личность или истинность утверждения.",
            "",
            f"Статус: {detail['status']}. {detail['reason']}",
            "",
        ]
        for candidate in detail["candidates"]:
            value = candidate["value"]
            source = source_map[candidate["source_id"]]
            lines += [
                f"## {value['name']}",
                value["description"],
                f"Оценка пользователя: {candidate['status']}",
                "",
            ]
            for fact in value["facts"]:
                lines += [f"- {fact['statement']}", f"> {fact['quote']}", ""]
            lines += [f"Источник: {source['url']}", f"Проверен: {source['fetched_at']}", ""]
        lines += [
            "## Проверенные адреса",
            *[f"- {s['url']} — {s['status']} {s['error']}" for s in detail["sources"]],
        ]
        return PlainTextResponse(
            "\n".join(lines),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="locus-{job_id}.md"'},
        )

    @app.delete("/api/jobs/{job_id}")
    async def delete(job_id: str):
        editable(job_id)
        with store.connect() as c:
            c.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        return {"ok": True}

    dist = ROOT / "frontend" / "dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/")
    async def index():
        if (dist / "index.html").exists():
            return FileResponse(dist / "index.html")
        return PlainTextResponse(
            "Сначала соберите интерфейс: cd frontend && npm ci && npm run build", status_code=503
        )

    @app.get("/favicon.svg")
    async def favicon():
        return FileResponse(ROOT / "frontend" / "public" / "favicon.svg", media_type="image/svg+xml")

    return app
