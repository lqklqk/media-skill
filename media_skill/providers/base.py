"""Abstract base class for media providers."""
from abc import ABC, abstractmethod
from typing import Optional


class BaseProvider(ABC):
    """Base class for all media providers."""

    def __init__(self, provider_config):
        self.config = provider_config

    @abstractmethod
    async def generate_image(self, prompt: str, params: dict, api_key: str, base_url: str) -> dict:
        ...

    @abstractmethod
    async def generate_video(self, prompt: str, params: dict, api_key: str, base_url: str) -> dict:
        ...

    @abstractmethod
    async def understand_image(self, image_input: str, prompt: str, params: dict, api_key: str, base_url: str) -> str:
        ...

    @abstractmethod
    async def understand_video(self, video_input: str, prompt: str, params: dict, api_key: str, base_url: str) -> str:
        ...

    @abstractmethod
    async def edit_image(self, reference_image: str, prompt: str, params: dict, api_key: str, base_url: str) -> dict:
        ...

    @abstractmethod
    async def edit_video(self, reference_video: str, prompt: str, params: dict, api_key: str, base_url: str) -> dict:
        ...
