import pytest
import tempfile
import os
from media_skill.config import Config


@pytest.fixture
def config_file():
    content = """
providers:
  - name: openai
    api_key: test-key-123
    base_url: https://api.openai.com/v1
    models:
      - name: dall-e-3
        type: image_generate
        params: { size: "1024x1024" }
      - name: gpt-4o
        type: image_understand
  - name: anthropic
    api_key: ant-key-456
    base_url: https://api.anthropic.com
    models:
      - name: claude-sonnet
        type: image_understand
        max_tokens: 4096

defaults:
  image_generate: openai/dall-e-3
  image_understand: openai/gpt-4o
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(content)
        path = f.name
    yield path
    os.unlink(path)


def test_load_config(config_file):
    cfg = Config(config_file)
    app = cfg.config
    assert len(app.providers) == 2
    assert app.defaults["image_generate"] == "openai/dall-e-3"


def test_get_provider(config_file):
    cfg = Config(config_file)
    p = cfg.get_provider("openai")
    assert p is not None
    assert p.api_key == "test-key-123"
    assert len(p.models) == 2


def test_get_models_by_type(config_file):
    cfg = Config(config_file)
    results = cfg.get_models_by_type("image_understand")
    assert len(results) == 2


def test_resolve_default(config_file):
    cfg = Config(config_file)
    result = cfg.resolve_default("image_generate")
    assert result == ("openai", "dall-e-3")


def test_find_model(config_file):
    cfg = Config(config_file)
    provider, model = cfg.find_model("openai", "dall-e-3", "image_generate")
    assert provider.name == "openai"
    assert model.name == "dall-e-3"
    assert model.params == {"size": "1024x1024"}


def test_find_model_default(config_file):
    cfg = Config(config_file)
    provider, model = cfg.find_model(None, None, "image_generate")
    assert provider.name == "openai"
    assert model.name == "dall-e-3"


def test_env_var_injection():
    os.environ["TEST_API_KEY"] = "secret-key"
    try:
        content = """
providers:
  - name: test
    api_key: "${TEST_API_KEY}"
    base_url: https://example.com/v1
    models: []
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(content)
            path = f.name
        try:
            cfg = Config(path)
            p = cfg.get_provider("test")
            assert p.api_key == "secret-key"
        finally:
            os.unlink(path)
    finally:
        del os.environ["TEST_API_KEY"]
