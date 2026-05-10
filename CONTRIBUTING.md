# Contributing / 贡献指南

Thanks for helping improve Image API Site.

感谢你帮助改进 Image API Site。

## Scope / 范围

Before opening a pull request, please check existing issues and recent commits to avoid duplicated work.

提交 PR 前请先检查现有 issue 和近期提交，避免重复工作。

## Development / 开发

Use the setup commands in `README.md`.

请使用 `README.md` 中的开发环境命令。

Common checks:

```bash
cd frontend
npm ci
npm run build
```

```bash
cd backend
uv run pytest
```

If local Python does not match the required version, use the Docker-based backend test command documented in `README.md`.

如果本机 Python 版本不匹配，请使用 `README.md` 里的 Docker 后端测试命令。

## Pull Requests / PR 要求

- Keep changes focused and explain user-facing behavior changes.
- Do not include secrets, generated local files, `storage/`, `frontend/dist/`, or local databases.
- Add or update tests when behavior changes.
- Update documentation when setup, deployment, security, or API behavior changes.
- For UI changes, include screenshots or a short screen recording when practical.

- 保持改动聚焦，并说明面向用户的行为变化。
- 不要提交密钥、本地生成文件、`storage/`、`frontend/dist/` 或本地数据库。
- 行为变化需要补充或更新测试。
- 设置、部署、安全或 API 行为变化需要更新文档。
- UI 改动尽量附截图或简短录屏。

## Conduct / 行为准则

All contributors are expected to follow `CODE_OF_CONDUCT.md`.

所有贡献者都应遵守 `CODE_OF_CONDUCT.md`。
