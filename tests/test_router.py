import pytest
import tempfile
import os

from media_skill.config import Config
from media_skill.router import ModelRouter, RouterError


@pytest.fixture
def config_file():
    content = """
providers:
  - name: openai
    api_key: test-key
    base_url: https://api.openai.com/v1
    models:
      - name: dall-e-3
        type: image_generate
        params: { size: "1024x1024" }
      - name: gpt-4o
        type: image_understand

  - name: aliyun
    api_key: aliyun-key
    base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
    models:
      - name: wanx-v1
        type: image_generate
      - name: sora-turbo
        type: video_generate

defaults:
  image_generate: openai/dall-e-3
  image_understand: openai/gpt-4o
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(content)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def router(config_file):
    cfg = Config(config_file)
    return ModelRouter(cfg)


def test_find_image_model(router):
    provider_cfg, model_cfg = router.config.find_model("openai", "dall-e-3", "image_generate")
    assert provider_cfg.name == "openai"
    assert model_cfg.type == "image_generate"


def test_find_video_model(router):
    provider_cfg, model_cfg = router.config.find_model("aliyun", "sora-turbo", "video_generate")
    assert provider_cfg.name == "aliyun"
    assert model_cfg.type == "video_generate"


def test_find_model_not_found(router):
    result = router.config.find_model("openai", "nonexistent", "image_generate")
    assert result is None
