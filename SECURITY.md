# Security Policy / 安全策略

## Supported Versions / 支持版本

This project currently supports security fixes on the `main` branch only.

本项目目前只在 `main` 分支接受安全修复。

## Reporting a Vulnerability / 报告漏洞

Please do not open a public issue for sensitive security reports.

请不要通过公开 issue 报告敏感安全问题。

Report privately with:

- A clear description of the vulnerability.
- Reproduction steps or proof of concept, if safe to share.
- Impact, affected configuration, and any known mitigation.

请在私下报告中包含：

- 漏洞说明。
- 可安全分享的复现步骤或 PoC。
- 影响范围、受影响配置和已知缓解方式。

If GitHub private vulnerability reporting is available for this repository, use it. Otherwise contact the maintainer through the repository owner profile.

如果仓库启用了 GitHub 私有漏洞报告，请优先使用；否则请通过仓库所有者主页联系维护者。

## Security Expectations / 安全要求

- Never commit `.env`, `.env.deploy`, API keys, passwords, tokens, generated images with private data, or database dumps.
- Replace all example secrets before deployment.
- Keep `CORS_ORIGINS` restricted to trusted origins in production.
- Keep API docs disabled in production unless explicitly needed.

- 不要提交 `.env`、`.env.deploy`、API key、密码、token、包含私密数据的生成图片或数据库导出。
- 部署前必须替换所有示例密钥。
- 生产环境 `CORS_ORIGINS` 只能包含可信来源。
- 生产环境默认关闭 API 文档，除非确有需要。
