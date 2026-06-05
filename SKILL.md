---
name: media-skill
description: Multi-provider image/video generation, understanding, and editing SDK. Supports OpenAI-compatible and Anthropic APIs with session-based context management.
---

# Media Skill

## Description
Media Skill is a Python SDK for managing AI image and video generation, understanding (vision), and editing across multiple providers. It supports OpenAI-compatible APIs (OpenAI, Azure, Dashscope, Zhipu, Gemini, etc.) and Anthropic APIs through a unified interface.

**Safety Note**: The installation process downloads packages from PyPI. Processing certain formats may require external network access.

## Dependencies
- `pyyaml>=6.0`
- `aiohttp>=3.9.0`

## Metadata for Auto-Install
```json
{
  "openclaw": {
    "requires": { "bins": ["python3", "python"] },
    "install": [
      {
        "id": "venv-linux-mac",
        "kind": "exec",
        "platforms": ["linux", "macos"],
        "command": "python3 -m venv .venv && .venv/bin/pip install pyyaml aiohttp",
        "label": "Create virtual environment and install pyyaml and aiohttp from PyPI (Linux/macOS)"
      },
      {
        "id": "venv-windows",
        "kind": "exec",
        "platforms": ["windows"],
        "command": "python -m venv .venv && .venv\\Scripts\\python -m pip install pyyaml aiohttp",
        "label": "Create virtual environment and install pyyaml and aiohttp from PyPI (Windows)"
      }
    ]
  }
}
```

## Trigger

This skill SHOULD be activated when the AI agent needs to:

1. **Generate an image** from a text description (e.g., "generate a banner image", "create a logo", "design a website background")
2. **Generate a video** from a text description (e.g., "create a promotional video")
3. **Understand/analyze an image** — user uploads or references an image
4. **Understand/analyze a video** — user uploads or references a video
5. **Edit an existing image or video** based on instructions (e.g., "make the cat black", "speed up the video")
6. **Reference a previously generated image** in a follow-up action (e.g., "use the first image but make it dark")

## First Time Setup

Before using this skill, check if the virtual environment exists. If not, create it and install dependencies:

**Linux/macOS:**
```bash
cd <skill_dir>
if [ ! -d ".venv" ]; then python3 -m venv .venv && .venv/bin/pip install pyyaml aiohttp; fi
```

**Windows (PowerShell/CMD):**
```powershell
cd <skill_dir>
if (-not (Test-Path ".venv")) { python -m venv .venv && .venv\Scripts\python -m pip install pyyaml aiohttp }
```

After setup, always use `.venv/bin/python` (Linux/macOS) or `.venv\Scripts\python` (Windows) to run all Python commands below.

## Agent Guidance

When generating code that uses this skill, you should:

### Virtual Environment Check

Always run Python code through the skill's virtual environment. Use this path pattern:

**Linux/macOS:** `<skill_dir>/.venv/bin/python`
**Windows:** `<skill_dir>/.venv/Scripts/python`

### Output Directory

Always set `output_dir` to the user's current project directory so generated files are saved there:

```python
skill = MediaSkill(config_path="<skill_dir>/models.yaml", output_dir=".")
```

If you run from the skill directory, pass the user's project path explicitly:
```python
skill = MediaSkill(
    config_path="<skill_dir>/models.yaml",
    output_dir="/path/to/user/project"
)
```

All generated files will be saved under `{output_dir}/generated/{session_id}/`.

### Prompt Language

The user speaks Chinese. Different models have different language support for prompts:

| Model Type | Prompt Language | Example |
|------------|----------------|---------|
| OpenAI DALL-E | **English preferred** | → Translate "一只橘猫" to "An orange cat" |
| 通义万相 (Aliyun) | **Chinese native** | → Pass directly "一只橘猫坐在窗台上" |
| 智谱 (Zhipu) | **Chinese native** | → Pass directly |
| Anthropic Claude | **Bilingual** | Chinese or English both work well |
| Others / Unknown | **English** (safer) | → Translate Chinese to English |

**Rule:** Check the provider name in `models.yaml`. If the provider is Aliyun, Zhipu, or other Chinese-oriented API, pass the prompt in the user's original Chinese. For OpenAI and unknown providers, translate the Chinese prompt to English first.

Example:

```bash
# User says: "生成一张橘猫坐在窗台上的图片"
# If using Aliyun (Chinese model):
prompt = "一只橘猫坐在窗台上，阳光洒在它身上，温暖的氛围"

# If using OpenAI DALL-E (English model):
prompt = "An orange cat sitting on a windowsill, sunlight shining on it, warm atmosphere"
```

