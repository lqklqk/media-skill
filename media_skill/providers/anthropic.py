"""Anthropic API provider adapter."""
import base64
import mimetypes
from pathlib import Path
from typing import Optional

import aiohttp


class AnthropicProvider:
    """Provider adapter for Anthropic Claude models."""

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
        """Convert image input to Anthropic format."""
        if image_input.startswith("data:"):
            parts = image_input.split(",", 1)
            mime_type = parts[0].split(":")[1].split(";")[0]
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": parts[1],
                },
            }
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
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime_type,
                "data": image_data,
            },
        }

    async def _send_message(self, messages: list, model: str, api_key: str, base_url: str, params: dict) -> str:
        """Send a message to Anthropic API."""
        url = f"{base_url.rstrip('/')}/messages"
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": params.get("max_tokens", 4096),
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"Anthropic API error: {resp.status} - {error_text}")
                data = await resp.json()
                return data["content"][0]["text"]

    async def generate_image(self, prompt: str, params: dict, api_key: str, base_url: str) -> dict:
        raise NotImplementedError("Anthropic does not support image generation")

    async def generate_video(self, prompt: str, params: dict, api_key: str, base_url: str) -> dict:
        raise NotImplementedError("Anthropic does not support video generation")

    async def understand_image(self, image_input: str, prompt: str, model: str, params: dict, api_key: str, base_url: str) -> str:
        media = self._resolve_image_input(image_input)
        messages = [
            {
                "role": "user",
                "content": [
                    media,
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        return await self._send_message(messages, model, api_key, base_url, params)

    async def understand_video(self, video_input: str, prompt: str, params: dict, api_key: str, base_url: str) -> str:
        raise NotImplementedError("Anthropic does not support video understanding")

    async def edit_image(self, reference_image: str, prompt: str, params: dict, api_key: str, base_url: str) -> dict:
        raise NotImplementedError("Anthropic does not support image editing")

    async def edit_video(self, reference_video: str, prompt: str, params: dict, api_key: str, base_url: str) -> dict:
        raise NotImplementedError("Anthropic does not support video editing")
