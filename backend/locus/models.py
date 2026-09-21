import re
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


def local_endpoint(value: str) -> str:
    parts = urlsplit(value.strip())
    if (
        parts.scheme != "http"
        or parts.hostname not in {"localhost", "127.0.0.1", "::1"}
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
    ):
        raise ValueError("Разрешён только локальный HTTP-сервер: http://127.0.0.1:1234/v1")
    port = parts.port
    if not port or not 1 <= port <= 65535:
        raise ValueError("Укажите порт локального сервера")
    # Pin localhost to a numeric loopback address; do not trust DNS or environment proxies.
    host = "[::1]" if parts.hostname == "::1" else "127.0.0.1"
    return urlunsplit(("http", f"{host}:{port}", parts.path.rstrip("/"), "", ""))


class Settings(Model):
    model_url: str = "http://127.0.0.1:1234/v1"
    model: str = Field(default="", max_length=240)
    temperature: float = Field(default=0.1, ge=0, le=2)
    top_p: float = Field(default=0.9, gt=0, le=1)
    max_tokens: int = Field(default=1600, ge=256, le=16384)
    context_chars: int = Field(default=16000, ge=2000, le=64000)
    model_timeout: int = Field(default=180, ge=15, le=1800)
    structured_output: bool = False
    inference_mode: Literal["chat", "qwen_no_thinking", "lmstudio"] = "chat"
    reasoning: str = Field(default="default", max_length=24, pattern=r"^[a-z_]+$")
    response_language: Literal["en", "ru"] = "en"
    top_k: int = Field(default=40, ge=1, le=1000)
    min_p: float = Field(default=0.05, ge=0, le=1)
    repeat_penalty: float = Field(default=1.0, ge=1, le=2)
    safesearch: Literal["on", "moderate", "off"] = "moderate"
    search_region: str = Field(default="auto", pattern=r"^(auto|wt-wt|[a-z]{2}-[a-z]{2})$")
    search_provider: Literal["direct", "searxng"] = "direct"
    search_backends: list[
        Literal[
            "duckduckgo", "bing", "brave", "mojeek", "yahoo", "google", "yandex", "wikipedia", "startpage"
        ]
    ] = Field(default_factory=lambda: ["duckduckgo", "brave"], min_length=1, max_length=9)
    searxng_url: str = "http://127.0.0.1:8080"
    request_timeout: int = Field(default=20, ge=5, le=90)
    results_per_query: int = Field(default=8, ge=1, le=30)
    domain_delay: float = Field(default=1.5, ge=1, le=30)

    _local_url = field_validator("model_url", "searxng_url")(local_endpoint)

    @model_validator(mode="after")
    def compatible_mode(self):
        if self.inference_mode == "qwen_no_thinking":
            if self.model and not re.search(r"qwen.?3", self.model, re.I):
                raise ValueError("Режим без thinking предназначен только для семейства Qwen 3")
            if self.structured_output:
                raise ValueError(
                    "JSON Schema доступен в стандартном режиме; проверка ответа работает в обоих"
                )
        if self.inference_mode == "lmstudio" and self.structured_output:
            raise ValueError("JSON Schema is only available in chat mode")
        return self


class Budget(Model):
    minutes: int = Field(default=30, ge=1, le=43200)
    queries: int = Field(default=40, ge=1, le=100000)
    pages: int = Field(default=80, ge=1, le=100000)
    rounds: int = Field(default=5, ge=1, le=10000)


class Brief(Model):
    name: str = Field(min_length=2, max_length=160)
    aliases: list[str] = Field(default_factory=list, max_length=15)
    expand_names: bool = True
    surname_change: Literal["unknown", "possible", "known"] = "unknown"
    previous_names: list[str] = Field(default_factory=list, max_length=15)
    output_language: Literal["en", "ru"] = "en"
    city: str = Field(default="", max_length=120)
    country: str = Field(default="", max_length=120)
    year_from: int | None = Field(default=None, ge=1850, le=2100)
    year_to: int | None = Field(default=None, ge=1850, le=2100)
    context: str = Field(default="", max_length=6000)
    languages: list[Literal["ru", "en", "uk", "de", "fr", "es", "it", "pt", "tr", "pl", "zh", "ja"]] = Field(
        default_factory=lambda: ["en", "ru", "uk"], min_length=1, max_length=12
    )
    include_domains: list[str] = Field(default_factory=list, max_length=25)
    exclude_domains: list[str] = Field(default_factory=list, max_length=25)
    seed_urls: list[str] = Field(default_factory=list, max_length=30)
    freshness: Literal["all", "d", "w", "m", "y"] = "all"
    budget: Budget = Field(default_factory=Budget)

    @field_validator("name")
    @classmethod
    def trimmed_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Введите имя")
        return value

    @field_validator("aliases", "previous_names")
    @classmethod
    def trim_aliases(cls, values: list[str]) -> list[str]:
        if any(len(v) > 160 for v in values):
            raise ValueError("Вариант имени слишком длинный")
        return list(dict.fromkeys(v.strip() for v in values if v.strip()))

    @field_validator("include_domains", "exclude_domains")
    @classmethod
    def domains(cls, values: list[str]) -> list[str]:
        result = []
        for value in values:
            value = value.lower().strip().removeprefix("www.")
            value = value.encode("idna").decode("ascii")
            if not re.fullmatch(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", value):
                raise ValueError("Укажите домен без https:// и пути, например example.org")
            result.append(value)
        return list(dict.fromkeys(result))

    @field_validator("seed_urls")
    @classmethod
    def seeds(cls, values: list[str]) -> list[str]:
        from .web import validate_url

        return list(dict.fromkeys(validate_url(v) for v in values))

    @model_validator(mode="after")
    def year_range(self):
        if self.year_from and self.year_to and self.year_from > self.year_to:
            raise ValueError("Начало диапазона лет должно быть раньше конца")
        return self


class Query(Model):
    query: str = Field(min_length=2, max_length=350)
    language: str = Field(default="en", max_length=10)
    reason: str = Field(default="", max_length=300)


class Plan(Model):
    queries: list[Query] = Field(default_factory=list, max_length=24)


class Fact(Model):
    category: Literal[
        "professional_role", "organization", "education", "publication", "public_profile", "public_work"
    ]
    statement: str = Field(min_length=3, max_length=400)
    quote: str = Field(min_length=12, max_length=500)


class Finding(Model):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=500)
    matches: list[str] = Field(default_factory=list, max_length=8)
    contradictions: list[str] = Field(default_factory=list, max_length=8)
    facts: list[Fact] = Field(default_factory=list, max_length=10)


class Extraction(Model):
    candidates: list[Finding] = Field(default_factory=list, max_length=5)


class Review(Model):
    status: Literal["unreviewed", "confirmed", "rejected"]


class Refinement(Model):
    text: str = Field(min_length=2, max_length=2000)
