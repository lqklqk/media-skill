"""Model router that selects the right provider and model for each operation."""
import io
import base64
from pathlib import Path
from typing import Optional

import aiohttp

from .config import Config, ProviderConfig
from .providers.openai_compat import OpenAICompatibleProvider
from .providers.anthropic import AnthropicProvider


class RouterError(Exception):
    pass


class ModelRouter:
    """Routes media operations to the correct provider and model."""

    def __init__(self, config: Config):
        self.config = config
        self._providers_cache: dict = {}

    def _get_provider(self, provider_name: str):
        """Get or create a provider instance."""
        if provider_name in self._providers_cache:
            return self._providers_cache[provider_name]

        provider_config = self.config.get_provider(provider_name)
        if not provider_config:
            raise RouterError(f"Provider '{provider_name}' not found in config")

        if provider_name == "anthropic":
            provider = AnthropicProvider(provider_config)
        else:
            provider = OpenAICompatibleProvider(provider_config)

        self._providers_cache[provider_name] = provider
        return provider

    async def close(self):
        """Close all provider sessions."""
        for p in self._providers_cache.values():
            await p.close()

    async def _save_image_from_result(self, result: dict, output_path: str):
        """Save image from API result to local file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if "url" in result and result["url"]:
            async with aiohttp.ClientSession() as session:
                async with session.get(result["url"]) as resp:
                    if resp.status == 200:
                        path.write_bytes(await resp.read())
                        return
        elif "b64_json" in result and result["b64_json"]:
            image_data = base64.b64decode(result["b64_json"])
            path.write_bytes(image_data)
            return

        # If no URL or base64, try to handle streaming/other formats
        path.write_text(str(result), encoding="utf-8")

    async def _save_video_from_result(self, result: dict, output_path: str):
        """Save video from API result to local file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if "url" in result and result["url"]:
            async with aiohttp.ClientSession() as session:
                async with session.get(result["url"]) as resp:
                    if resp.status == 200:
                        path.write_bytes(await resp.read())
                        return
        path.write_text(str(result), encoding="utf-8")

    async def generate_image(self, provider_name: Optional[str], model_name: Optional[str], prompt: str, params: dict, output_path: str) -> str:
        model_info = self.config.find_model(provider_name, model_name, "image_generate")
        if not model_info:
            available = [f"{p.name}/{m.name}" for p, m in self.config.get_models_by_type("image_generate")]
            raise RouterError(f"Model not found for image_generate. Try one of: {', '.join(available)}")
        provider_cfg, model_cfg = model_info
        provider = self._get_provider(provider_cfg.name)
        merged_params = {**model_cfg.params, **params}

        # Pass the actual model name to the provider
        if hasattr(provider, 'generate_image'):
            result = await provider.generate_image(prompt, model_cfg.name, merged_params, provider_cfg.api_key, provider_cfg.base_url)
        else:
            result = await provider.generate_image(prompt, merged_params, provider_cfg.api_key, provider_cfg.base_url)

        await self._save_image_from_result(result, output_path)
        return output_path

    async def generate_video(self, provider_name: Optional[str], model_name: Optional[str], prompt: str, params: dict, output_path: str) -> str:
        model_info = self.config.find_model(provider_name, model_name, "video_generate")
        if not model_info:
            available = [f"{p.name}/{m.name}" for p, m in self.config.get_models_by_type("video_generate")]
            raise RouterError(f"Model not found for video_generate. Try one of: {', '.join(available)}")
        provider_cfg, model_cfg = model_info
        provider = self._get_provider(provider_cfg.name)
        merged_params = {**model_cfg.params, **params}
        result = await provider.generate_video(prompt, model_cfg.name, merged_params, provider_cfg.api_key, provider_cfg.base_url)

        await self._save_video_from_result(result, output_path)
        return output_path

    async def understand_image(self, provider_name: Optional[str], model_name: Optional[str], image_input: str, prompt: str, params: dict) -> str:
        model_info = self.config.find_model(provider_name, model_name, "image_understand")
        if not model_info:
            available = [f"{p.name}/{m.name}" for p, m in self.config.get_models_by_type("image_understand")]
            raise RouterError(f"Model not found for image_understand. Try one of: {', '.join(available)}")
        provider_cfg, model_cfg = model_info
        provider = self._get_provider(provider_cfg.name)
        merged_params = {**model_cfg.params, **params}

        if hasattr(provider, 'understand_image'):
            return await provider.understand_image(image_input, prompt, model_cfg.name, merged_params, provider_cfg.api_key, provider_cfg.base_url)
        return await provider.understand_image(image_input, prompt, merged_params, provider_cfg.api_key, provider_cfg.base_url)

    async def understand_video(self, provider_name: Optional[str], model_name: Optional[str], video_input: str, prompt: str, params: dict) -> str:
        model_info = self.config.find_model(provider_name, model_name, "video_understand")
        if not model_info:
            available = [f"{p.name}/{m.name}" for p, m in self.config.get_models_by_type("video_understand")]
            raise RouterError(f"Model not found for video_understand. Try one of: {', '.join(available)}")
        provider_cfg, model_cfg = model_info
        provider = self._get_provider(provider_cfg.name)
        merged_params = {**model_cfg.params, **params}

        if hasattr(provider, 'understand_video'):
            return await provider.understand_video(video_input, prompt, model_cfg.name, merged_params, provider_cfg.api_key, provider_cfg.base_url)
        return await provider.understand_video(video_input, prompt, merged_params, provider_cfg.api_key, provider_cfg.base_url)

    async def edit_image(self, provider_name: Optional[str], model_name: Optional[str], reference_image: str, prompt: str, params: dict, output_path: str) -> str:
        model_info = self.config.find_model(provider_name, model_name, "image_generate")
        if not model_info:
            raise RouterError("No model found for image generation/editing")
        provider_cfg, model_cfg = model_info
        provider = self._get_provider(provider_cfg.name)
        merged_params = {**model_cfg.params, **params}

        if hasattr(provider, 'edit_image'):
            result = await provider.edit_image(reference_image, prompt, model_cfg.name, merged_params, provider_cfg.api_key, provider_cfg.base_url)
        else:
            result = await provider.edit_image(reference_image, prompt, merged_params, provider_cfg.api_key, provider_cfg.base_url)

        await self._save_image_from_result(result, output_path)
        return output_path

    async def edit_video(self, provider_name: Optional[str], model_name: Optional[str], reference_video: str, prompt: str, params: dict, output_path: str) -> str:
        model_info = self.config.find_model(provider_name, model_name, "video_generate")
        if not model_info:
            raise RouterError("No model found for video editing")
        provider_cfg, model_cfg = model_info
        provider = self._get_provider(provider_cfg.name)
        merged_params = {**model_cfg.params, **params}
        result = await provider.edit_video(reference_video, prompt, model_cfg.name, merged_params, provider_cfg.api_key, provider_cfg.base_url)

        await self._save_video_from_result(result, output_path)
        return output_path