Example:
```bash
<skill_dir>/.venv/bin/python -c "
import asyncio
from media_skill import MediaSkill
...
"
```

### Image Generation

Call `skill.generate_image()` with the prompt. Use the `size` parameter when you know the required dimensions:

```bash
<skill_dir>/.venv/bin/python -c "
import asyncio
from media_skill import MediaSkill
async def main():
    skill = MediaSkill('<skill_dir>/models.yaml', output_dir='.')
    # Default size (model decides)
    result = await skill.generate_image(prompt='A serene lake at sunset')
    print('Image:', result['file_path'])
asyncio.run(main())
"
```

Common web dimensions to use:
- **Banner/Carousel**: `1920x480` or `1920x600`
- **Blog cover**: `1200x630` (social media optimal)
- **Logo**: `512x512` or `256x256`
- **Profile picture**: `256x256` or `512x512`
- **Social media post**: `1080x1080`

If the user does not specify dimensions, choose an appropriate size based on the context (e.g., `1024x1024` for a general image, `1920x480` for a website banner).

### Video Generation

```bash
<skill_dir>/.venv/bin/python -c "
import asyncio
from media_skill import MediaSkill
async def main():
    skill = MediaSkill('<skill_dir>/models.yaml', output_dir='.')
    result = await skill.generate_video(prompt='A cat sunbathing, camera slowly zooms in', duration=5)
    print('Video:', result['file_path'])
asyncio.run(main())
"
```

### Image Understanding

```bash
<skill_dir>/.venv/bin/python -c "
import asyncio
from media_skill import MediaSkill
async def main():
    skill = MediaSkill('<skill_dir>/models.yaml', output_dir='.')
    result = await skill.understand_image(image='file:///path/to/image.jpg', prompt='Describe this image in detail')
    print(result['description'])
asyncio.run(main())
"
```

### Image/Video Editing

Use `reference_ref` to reference a previously generated image:

```bash
<skill_dir>/.venv/bin/python -c "
import asyncio
from media_skill import MediaSkill
async def main():
    skill = MediaSkill('<skill_dir>/models.yaml', output_dir='.')
    # Generate first image
    r1 = await skill.generate_image(prompt='A white cat')
    print('Original:', r1['file_path'])
    # Edit based on reference
    r2 = await skill.edit_image(prompt='Make the cat black', reference_ref='img_001')
    print('Edited:', r2['file_path'])
asyncio.run(main())
"
```

The `reference_ref` points to images/videos generated in the same session (e.g., `img_001`, `vid_001`).

## Configuration

Edit `<skill_dir>/models.yaml` to add your provider configurations. Example:

```yaml
providers:
  - name: openai
    api_key: "${OPENAI_API_KEY}"
    base_url: https://api.openai.com/v1
    models:
      - name: dall-e-3
        type: image_generate
      - name: gpt-4o
        type: image_understand
        max_tokens: 4096

defaults:
  image_generate: openai/dall-e-3
  image_understand: openai/gpt-4o
```

## API Reference

### Supported Operations

| Method | Purpose | Key Parameters |
|--------|---------|----------------|
| `generate_image(prompt, size?, provider?, model?)` | Generate image from text | `prompt` (required), `size` (optional, e.g., "1920x480") |
| `generate_video(prompt, duration?, resolution?, provider?, model?)` | Generate video from text | `prompt` (required), `duration` in seconds |
| `understand_image(image, prompt, provider?, model?)` | Analyze/understand an image | `image` (file path/URL/base64), `prompt` |
| `understand_video(video, prompt, provider?, model?)` | Analyze/understand a video | `video` (file path/URL/base64), `prompt` |
| `edit_image(prompt, reference_ref?, provider?, model?)` | Edit an existing image | `prompt`, `reference_ref` (e.g., "img_001") |
| `edit_video(prompt, reference_ref?, provider?, model?)` | Edit an existing video | `prompt`, `reference_ref` (e.g., "vid_001") |

### Session Management

Sessions are automatically managed:
- **Default session** — Created on first use, persisted in SQLite database
- **Named sessions** — Pass `session_id` for multi-conversation isolation
- **Media references** — Generated images/videos are tracked as `img_001`, `img_002`, `vid_001` for easy reference in subsequent edits

### Supported Input Formats

All media operations support three input formats:
- `file:///path/to/local/file` — Local file path
- `https://example.com/image.jpg` — Public URL
- `data:image/jpeg;base64,...` — Base64 encoded data

### Supported Providers

- **OpenAI-compatible** — Any provider following OpenAI API format (OpenAI, Azure, Dashscope, Zhipu, Gemini, etc.)
- **Anthropic** — Claude models for image understanding only
