# Media Skill

Multi-provider AI image/video generation, understanding, and editing skill for opencode and other AI agents.

## Features

- **Image Generation** — Generate images from text prompts
- **Video Generation** — Generate videos from text prompts  
- **Image Understanding** — Analyze images (vision models)
- **Video Understanding** — Analyze videos (vision models)
- **Image Editing** — Modify existing images with instructions
- **Video Editing** — Modify existing videos with instructions
- **Multi-Provider** — Supports OpenAI-compatible and Anthropic APIs
- **Session Management** — Context-aware conversations with automatic session tracking

## Installation

### Option 1: Install via opencode skill system

Copy the `media-skill` folder into your opencode `skills/` directory:

```bash
cp -r media-skill ~/.config/opencode/skills/
```

opencode will automatically:
1. Create a `.venv` inside the skill folder
2. Install `pyyaml` and `aiohttp` dependencies

### Option 2: Manual Python installation

```bash
cd media-skill
python3 -m venv .venv
.venv/bin/pip install pyyaml aiohttp
```

## Quick Start

### 1. Configure models

```bash
cp models.yaml.example models.yaml
```

Edit `models.yaml` with your provider configurations:

```yaml
providers:
  - name: openai
    api_key: "${OPENAI_API_KEY}"
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
```

### 2. Use in opencode

When you want to generate images, analyze media, or edit content, opencode will automatically activate this skill and handle the API calls.

### 3. Use as Python SDK

```bash
cd media-skill
.venv/bin/python -c "
import asyncio
from media_skill import MediaSkill

async def main():
    skill = MediaSkill('models.yaml')
    
    # Generate an image
    result = await skill.generate_image(prompt='A cat on a windowsill')
    print(f'Image saved to: {result[\"file_path\"]}')
    
    # Analyze an image
    result = await skill.understand_image(
        image='file:///path/to/image.jpg',
        prompt='Describe this image in detail'
    )
    print(result['description'])
    
    # Edit an image with session context
    result = await skill.edit_image(
        prompt='Make the cat black',
        reference_ref='img_001'
    )
    print(f'Edited image saved to: {result[\"file_path\"]}')

asyncio.run(main())
"
```

## Supported Providers

### OpenAI-Compatible (Universal)
Works with any provider following OpenAI API format:
- OpenAI (DALL-E, GPT-4o)
- Azure OpenAI
- Google Gemini
- Aliyun Dashscope (通义万相)
- Zhipu AI (智谱)
- Any custom endpoint with OpenAI-compatible format

### Anthropic
- Claude models for image understanding only

## Configuration

### Provider Setup

Each provider entry needs:
- `name` — Unique identifier
- `api_key` — Your API key (supports `${ENV_VAR}` syntax)
- `base_url` — API endpoint URL
- `models` — List of available models with their types

### Model Types

| Type | Description |
|------|-------------|
| `image_generate` | Generate image from text |
| `video_generate` | Generate video from text |
| `image_understand` | Analyze/understand images |
| `video_understand` | Analyze/understand videos |

### Default Models

Configure `defaults` in `models.yaml` to set fallback models when provider/model is not specified:

```yaml
defaults:
  image_generate: openai/dall-e-3
  video_generate: aliyun/sora-turbo
  image_understand: openai/gpt-4o
  video_understand: openai/gpt-4o
```

## Session Management

Sessions are automatically managed:
- **Default session** — Created on first use, persisted in `skill_state.json`
- **Named sessions** — Pass `session_id` for multi-conversation isolation
- **Media references** — Generated images/videos are tracked as `img_001`, `vid_001`, etc. for easy reference in subsequent edits

## Input Formats

All media operations support three input formats:
- `file:///path/to/local/file` — Local file path
- `https://example.com/image.jpg` — Public URL
- `data:image/jpeg;base64,...` — Base64 encoded data

## Project Structure

```
media-skill/
├── SKILL.md                    # Skill definition + auto-install config
├── manifest.json               # Clawhub metadata
├── models.yaml.example         # Example configuration
├── README.md                   # This file
├── media_skill/                # Core Python package
│   ├── __init__.py
│   ├── skill.py                # Main API entry point
│   ├── config.py               # YAML config loader
│   ├── session.py              # Session/context management
│   ├── router.py               # Model provider router
│   └── providers/
│       ├── base.py             # Abstract provider interface
│       ├── openai_compat.py    # OpenAI-compatible adapter
│       └── anthropic.py        # Anthropic adapter
└── tests/                      # 31 unit and integration tests
```

## License

MIT
