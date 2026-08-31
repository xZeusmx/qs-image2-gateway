# QS Image2 Gateway

Codex Skill for generating images through a configured Image 2 gateway.

This skill is designed for Codex users who store their OpenAI-compatible API key in:

```text
~/.codex/auth.json
```

and their provider gateway URL in:

```text
~/.codex/config.toml
```

It defaults to:

```text
gpt-image-2
```

and calls the gateway endpoint without a `/v1` prefix:

```text
{base_url}/images/generations
```

## What It Does

- Triggers on image generation requests such as 生图, 生成图片, 画图, Image 2, `gpt-image-2`, and image generation.
- Reads `OPENAI_API_KEY` from `~/.codex/auth.json`.
- Reads the active `model_provider` and provider `base_url` from `~/.codex/config.toml`.
- Calls `{base_url}/images/generations`.
- Saves generated PNG images to `output/imagegen/` by default.
- Avoids printing or exposing the API key.

## Installation

Copy this skill folder into your user-level Codex skills directory:

```bash
mkdir -p "$HOME/.agents/skills"
cp -R qs-image2-gateway "$HOME/.agents/skills/qs-image2-gateway"
```

Then restart Codex or open a new task so the skill list is refreshed.

## Required Local Config

`~/.codex/auth.json` should contain:

```json
{
  "OPENAI_API_KEY": "your-api-key"
}
```

`~/.codex/config.toml` should contain a provider with a `base_url`:

```toml
model_provider = "sub2api"

[model_providers.sub2api]
name = "sub2api"
base_url = "https://your-gateway.example.com/"
wire_api = "responses"
requires_openai_auth = true
```

The skill dynamically reads the active provider, so changing `model_provider` changes the gateway used by the helper script.

## Usage In Codex

Natural language:

```text
帮我生成一张科技感的产品海报
```

Explicit provider wording:

```text
用 QS Image2 Gateway 生成一张图：一个蓝色科技风的数据安全平台主视觉，16:9，适合 PPT 首页。
```

Explicit skill invocation:

```text
$qs-image2-gateway 生成一张图：一个简洁高级的 AI 数据中台插画，白底，蓝绿色点缀。
```

## Manual Script Usage

Generate one image:

```bash
./scripts/generate_image2.py \
  --prompt "一张简洁的蓝色科技风图标，白底，无文字" \
  --quality low \
  --size 1024x1024 \
  --out-dir output/imagegen
```

List available image models:

```bash
./scripts/generate_image2.py --list-models
```

## Defaults

- Model: `gpt-image-2`
- Quality: `medium`
- Size: `1024x1024`
- Count: `1`
- Output directory: `output/imagegen/`

Common `gpt-image-2` sizes:

- `1024x1024`
- `1536x1024`
- `1024x1536`
- `2048x1152`
- `3840x2160`
- `2160x3840`

## Files

```text
qs-image2-gateway/
├── SKILL.md
├── agents/
│   └── openai.yaml
└── scripts/
    └── generate_image2.py
```

## Security

Do not commit `~/.codex/auth.json`, `.env`, or any local API key files.

The helper script only reads the API key locally and sends it in the `Authorization` header. It does not print the key.
