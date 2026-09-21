import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from . import __version__, archive, reports
from .db import Store, dump
from .engine import Engine, friendly_error
from .models import Brief, Budget, Continuation, Query, Refinement, Review, Settings
from .names import variants
from .providers.local_model import LocalModel
from .providers.search import Search, catalog

ROOT = Path(__file__).resolve().parents[2]


def create_app(data_dir: Path | None = None, run_worker: bool = True) -> FastAPI:
    folder = data_dir or Path(os.environ.get("LOCUS_DATA_DIR", ROOT / "data"))
    store = Store(folder / "locus.sqlite3")
    engine = Engine(store)

    @asynccontextmanager
    async def lifespan(app):
        for job in store.jobs():
            store.sync_archive(job["id"])
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
            model = LocalModel(settings)
            ids = await model.models()
            capabilities, capability_error = [], ""
            try:
                capabilities = await model.capabilities()
            except Exception:
                capability_error = (
                    "Cannot verify this Ollama model. Select a downloaded chat model and refresh; inference requires successful local model verification."
                    if settings.model_provider == "ollama"
                    else "Model capability discovery is unavailable on this server. Standard local chat remains available."
                )
            return {
                "connected": True,
                "models": ids,
                "error": "",
                "capabilities": capabilities,
                "capability_error": capability_error,
                "excluded_models": model.ollama.excluded_models if model.ollama else 0,
            }
        except Exception as exc:
            return {"connected": False, "models": [], "error": friendly_error(exc)}

    @app.post("/api/names/preview")
    async def name_preview(brief: Brief):
        return {"variants": variants(brief)}

    @app.get("/api/search/catalog")
    async def search_catalog():
        return catalog()

    @app.post("/api/search/probe")
    async def search_probe(settings: Settings):
        engines = (
            ["searxng"]
            if settings.search_provider == "searxng"
            else list(dict.fromkeys(settings.search_backends))
        )
        installed = {e["id"] for e in catalog() if e["available"]}
        gate = asyncio.Semaphore(2)

        async def check(engine):
            if engine != "searxng" and engine not in installed:
                return {"engine": engine, "status": "unavailable", "error": "Adapter is not installed"}
            async with gate:
                search = Search(
                    settings.model_copy(
                        update={
                            "search_backends": [engine] if engine != "searxng" else settings.search_backends,
                            "results_per_query": 1,
                            "request_timeout": 8,
                        }
                    )
                )
                try:
                    await search.search(
                        Query(query="Python programming language official", language="en"),
                        Brief(name="Connection test"),
                    )
                except Exception:
                    pass
                return search.last_audit[-1] if search.last_audit else {"engine": engine, "status": "failed"}

        return await asyncio.gather(*(check(e) for e in engines))

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
        store.continue_research(job_id, brief)
        return store.job(job_id)

    @app.post("/api/jobs/{job_id}/continue")
    async def continue_research(job_id: str, request: Continuation):
        editable(job_id)
        if request.start and not store.settings().model:
            raise HTTPException(409, "Сначала выберите локальную модель в настройках")
        try:
            store.continue_research(job_id, request.brief, request.additional_budget)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        if request.start:
            await start(job_id)
        return store.detail(job_id)

    @app.post("/api/jobs/{job_id}/candidates/{candidate_id}/review")
    async def review(job_id: str, candidate_id: str, review: Review):
        job = store.job(job_id)
        with store.connect() as c:
            result = c.execute(
                "UPDATE candidates SET status=?,review_revision=? WHERE id=? AND job_id=?",
                (review.status, job["revision"], candidate_id, job_id),
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

    @app.get("/api/jobs/{job_id}/analysis")
    async def job_analysis(job_id: str):
        return reports.analysis(store.detail(job_id))

    @app.get("/api/jobs/{job_id}/export")
    async def export(
        job_id: str, format: Literal["md", "json", "pdf", "zip"] = "md", lang: Literal["en", "ru"] = "en"
    ):
        detail = store.detail(job_id)
        headers = {"Content-Disposition": f'attachment; filename="locus-{job_id}.{format}"'}
        if format == "zip":
            try:
                content = await run_in_threadpool(archive.export_zip, store, job_id, lang)
            except (OSError, ValueError) as exc:
                raise HTTPException(
                    409,
                    "Cannot update the local archive. Check project folder permissions and symbolic links.",
                ) from exc
            return Response(content, media_type="application/zip", headers=headers)
        if format == "json":
            return PlainTextResponse(
                dump(detail | {"analysis": reports.analysis(detail)}),
                media_type="application/json",
                headers=headers,
            )
        if format == "pdf":
            content = await run_in_threadpool(reports.pdf, detail, lang)
            return Response(content, media_type="application/pdf", headers=headers)
        return PlainTextResponse(reports.markdown(detail, lang), media_type="text/markdown", headers=headers)

    @app.delete("/api/jobs/{job_id}")
    async def delete(job_id: str):
        editable(job_id)
        try:
            await run_in_threadpool(archive.delete, store, job_id)
        except (OSError, ValueError) as exc:
            raise HTTPException(
                409,
                "Cannot delete the project folder. Database findings are preserved; check folder permissions and symbolic links.",
            ) from exc
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
