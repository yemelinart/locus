import json

import httpx
import pytest
from fastapi.testclient import TestClient
from locus.api import create_app
from locus.models import Plan, Settings
from locus.providers.local_model import LocalModel
from locus.providers.ollama import thinking_controls


def transport(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)
    )


def test_old_settings_preserve_lmstudio_and_provider_addresses_are_normalized():
    old = Settings.model_validate({"model": "qwen3", "inference_mode": "qwen_no_thinking"})
    assert old.model_provider == "lmstudio" and old.inference_mode == "qwen_no_thinking"
    assert Settings(model_provider="ollama").model_url == "http://127.0.0.1:11434"
    for path in ["", "/", "/v1", "/api"]:
        assert (
            Settings(model_provider="ollama", model_url="http://localhost:11434" + path).model_url
            == "http://127.0.0.1:11434"
        )
    assert Settings(model_provider="openai_compatible", model_url="http://localhost:8080").model_url.endswith(
        "/v1"
    )
    for provider in ["lmstudio", "ollama", "openai_compatible"]:
        with pytest.raises(ValueError):
            Settings(model_provider=provider, model_url="https://external.example:1234")
    with pytest.raises(ValueError):
        Settings(model_provider="ollama", inference_mode="lmstudio")
    with pytest.raises(ValueError):
        Settings(model_provider="openai_compatible", model="qwen3", inference_mode="qwen_no_thinking")


async def test_ollama_discovery_never_loads_a_model_and_filters_cloud_and_embedding(monkeypatch):
    calls = []

    async def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"name": "local", "capabilities": ["completion"]},
                        {"name": "alias", "remote_host": "https://ollama.com"},
                        {"name": "embed", "capabilities": ["embedding"]},
                    ]
                },
            )
        assert request.url.path == "/api/show"
        return httpx.Response(
            200,
            json={
                "capabilities": ["completion", "thinking"],
                "thinking": {"values": [False, True], "default": True},
                "details": {"family": "qwen3"},
                "model_info": {"qwen3.context_length": 32768},
            },
        )

    transport(monkeypatch, handler)
    model = LocalModel(Settings(model_provider="ollama", model="local"))
    assert await model.models() == ["local"]
    assert model.ollama.excluded_models == 1
    caps = (await model.capabilities())[0]
    assert caps["reasoning_options"] == ["off", "on"] and caps["reasoning_default"] == "on"
    assert caps["max_context"] == 32768
    assert calls == ["/api/tags", "/api/show"]


@pytest.mark.parametrize("reasoning,expected", [("off", False), ("on", True), ("default", None)])
async def test_ollama_generation_maps_options_and_ignores_thinking(monkeypatch, reasoning, expected):
    requests = []

    async def handler(request):
        data = json.loads(request.content)
        requests.append((request.url.path, data))
        if request.url.path == "/api/show":
            return httpx.Response(
                200,
                json={
                    "capabilities": ["completion", "thinking"],
                    "thinking": {"values": [True, False], "default": True},
                },
            )
        return httpx.Response(
            200,
            json={
                "done": True,
                "done_reason": "stop",
                "message": {"thinking": "do not retain this trace", "content": '{"queries":[]}'},
            },
        )

    transport(monkeypatch, handler)
    settings = Settings(
        model_provider="ollama",
        model="local",
        reasoning=reasoning,
        structured_output=True,
        top_k=20,
        min_p=0.1,
        repeat_penalty=1.05,
        max_tokens=2400,
    )
    assert (await LocalModel(settings).complete("Public research plan", Plan)).queries == []
    assert requests[0][0] == "/api/show"
    path, body = requests[1]
    assert path == "/api/chat"
    assert body["options"] == {
        "temperature": 0.1,
        "top_p": 0.9,
        "top_k": 20,
        "min_p": 0.1,
        "repeat_penalty": 1.05,
        "num_predict": 2400,
    }
    assert body.get("think") == expected
    assert ("think" in body) == (reasoning != "default")
    assert body["format"] == Plan.model_json_schema() and body["stream"] is False
    assert not {"tools", "num_ctx", "keep_alive", "max_tokens"} & body.keys()


@pytest.mark.parametrize(
    "info,reason",
    [
        ({"remote_host": "https://ollama.com", "capabilities": ["completion"]}, "remotely"),
        ({"capabilities": ["embedding"]}, "text generation"),
        ({"capabilities": ["completion"]}, "thinking level"),
    ],
)
async def test_ollama_preflight_blocks_incompatible_or_remote_models_before_sending_prompts(
    monkeypatch, info, reason
):
    paths = []

    async def handler(request):
        paths.append(request.url.path)
        return httpx.Response(200, json=info)

    transport(monkeypatch, handler)
    with pytest.raises(ValueError, match=reason):
        await LocalModel(
            Settings(model_provider="ollama", model="innocent-alias", reasoning="high")
        ).complete("private user brief", Plan)
    assert paths == ["/api/show"]


def test_thinking_legacy_known_families_and_unknown_do_not_invent_levels():
    assert thinking_controls({"capabilities": ["thinking"], "details": {"family": "gptoss"}})[0] == [
        "low",
        "medium",
        "high",
    ]
    assert thinking_controls({"capabilities": ["thinking"], "details": {"family": "qwen3"}})[0] == [
        "off",
        "on",
    ]
    assert thinking_controls({"capabilities": ["thinking"], "details": {"family": "unknown"}})[0] == []
    assert thinking_controls({"thinking": {"values": ["low", "max"], "default": "low"}}) == (
        ["low", "max"],
        "low",
    )


async def test_generic_provider_does_not_probe_lmstudio_and_keeps_standard_wire_format(monkeypatch):
    calls = []

    async def handler(request):
        calls.append(request)
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "local-chat"}]})
        return httpx.Response(
            200, json={"choices": [{"message": {"content": '{"queries":[]}'}, "finish_reason": "stop"}]}
        )

    transport(monkeypatch, handler)
    model = LocalModel(
        Settings(model_provider="openai_compatible", model_url="http://127.0.0.1:8080/v1", model="local-chat")
    )
    assert await model.models() == ["local-chat"]
    assert await model.capabilities() == []
    assert (await model.complete("plan", Plan)).queries == []
    assert [r.url.path for r in calls] == ["/v1/models", "/v1/chat/completions"]
    assert "options" not in json.loads(calls[-1].content)


def test_provider_settings_persist_without_altering_research(tmp_path):
    app = create_app(tmp_path, run_worker=False)
    with TestClient(app) as client:
        headers = {"X-Locus-Request": "1"}
        job = client.post("/api/jobs", headers=headers, json={"name": "Fictional model test"}).json()
        for provider in ["ollama", "openai_compatible", "lmstudio"]:
            result = client.put(
                "/api/settings", headers=headers, json=Settings(model_provider=provider).model_dump()
            )
            assert result.status_code == 200
            assert client.get("/api/settings").json()["model_provider"] == provider
        assert client.get(f"/api/jobs/{job['id']}").json()["status"] == "draft"
