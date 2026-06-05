"""Integration test that exercises the full flow."""
import pytest
import tempfile
import os
from pathlib import Path

from media_skill import MediaSkill


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


def test_full_skill_lifecycle(config_file, tmp_path):
    """Test that the skill can be instantiated and basic methods work."""
    skill = MediaSkill(config_path=config_file)

    # Check config loaded correctly
    assert len(skill.config.config.providers) == 1
    assert skill.config.config.defaults["image_generate"] == "openai/dall-e-3"

    # Check session management
    sessions = skill.list_sessions()
    assert isinstance(sessions, list)

    # Check history is empty initially
    history = skill.get_history()
    assert isinstance(history, list)
    assert len(history) == 0
