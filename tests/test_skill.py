import pytest
import tempfile
import os

from media_skill.skill import MediaSkill


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
def skill(config_file):
    return MediaSkill(config_path=config_file)


def test_skill_initialization(skill):
    assert skill.config is not None
    assert skill.session_manager is not None
    assert skill.router is not None


def test_list_sessions_empty(skill):
    sessions = skill.list_sessions()
    assert isinstance(sessions, list)


def test_get_history_empty(skill):
    history = skill.get_history()
    assert isinstance(history, list)
    assert len(history) == 0
