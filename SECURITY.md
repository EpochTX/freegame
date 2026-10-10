# 🔒 安全说明

本项目的目标是：**在不取得 Epic / Steam 登录信息的情况下，发现免费游戏并用 Bark 通知你**。

## 不应提交到 GitHub 的资料

- Bark 设备密钥与推送 URL（例如完整 `https://api.day.app/...`）。
- ntfy 随机主题名（不应发布于公开代码；公共 ntfy 主题默认没有强制身份验证）。
- Epic / Steam 账号密码、浏览器 Cookie、Token、短信验证码、备用码。
- 自建 Bark 服务器密码及其他服务的 API Key。

请将 Bark URL 保存为 **Repository Secret**：`BARK_URL`；安卓 ntfy 主题保存为 `NTFY_TOPIC`。**不要**把它写入 README、普通 Variables、Issue、Discussion、Pull Request、Actions 日志或截图中。

## 密钥泄露如何处理

如果 Bark Key 曾贴在公开页面或聊天内容中：

1. 在 Bark 端更换或撤销旧密钥（以所用 Bark 服务支持的管理方式为准）。
2. 更新 GitHub Actions Secret `BARK_URL`。
3. 用 Actions 的 `test` 模式确认新密钥可用。
4. 若密钥曾写入 Git 提交，删除工作树中的明文并清理 Git 历史中敏感信息；**不要认为删掉最新版本就意味着泄露已消除**。

## 依赖和网络边界

- 本项目无外部 pip 依赖，使用 Python 标准库。
- GitHub Actions 在 GitHub 托管的运行环境中执行；该环境内的脚本**会读取** `BARK_URL` 或 `NTFY_TOPIC`，用于向推送服务发送通知。
- 免费的公共 `ntfy.sh` 主题默认没有身份验证；知道主题的人可能查看或发送此主题通知。不要用它来传输私密数据。
- 仓库 Actions 工作流可以修改时，应特别审查后续对 `radar.py` 和 workflow 文件的提交。
- 数据请求依赖 Epic 公开促销接口及 GamerPower API；上游信息可能有误或延迟。

## 漏洞报告

请不要在公开 Issue 中分享任何实际密码、Token、Cookie 或密钥。可以先发起一个不含敏感信息的 Issue 描述问题类型，并使用 GitHub 支持的私密报告途径与维护者沟通具体细节（如仓库启用了私密漏洞报告）。

## 使用声明

本项目与 Epic Games、Valve/Steam、GamerPower、Bark 无官方关联；不得用它来规避平台验证机制或批量滥用福利。

[← 返回项目首页](./README.md)
