import pytest
from pathlib import Path
from media_skill.providers.openai_compat import OpenAICompatibleProvider


@pytest.fixture
def provider():
    return OpenAICompatibleProvider({"name": "test"})


def test_resolve_image_from_file(provider, tmp_path):
    img_file = tmp_path / "test.png"
    img_file.write_bytes(b"fake image data")
    result = provider._resolve_image_input(str(img_file))
    assert result["type"] == "image_url"
    assert result["image_url"]["url"].startswith("data:image/png;base64,")


def test_resolve_image_from_url(provider):
    result = provider._resolve_image_input("https://example.com/image.jpg")
    assert result["type"] == "image_url"
    assert result["image_url"]["url"] == "https://example.com/image.jpg"


def test_resolve_image_from_data_uri(provider):
    data_uri = "data:image/jpeg;base64,abc123"
    result = provider._resolve_image_input(data_uri)
    assert result["type"] == "image_url"
    assert result["image_url"]["url"] == data_uri


def test_resolve_image_missing_file(provider):
    with pytest.raises(FileNotFoundError):
        provider._resolve_image_input("/nonexistent/path/image.png")


def test_build_messages_without_media(provider):
    messages = provider._build_messages("describe this")
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "describe this"


def test_build_messages_with_media(provider):
    media = {"type": "image_url", "image_url": {"url": "https://example.com/img.png"}}
    messages = provider._build_messages("describe this", media)
    assert len(messages) == 1
    assert len(messages[0]["content"]) == 2
    assert messages[0]["content"][0] == media
    assert messages[0]["content"][1]["type"] == "text"
    assert messages[0]["content"][1]["text"] == "describe this"
