"""Ollama native local inference. Metadata probes never load or download models."""

import json
import re

import httpx

from ..models import Settings


def remote(item):
    return bool(item.get("remote_host") or item.get("remote_model"))


def thinking_controls(info):
    descriptor = info.get("thinking") or {}
    values = descriptor.get("values", [])

    def encode(v):
        return "on" if v is True else "off" if v is False else v

    if values:
        options = [encode(v) for v in values if isinstance(v, (str, bool))]
        options = [v for v in options if re.fullmatch(r"[a-z_]{1,24}", v) and v != "default"]
        return list(dict.fromkeys(options)), encode(descriptor.get("default"))
    # Older Ollama releases report capabilities but not the explicit descriptor.
    family = info.get("details", {}).get("family", "")
    if "thinking" in info.get("capabilities", []):
        if family == "gptoss":
            return ["low", "medium", "high"], None
        if family in {"qwen3", "qwen3moe"}:
            return ["off", "on"], None
    return [], None


class OllamaModel:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.excluded_models = 0

    async def models(self):
        async with httpx.AsyncClient(timeout=5, trust_env=False, follow_redirects=False) as client:
            response = await client.get(self.settings.model_url + "/api/tags")
            response.raise_for_status()
            items = response.json().get("models", [])
            self.excluded_models = sum(bool(remote(m)) for m in items)
            return list(
                dict.fromkeys(
                    m["name"]
                    for m in items
                    if isinstance(m.get("name"), str)
                    and not remote(m)
                    and (not m.get("capabilities") or "completion" in m["capabilities"])
                )
            )

    async def inspect(self, model):
        async with httpx.AsyncClient(timeout=10, trust_env=False, follow_redirects=False) as client:
            response = await client.post(self.settings.model_url + "/api/show", json={"model": model})
            response.raise_for_status()
            data = response.json()
        if remote(data):
            raise ValueError("This Ollama model runs remotely. Choose a downloaded local model.")
        if "completion" not in data.get("capabilities", []):
            raise ValueError(
                "Ollama has not confirmed text generation for this model. Choose a local chat model or update Ollama."
            )
        return data

    async def capabilities(self):
        if not self.settings.model:
            return []
        data = await self.inspect(self.settings.model)
        options, default = thinking_controls(data)
        family = data.get("details", {}).get("family", "")
        return [
            {
                "key": self.settings.model,
                "name": self.settings.model,
                "instances": [],
                "max_context": data.get("model_info", {}).get(f"{family}.context_length"),
                "reasoning_options": options,
                "reasoning_default": default,
                "architecture": family,
            }
        ]

    async def complete(self, prompt, schema):
        from .local_model import SYSTEM, parse_json

        # Recheck immediately before each inference, including aliases without a cloud suffix.
        data = await self.inspect(self.settings.model)
        options, _ = thinking_controls(data)
        if self.settings.reasoning != "default" and self.settings.reasoning not in options:
            raise ValueError("This model does not expose the selected thinking level. Refresh capabilities.")
        body = {
            "model": self.settings.model,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM.format(
                        language="Russian" if self.settings.response_language == "ru" else "English"
                    ),
                },
                {
                    "role": "user",
                    "content": prompt + "\nJSON schema:\n" + json.dumps(schema.model_json_schema()),
                },
            ],
            "stream": False,
            "format": schema.model_json_schema() if self.settings.structured_output else "json",
            "options": {
                "temperature": self.settings.temperature,
                "top_p": self.settings.top_p,
                "top_k": self.settings.top_k,
                "min_p": self.settings.min_p,
                "repeat_penalty": self.settings.repeat_penalty,
                "num_predict": self.settings.max_tokens,
            },
        }
        if self.settings.reasoning != "default":
            body["think"] = {"on": True, "off": False}.get(self.settings.reasoning, self.settings.reasoning)
        async with httpx.AsyncClient(
            timeout=self.settings.model_timeout, trust_env=False, follow_redirects=False
        ) as client:
            response = await client.post(self.settings.model_url + "/api/chat", json=body)
            if response.status_code != 200:
                raise ValueError(
                    f"Ollama returned HTTP {response.status_code}. Check the model and generation settings."
                )
            result = response.json()
        if result.get("done_reason") == "length":
            raise ValueError(
                "Model output was truncated. Increase the output token budget or reduce thinking."
            )
        if result.get("error") or not result.get("done"):
            raise ValueError("Ollama did not complete its response. Check the local server.")
        return schema.model_validate(parse_json(result.get("message", {}).get("content", "")))
