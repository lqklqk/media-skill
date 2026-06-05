import pytest
import asyncio
from media_skill.providers.anthropic import AnthropicProvider


@pytest.fixture
def provider():
    return AnthropicProvider({"name": "anthropic"})


def test_resolve_image_from_file(provider, tmp_path):
    img_file = tmp_path / "test.png"
    img_file.write_bytes(b"fake image data")
    result = provider._resolve_image_input(str(img_file))
    assert result["type"] == "image"
    assert result["source"]["type"] == "base64"
    assert result["source"]["media_type"] == "image/png"


def test_resolve_image_from_data_uri(provider):
    data_uri = "data:image/jpeg;base64,abc123"
    result = provider._resolve_image_input(data_uri)
    assert result["type"] == "image"
    assert result["source"]["data"] == "abc123"


async def _test_unsupported(provider):
    with pytest.raises(NotImplementedError):
        await provider.generate_image("prompt", {}, "key", "url")
    with pytest.raises(NotImplementedError):
        await provider.generate_video("prompt", {}, "key", "url")
    with pytest.raises(NotImplementedError):
        await provider.understand_video("ref", "prompt", {}, "key", "url")
    with pytest.raises(NotImplementedError):
        await provider.edit_image("ref", "prompt", {}, "key", "url")
    with pytest.raises(NotImplementedError):
        await provider.edit_video("ref", "prompt", {}, "key", "url")


def test_unsupported_operations(provider):
    asyncio.get_event_loop().run_until_complete(_test_unsupported(provider))
