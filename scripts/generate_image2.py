#!/usr/bin/env python3
"""通过用户配置的 QS Image 2 网关生成图片。"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_AUTH_PATH = Path.home() / ".codex" / "auth.json"
DEFAULT_CONFIG_PATH = Path.home() / ".codex" / "config.toml"
DEFAULT_OUT_DIR = Path("output/imagegen")


def die(message: str, exit_code: int = 1) -> None:
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False), file=sys.stderr)
    raise SystemExit(exit_code)


def slugify(value: str, fallback: str = "image") -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return (value[:60].strip("-") or fallback)


def parse_simple_toml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current: dict[str, Any] = data

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            current = data
            for part in section.split("."):
                current = current.setdefault(part, {})
            continue

        if "=" not in line:
            continue

        key, value = [part.strip() for part in line.split("=", 1)]
        if value.startswith('"') and value.endswith('"'):
            parsed: Any = value[1:-1]
        elif value.lower() == "true":
            parsed = True
        elif value.lower() == "false":
            parsed = False
        else:
            parsed = value
        current[key] = parsed

    return data


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        die(f"Config file not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        import tomllib

        return tomllib.loads(text)
    except Exception:
        return parse_simple_toml(text)


def load_key(path: Path) -> str:
    if not path.exists():
        die(f"Auth file not found: {path}")
    try:
        auth = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die(f"Could not parse auth JSON: {exc}")

    key = auth.get("OPENAI_API_KEY")
    if not isinstance(key, str) or not key.strip():
        die("OPENAI_API_KEY was not found in auth.json")
    return key.strip()


def resolve_base_url(config: dict[str, Any]) -> str:
    provider_name = config.get("model_provider")
    providers = config.get("model_providers")
    if not isinstance(provider_name, str) or not provider_name:
        die("model_provider was not found in config.toml")
    if not isinstance(providers, dict):
        die("model_providers was not found in config.toml")

    provider = providers.get(provider_name)
    if not isinstance(provider, dict):
        die(f"Provider config was not found for model_provider={provider_name!r}")

    base_url = provider.get("base_url")
    if not isinstance(base_url, str) or not base_url.strip():
        die(f"base_url was not found for provider {provider_name!r}")
    return base_url.strip().rstrip("/")


def curl_json(url: str, key: str, payload: dict[str, Any] | None = None, timeout: int = 240) -> tuple[int, bytes]:
    curl = shutil.which("curl")
    if not curl:
        die("curl is required but was not found")

    with tempfile.NamedTemporaryFile(delete=False) as body_file:
        body_path = Path(body_file.name)
    try:
        cmd = [
            curl,
            "-sS",
            "-m",
            str(timeout),
            "-o",
            str(body_path),
            "-w",
            "%{http_code}",
            url,
            "-H",
            f"Authorization: Bearer {key}",
        ]
        if payload is not None:
            cmd.extend(["-H", "Content-Type: application/json", "-d", json.dumps(payload, ensure_ascii=False)])

        result = subprocess.run(cmd, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            stderr = result.stderr.strip()
            die(f"Network request failed: {stderr or 'curl exited with a non-zero status'}", exit_code=2)

        status_text = result.stdout.strip()
        status = int(status_text) if status_text.isdigit() else 0
        return status, body_path.read_bytes()
    finally:
        try:
            body_path.unlink()
        except FileNotFoundError:
            pass


def parse_json_response(status: int, raw: bytes) -> dict[str, Any]:
    try:
        body = json.loads(raw.decode("utf-8", "replace"))
    except json.JSONDecodeError:
        preview = raw[:300].decode("utf-8", "replace")
        die(f"Non-JSON response from gateway, status={status}, preview={preview!r}")

    if 200 <= status < 300:
        return body

    error = body.get("error") if isinstance(body, dict) else None
    summary = {
        "status": status,
        "type": error.get("type") if isinstance(error, dict) else None,
        "code": error.get("code") if isinstance(error, dict) else None,
        "message": error.get("message") if isinstance(error, dict) else body.get("message") if isinstance(body, dict) else None,
    }
    die("API request failed: " + json.dumps(summary, ensure_ascii=False))


def unique_path(path: Path, force: bool) -> Path:
    if force or not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for idx in range(2, 1000):
        candidate = parent / f"{stem}-{idx}{suffix}"
        if not candidate.exists():
            return candidate
    die(f"Could not find a non-existing output path for {path}")


def save_url(url: str, key: str, out_path: Path, force: bool) -> Path:
    curl = shutil.which("curl")
    if not curl:
        die("curl is required but was not found")

    out_path = unique_path(out_path, force)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [curl, "-sS", "-L", "-m", "240", "-o", str(out_path), url]
    host = urlparse(url).netloc
    if host and "openai" not in host.lower():
        cmd.extend(["-H", f"Authorization: Bearer {key}"])
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        die(f"Could not download returned image URL: {result.stderr.strip()}")
    return out_path


def save_images(body: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    data = body.get("data")
    if not isinstance(data, list) or not data:
        die("The gateway returned no image data")

    outputs: list[dict[str, Any]] = []
    out_dir = Path(args.out_dir)
    prompt_slug = slugify(args.filename_prefix or args.prompt[:48])

    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            continue

        if args.out:
            requested = Path(args.out)
            if len(data) > 1:
                requested = requested.with_name(f"{requested.stem}-{idx}{requested.suffix or '.png'}")
        else:
            requested = out_dir / f"{prompt_slug}-{idx}.png"

        requested = requested if requested.suffix else requested.with_suffix(".png")
        requested.parent.mkdir(parents=True, exist_ok=True)

        b64 = item.get("b64_json") or item.get("image_base64")
        if isinstance(b64, str) and b64:
            image_bytes = base64.b64decode(b64)
            target = unique_path(requested, args.force)
            target.write_bytes(image_bytes)
            outputs.append({"path": str(target.resolve()), "bytes": len(image_bytes)})
            continue

        url = item.get("url")
        if isinstance(url, str) and url:
            target = save_url(url, args.api_key, requested, args.force)
            outputs.append({"path": str(target.resolve()), "url_returned": True})
            continue

        outputs.append({"warning": "image item did not contain b64_json or url", "keys": sorted(item.keys())})

    if not outputs:
        die("No images could be saved from the gateway response")
    return outputs


def read_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8").strip()
    else:
        prompt = (args.prompt or "").strip()
    if not prompt:
        die("A prompt is required. Pass --prompt or --prompt-file.")
    return prompt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="通过配置好的 QS Image 2 网关生成图片")
    parser.add_argument("--prompt", help="Image prompt")
    parser.add_argument("--prompt-file", help="Read the prompt from a UTF-8 text file")
    parser.add_argument("--model", default="gpt-image-2", help="Image model to use")
    parser.add_argument("--quality", default="medium", choices=["low", "medium", "high", "auto"])
    parser.add_argument("--size", default="1024x1024", help="Image size, for example 1024x1024")
    parser.add_argument("--n", type=int, default=1, help="Number of images")
    parser.add_argument("--out", help="Output file path")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory")
    parser.add_argument("--filename-prefix", help="Prefix for generated filenames")
    parser.add_argument("--force", action="store_true", help="Overwrite the requested output path")
    parser.add_argument("--list-models", action="store_true", help="List image-related models and exit")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help=argparse.SUPPRESS)
    parser.add_argument("--auth", default=str(DEFAULT_AUTH_PATH), help=argparse.SUPPRESS)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config = load_config(Path(args.config))
    key = load_key(Path(args.auth))
    base_url = resolve_base_url(config)
    args.api_key = key

    if args.list_models:
        status, raw = curl_json(f"{base_url}/models", key, timeout=120)
        body = parse_json_response(status, raw)
        ids = [item.get("id") for item in body.get("data", []) if isinstance(item, dict)]
        image_ids = [model_id for model_id in ids if isinstance(model_id, str) and "image" in model_id.lower()]
        print(json.dumps({"ok": True, "status": status, "base_url": base_url, "image_models": image_ids}, ensure_ascii=False))
        return 0

    prompt = read_prompt(args)
    payload = {
        "model": args.model,
        "prompt": prompt,
        "quality": args.quality,
        "size": args.size,
        "n": args.n,
    }

    status, raw = curl_json(f"{base_url}/images/generations", key, payload=payload)
    body = parse_json_response(status, raw)
    outputs = save_images(body, args)
    print(json.dumps({"ok": True, "status": status, "model": args.model, "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
