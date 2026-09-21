import asyncio
import hashlib
import ipaddress
import re
import socket
import time
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import aiohttp
from aiohttp.abc import AbstractResolver
from bs4 import BeautifulSoup

USER_AGENT = "LocusResearch/0.1 (+local public-source research; respects robots.txt)"
MAX_BODY = 2 * 1024 * 1024


def validate_url(url: str) -> str:
    if len(url) > 4000:
        raise ValueError("Слишком длинный адрес")
    p = urlsplit(url.strip())
    host = p.hostname
    if p.scheme not in {"http", "https"} or not host or p.username or p.password:
        raise ValueError("Нужна публичная ссылка http:// или https:// без логина и пароля")
    if p.port not in {None, 80, 443}:
        raise ValueError("Нестандартный порт источника запрещён")
    if host.lower().rstrip(".") in {"localhost", "localhost.localdomain"} or host.endswith(
        (".local", ".internal", ".localhost")
    ):
        raise ValueError("Локальные адреса не могут быть веб-источниками")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if "." not in host:
            raise ValueError("Нужен публичный домен") from None
    else:
        if not address.is_global:
            raise ValueError("Внутренние адреса не могут быть веб-источниками")
    host = host.encode("idna").decode("ascii").lower()
    netloc = f"[{host}]" if ":" in host else host
    if p.port:
        netloc += f":{p.port}"
    return urlunsplit((p.scheme, netloc, p.path or "/", p.query, ""))


def canonical_url(url: str) -> str:
    p = urlsplit(validate_url(url))
    query = urlencode(
        [
            (k, v)
            for k, v in parse_qsl(p.query, keep_blank_values=True)
            if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}
        ]
    )
    return urlunsplit((p.scheme, p.netloc, p.path, query, ""))


def domain_allowed(url: str, include: list[str], exclude: list[str]) -> bool:
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")

    def matches(domain):
        return host == domain or host.endswith("." + domain)

    return not any(map(matches, exclude)) and (not include or any(map(matches, include)))


class PublicResolver(AbstractResolver):
    """Resolve once, validate every result, and give the pinned addresses to aiohttp."""

    async def resolve(self, host, port=0, family=socket.AF_INET):
        results = await asyncio.get_running_loop().getaddrinfo(
            host, port, type=socket.SOCK_STREAM, family=family
        )
        addresses = []
        for af, _, proto, _, address in results:
            ip = address[0]
            if not ipaddress.ip_address(ip).is_global:
                raise ValueError("Источник разрешился во внутренний IP-адрес")
            addresses.append(
                {
                    "hostname": host,
                    "host": ip,
                    "port": port,
                    "family": af,
                    "proto": proto,
                    "flags": socket.AI_NUMERICHOST,
                }
            )
        if not addresses:
            raise ValueError("Не удалось определить адрес источника")
        return addresses

    async def close(self):
        pass


class Reader:
    def __init__(self, timeout: int = 20, delay: float = 1.5):
        self.timeout, self.delay = timeout, delay
        self.last_request: dict[str, float] = {}
        self.robots: dict[str, RobotFileParser] = {}

    async def _get(self, url: str, include: list[str], exclude: list[str], check_robots: bool = False):
        connector = aiohttp.TCPConnector(resolver=PublicResolver(), use_dns_cache=False)
        async with aiohttp.ClientSession(
            connector=connector,
            trust_env=False,
            cookie_jar=aiohttp.DummyCookieJar(),
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9"},
            timeout=aiohttp.ClientTimeout(total=self.timeout),
        ) as session:
            for _ in range(5):
                url = validate_url(url)
                if not domain_allowed(url, include, exclude):
                    raise ValueError("Источник исключён фильтром доменов")
                if check_robots:
                    await self._allow(url, include, exclude)
                host = urlsplit(url).netloc
                robot = self.robots.get(f"{urlsplit(url).scheme}://{host}")
                delay = max(self.delay, (robot.crawl_delay("LocusResearch") or 0) if robot else 0)
                wait = delay - (time.monotonic() - self.last_request.get(host, 0))
                if wait > 0:
                    await asyncio.sleep(wait)
                self.last_request[host] = time.monotonic()
                async with session.get(url, allow_redirects=False) as response:
                    if response.status in {301, 302, 303, 307, 308}:
                        url = urljoin(url, response.headers.get("Location", ""))
                        continue
                    data = bytearray()
                    async for chunk in response.content.iter_chunked(32768):
                        data.extend(chunk)
                        if len(data) > MAX_BODY:
                            raise ValueError("Страница больше 2 МБ; чтение остановлено")
                    try:
                        text = data.decode(response.charset or "utf-8", errors="replace")
                    except LookupError:
                        text = data.decode("utf-8", errors="replace")
                    return response.status, text, response.content_type, url
        raise ValueError("Слишком много перенаправлений")

    async def _allow(self, url: str, include: list[str], exclude: list[str]):
        url = validate_url(url)
        p = urlsplit(url)
        origin = f"{p.scheme}://{p.netloc}"
        if origin not in self.robots:
            status, body, _, _ = await self._get(origin + "/robots.txt", include, exclude)
            robots = RobotFileParser()
            if status in {401, 403}:
                robots.disallow_all = True
            elif status == 404:
                robots.allow_all = True
            elif status != 200:
                raise ValueError(f"Не удалось проверить robots.txt (HTTP {status}); источник пропущен")
            else:
                robots.parse(body.splitlines())
            self.robots[origin] = robots
        if not self.robots[origin].can_fetch("LocusResearch", url):
            raise ValueError("Сайт ограничивает автоматическое чтение в robots.txt")

    async def read(self, url: str, include: list[str], exclude: list[str]) -> dict:
        status, html, content_type, final_url = await self._get(url, include, exclude, check_robots=True)
        if status != 200:
            raise ValueError(f"Источник недоступен: HTTP {status}")
        if content_type not in {"text/html", "text/plain", "application/xhtml+xml"}:
            raise ValueError("В этой версии поддерживаются HTML и текстовые страницы")
        if content_type == "text/plain":
            title, body = urlsplit(final_url).netloc, html
        else:
            soup = BeautifulSoup(html, "html.parser")
            title = soup.title.get_text(" ", strip=True) if soup.title else urlsplit(final_url).netloc
            for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "form", "svg"]):
                tag.decompose()
            body = (soup.find("main") or soup.find("article") or soup).get_text(" ", strip=True)
        body = re.sub(r"\s+", " ", body).strip()[:64000]
        if len(body) < 120:
            raise ValueError("На странице недостаточно доступного текста")
        return {
            "url": canonical_url(final_url),
            "title": title[:400],
            "body": body,
            "content_hash": hashlib.sha256(body.encode()).hexdigest(),
        }
