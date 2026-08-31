---
name: qs-image2-gateway
description: "当用户在 Codex 中要求生图、生成图片、画图、文生图，或提到 Image 2、gpt-image-2、image generation 时使用。通过用户本地 auth.json 和 config.toml 中配置的 QS Image 2 网关生成图片。"
metadata:
  short-description: "通过 QS Image 2 网关生成图片"
---

# QS Image2 Gateway

Use this skill whenever the user asks for image generation, including requests such as 生图, 生成图片, 画图, 文生图, 做一张图, generate an image, draw, create an image, Image 2, or `gpt-image-2`.

This skill is for the user's configured QS Image 2 API gateway. Prefer it over the built-in image generation path when the user is asking Codex to generate an image and has not explicitly chosen another provider.

## Configuration

Use the user's existing Codex configuration:

- API key file: `$HOME/.codex/auth.json`
- API key field: `OPENAI_API_KEY`
- Provider config file: `$HOME/.codex/config.toml`
- Read top-level `model_provider`, then read `[model_providers.<model_provider>]`
- Use that provider's `base_url`
- Default model: `gpt-image-2`
- Generation endpoint: `{base_url.rstrip("/")}/images/generations`

Important: this gateway currently uses OpenAI-compatible paths without `/v1`. Do not call `/v1/images/generations` for this configured gateway unless the user changes the gateway configuration and asks you to retest.

Never print, echo, log, or expose the API key.

## Standard Workflow

For ordinary generation requests, call:

```bash
python "$HOME/.agents/skills/qs-image2-gateway/scripts/generate_image2.py" \
  --prompt "<user image prompt>" \
  --out-dir output/imagegen
```

Use the current workspace for relative output paths. Save final generated images under `output/imagegen/` unless the user requests another location.

After generation, show the saved image inline with an absolute local path and report the saved path.

## Defaults

- `--model gpt-image-2`
- `--quality medium`
- `--size 1024x1024`
- `--n 1`
- Output format is PNG when the gateway returns base64 image data

Use `--quality low` for quick tests or drafts. Use `--quality high` for polished final assets, images with dense text, product mockups, or presentation-ready visuals.

When the user asks for a specific aspect ratio, pick a valid `gpt-image-2` size:

- Square: `1024x1024`
- Landscape: `1536x1024` or `2048x1152`
- Portrait: `1024x1536`
- Wide 4K-style: `3840x2160`
- Tall 4K-style: `2160x3840`

## Script Options

The helper script supports:

- `--prompt`
- `--prompt-file`
- `--model`
- `--quality`
- `--size`
- `--n`
- `--out`
- `--out-dir`
- `--filename-prefix`
- `--force`
- `--list-models`

Use `--list-models` only when checking availability or troubleshooting.

## Failure Handling

If the request fails, report only the status code and sanitized API error fields such as `type`, `code`, and `message`.

If network access is blocked by the sandbox, request approval to run the same command with network access.

If Python HTTPS certificate verification fails in this environment, keep using the helper script; it shells out to `curl` for the actual HTTPS request, which has already been validated against this gateway.

Do not install dependencies for this skill. The helper script uses only Python standard library plus the system `curl` command.
