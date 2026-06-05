"""OpenAI-compatible API provider adapter."""
import asyncio
import base64
import mimetypes
from pathlib import Path
from typing import Optional

import aiohttp

# Config-only params that should not be sent to the API
_CONFIG_PARAMS = {"endpoint", "poll", "poll_interval"}


def _strip_config_params(params: dict) -> dict:
    """Remove config-only params, return only API payload params."""
    return {k: v for k, v in params.items() if k not in _CONFIG_PARAMS}


class OpenAICompatibleProvider:
    """Provider adapter for any OpenAI-compatible API."""

    def __init__(self, provider_config):
        self.config = provider_config
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    def _resolve_image_input(self, image_input: str) -> dict:
        """Convert image input to OpenAI-compatible format."""
        if image_input.startswith("data:"):
            return {"type": "image_url", "image_url": {"url": image_input}}
        elif image_input.startswith("http://") or image_input.startswith("https://"):
            return {"type": "image_url", "image_url": {"url": image_input}}
        elif image_input.startswith("file://"):
            file_path = Path(image_input[7:])
        else:
            file_path = Path(image_input)

        if not file_path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "image/png"
        with open(file_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        return {
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{image_data}"},
        }

    def _resolve_video_input(self, video_input: str) -> dict:
        """Convert video input to OpenAI-compatible format."""
        if video_input.startswith("file://"):
            file_path = Path(video_input[7:])
        elif video_input.startswith("http://") or video_input.startswith("https://"):
            return {"type": "video_url", "video_url": {"url": video_input}}
        else:
            file_path = Path(video_input)

        if not file_path.exists():
            raise FileNotFoundError(f"Video file not found: {file_path}")

        return {"type": "file_path", "file_path": str(file_path)}

    def _build_messages(self, prompt: str, media_input: Optional[dict] = None) -> list:
        """Build the messages array for the API call."""
        if media_input:
            return [
                {
                    "role": "user",
                    "content": [
                        media_input,
                        {"type": "text", "text": prompt},
                    ],
                }
            ]
        return [{"role": "user", "content": prompt}]

    async def _chat_completion(self, messages: list, model: str, api_key: str, base_url: str, max_tokens: int = 4096) -> str:
        """Make a chat completion API call."""
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"API error: {resp.status} - {error_text}")
                data = await resp.json()
                return data["choices"][0]["message"]["content"]

    async def _image_generation(self, prompt: str, model: str, api_key: str, base_url: str, params: dict) -> dict:
        """Make an image generation API call."""
        url = f"{base_url.rstrip('/')}/images/generations"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if model:
            payload = {
                "model": model,
                "prompt": prompt,
                **params,
            }
        else:
            payload = {
                "prompt": prompt,
                **params,
            }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"API error: {resp.status} - {error_text}")
                data = await resp.json()
                return data

    async def generate_image(self, prompt: str, model: str, params: dict, api_key: str, base_url: str) -> dict:
        data = await self._image_generation(prompt, model, api_key, base_url, _strip_config_params(params))
        if isinstance(data, dict) and "data" in data and len(data["data"]) > 0:
            result = data["data"][0]
            if "url" in result:
                return {"url": result["url"]}
            if "b64_json" in result:
                return {"b64_json": result["b64_json"]}
        return data

    async def _poll_video_task(self, poll_url: str, headers: dict, params: dict) -> dict:
        """Poll for video task completion."""
        interval = params.get("poll_interval", 2)
        while True:
            async with aiohttp.ClientSession() as session:
                async with session.get(poll_url, headers=headers) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise RuntimeError(f"Poll error: {resp.status} - {error_text}")
                    data = await resp.json()

            # Handle nested response formats
            body = data.get("response", {}).get("body", data) if isinstance(data, dict) else data
            status = body.get("status", "")

            if status == "completed":
                video_url = body.get("remixed_from_video_id") or body.get("url") or ""
                return {"url": video_url}
            elif status in ("failed", "error"):
                error_msg = body.get("error", "Unknown error")
                raise RuntimeError(f"Video task failed: {error_msg}")

            await asyncio.sleep(interval)

    async def generate_video(self, prompt: str, model: str, params: dict, api_key: str, base_url: str) -> dict:
        """Generate a video. Supports three modes:

        1. OpenAI-compatible: POST {base_url}/videos/generations, sync response
        2. Custom endpoint: POST {base_url}{endpoint}, sync response
        3. Poll mode: POST {base_url}{endpoint}, then poll GET {base_url}{endpoint}/{task_id}
        """
        endpoint = params.get("endpoint", "/videos/generations")
        url = f"{base_url.rstrip('/')}{endpoint}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        is_poll = params.get("poll", False)
        api_params = _strip_config_params(params)
        payload = {"model": model, "prompt": prompt, **api_params}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"API error: {resp.status} - {error_text}")
                data = await resp.json()

        if is_poll:
            # Async task mode: extract task_id and poll for result
            body = data.get("response", {}).get("body", data) if isinstance(data, dict) else data
            task_id = body.get("id") or body.get("task_id") or ""
            if not task_id:
                return data
            poll_url = f"{url}/{task_id}"
            return await self._poll_video_task(poll_url, headers, params)

        return data

    async def understand_image(self, image_input: str, prompt: str, model: str, params: dict, api_key: str, base_url: str) -> str:
        media = self._resolve_image_input(image_input)
        messages = self._build_messages(prompt, media)
        return await self._chat_completion(messages, model, api_key, base_url, params.get("max_tokens", 4096))

    async def understand_video(self, video_input: str, prompt: str, model: str, params: dict, api_key: str, base_url: str) -> str:
        media = self._resolve_video_input(video_input)
        if media["type"] == "file_path":
            messages = self._build_messages(
                f"{prompt}\n\nVideo file: {media['file_path']}",
                None,
            )
        else:
            messages = self._build_messages(prompt, media)
        return await self._chat_completion(messages, model, api_key, base_url, params.get("max_tokens", 4096))

    async def edit_image(self, reference_image: str, prompt: str, model: str, params: dict, api_key: str, base_url: str) -> dict:
        data = self._resolve_image_input(reference_image)
        if data["type"] == "image_url" and data["image_url"]["url"].startswith("data:"):
            messages = self._build_messages(prompt, data)
            return await self._chat_completion(messages, model, api_key, base_url, params.get("max_tokens", 4096))
        return {"error": "Image editing via URL not supported by this endpoint"}

    async def edit_video(self, reference_video: str, prompt: str, model: str, params: dict, api_key: str, base_url: str) -> dict:
        endpoint = params.get("endpoint", "/videos/edits")
        media = self._resolve_video_input(reference_video)
        url = f"{base_url.rstrip('/')}{endpoint}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        is_poll = params.get("poll", False)
        api_params = _strip_config_params(params)
        payload = {"model": model, "prompt": prompt, "reference_video": media, **api_params}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"API error: {resp.status} - {error_text}")
                data = await resp.json()

        if is_poll:
            body = data.get("response", {}).get("body", data) if isinstance(data, dict) else data
            task_id = body.get("id") or body.get("task_id") or ""
            if not task_id:
                return data
            poll_url = f"{url}/{task_id}"
            return await self._poll_video_task(poll_url, headers, params)

        return data
