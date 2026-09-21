"""Rebuildable local project snapshots. SQLite remains authoritative."""

import io
import json
import re
import shutil
import threading
import zipfile
from html import escape
from urllib.parse import urlsplit

from . import reports

LOCK = threading.RLock()


def project_path(store, job_id):
    if not re.fullmatch(r"[0-9a-f]{16}", job_id):
        raise KeyError(job_id)
    root = store.path.parent / "projects"
    path = root / job_id
    if root.is_symlink() or path.is_symlink():
        raise ValueError("Project archive cannot be a symbolic link")
    return path


def snapshot(store, job_id):
    detail = store.detail(job_id)
    with store.connect() as c:
        detail["events"] = [
            dict(r) for r in c.execute("SELECT * FROM events WHERE job_id=? ORDER BY id", (job_id,))
        ]
    return detail


def files(detail, lang):
    parts = []
    tags = {"title": "h1", "h1": "h2", "h2": "h3", "quote": "blockquote"}
    for kind, text in reports.blocks(detail, lang):
        safe = escape(str(text))
        if kind == "link" and urlsplit(str(text)).scheme in {"http", "https"}:
            parts.append(f'<p><a href="{safe}" rel="noreferrer">{safe}</a></p>')
        else:
            tag = tags.get(kind, "p")
            parts.append(f'<{tag} class="{kind}">{safe}</{tag}>')
    html = """<!doctype html><html lang="%s"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Locus · %s</title><style>body{max-width:850px;margin:60px auto;padding:0 24px;color:#24342e;background:#faf9f5;font:16px/1.7 system-ui}h1{font-size:40px;line-height:1.2}h2{margin-top:48px;border-top:1px solid #bbc6bf;padding-top:24px}h3{margin-top:30px}blockquote{border-left:3px solid #587764;margin:16px 0;padding:12px 22px;background:#eef1eb}a{color:#2c6551;overflow-wrap:anywhere}.note,.warning{padding:16px;background:#efe9da}.eyebrow{font-size:12px;letter-spacing:2px}.bullet{padding-left:18px}p,blockquote{white-space:pre-wrap;overflow-wrap:anywhere}@media print{body{margin:0;background:white}h2,h3{break-after:avoid}blockquote{break-inside:avoid}}</style><body>%s</body></html>""" % (
        lang,
        escape(detail["name"]),
        "\n".join(parts),
    )
    result = {
        "index.html": html.encode(),
        "research.json": json.dumps(
            detail | {"analysis": reports.analysis(detail)}, ensure_ascii=False, indent=2
        ).encode(),
        "report.md": reports.markdown(detail, lang).encode(),
        "README.txt": (
            "Locus public-source research archive\nOpen index.html in a browser. Sources contain recorded quotations and links, not full copies of websites.\nEvidence support is a rule-based aid, not an identity probability. Cards remain separate.\nresearch.json includes criteria revisions, prior assessments, activity and current findings.\nDeleting the project in Locus does not delete previously exported copies or migration backups.\n"
        ).encode(),
    }
    for source in detail["sources"]:
        if not re.fullmatch(r"[0-9a-f]{16}", source["id"]):
            continue
        quotes = list(
            dict.fromkeys(
                f["quote"]
                for c in detail["candidates"]
                if c["source_id"] == source["id"]
                for f in c["value"]["facts"]
            )
        )
        result[f"sources/{source['id']}.txt"] = (
            f"{source['title']}\n{source['url']}\nFetched: {source['fetched_at']}\nStatus: {source['status']}\n\n"
            + "\n\n".join(quotes)
        ).encode()
    return result


def write_files(path, entries):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name, content in entries.items():
        target = path / name
        if target.parent.is_symlink() or target.is_symlink():
            raise ValueError("Project archive cannot contain symbolic links")
        target.parent.mkdir(exist_ok=True, mode=0o700)
        temporary = target.with_suffix(target.suffix + ".tmp")
        if temporary.is_symlink():
            raise ValueError("Invalid archive temporary file")
        temporary.write_bytes(content)
        temporary.chmod(0o600)
        temporary.replace(target)


def sync(store, job_id):
    with LOCK:
        detail = snapshot(store, job_id)
        write_files(project_path(store, job_id), files(detail, detail["brief"]["output_language"]))


def export_zip(store, job_id, lang):
    with LOCK:
        detail = snapshot(store, job_id)
        entries = files(detail, lang)
        write_files(project_path(store, job_id), files(detail, detail["brief"]["output_language"]))
        entries["report.pdf"] = reports.pdf(detail, lang)
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, content in entries.items():
                archive.writestr(f"locus-{job_id}/{name}", content)
        return output.getvalue()


def delete(store, job_id):
    with LOCK:
        store.job(job_id)
        path = project_path(store, job_id)
        if path.exists():
            shutil.rmtree(path)
        with store.connect() as c:
            c.execute("DELETE FROM jobs WHERE id=?", (job_id,))
