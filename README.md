# QS Image2 Gateway

这是一个用于 Codex 的全局生图 Skill，可以通过你本地配置好的 Image 2 网关生成图片。

它适合这样的使用方式：API key 存在本地 Codex 鉴权文件里，网关地址存在 Codex 配置文件里；以后在任何 Codex 会话中，只要提出“生图、生成图片、画图、Image 2、gpt-image-2”等请求，就可以自动走这个 Skill。

本 Skill 默认从这里读取 OpenAI 兼容 API key：

```text
~/.codex/auth.json
```

并从这里读取当前 provider 的网关地址：

```text
~/.codex/config.toml
```

默认使用模型：

```text
gpt-image-2
```

调用接口时不添加 `/v1` 前缀：

```text
{base_url}/images/generations
```

## 功能说明

- 自动响应生图类请求，例如：生图、生成图片、画图、文生图、Image 2、`gpt-image-2`、image generation。
- 从 `~/.codex/auth.json` 读取 `OPENAI_API_KEY`。
- 从 `~/.codex/config.toml` 读取当前启用的 `model_provider` 和对应的 `base_url`。
- 调用 `{base_url}/images/generations` 生成图片。
- 默认把生成的 PNG 图片保存到 `output/imagegen/`。
- 不打印、不回显、不暴露 API key。

## 安装方式

把这个 Skill 文件夹复制到用户级 Codex Skills 目录：

```bash
mkdir -p "$HOME/.agents/skills"
cp -R qs-image2-gateway "$HOME/.agents/skills/qs-image2-gateway"
```

然后重启 Codex，或者新开一个任务，让技能列表刷新。

## 本地配置要求

`~/.codex/auth.json` 需要包含：

```json
{
  "OPENAI_API_KEY": "your-api-key"
}
```

`~/.codex/config.toml` 需要包含一个带 `base_url` 的 provider：

```toml
model_provider = "sub2api"

[model_providers.sub2api]
name = "sub2api"
base_url = "https://your-gateway.example.com/"
wire_api = "responses"
requires_openai_auth = true
```

这个 Skill 会动态读取当前启用的 provider，所以修改 `model_provider` 后，脚本下次运行会自动使用新的网关地址。

## 在 Codex 中使用

自然语言直接触发：

```text
帮我生成一张科技感的产品海报
```

明确指定使用 QS Image2 Gateway：

```text
用 QS Image2 Gateway 生成一张图：一个蓝色科技风的数据安全平台主视觉，16:9，适合 PPT 首页。
```

显式调用 Skill：

```text
$qs-image2-gateway 生成一张图：一个简洁高级的 AI 数据中台插画，白底，蓝绿色点缀。
```

## 手动运行脚本

生成一张图片：

```bash
./scripts/generate_image2.py \
  --prompt "一张简洁的蓝色科技风图标，白底，无文字" \
  --quality low \
  --size 1024x1024 \
  --out-dir output/imagegen
```

列出当前网关可用的 image 模型：

```bash
./scripts/generate_image2.py --list-models
```

## 默认参数

- 模型：`gpt-image-2`
- 质量：`medium`
- 尺寸：`1024x1024`
- 张数：`1`
- 输出目录：`output/imagegen/`

常用 `gpt-image-2` 尺寸：

- `1024x1024`
- `1536x1024`
- `1024x1536`
- `2048x1152`
- `3840x2160`
- `2160x3840`

## 文件结构

```text
qs-image2-gateway/
├── SKILL.md
├── agents/
│   └── openai.yaml
└── scripts/
    └── generate_image2.py
```

## 安全说明

不要提交 `~/.codex/auth.json`、`.env` 或任何包含 API key 的本地文件。

辅助脚本只会在本地读取 API key，并通过 `Authorization` 请求头发送给配置中的网关。脚本不会打印 key。
