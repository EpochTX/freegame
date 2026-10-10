# 🔐 安全与隐私说明

FreeGame Radar 使用公开游戏促销信息，不需要 Epic Games、Steam 或其他游戏平台的账号密码、Cookie、验证码或登录 Token。

## 敏感信息管理

- 将 Bark 推送地址保存为 GitHub Actions Secret：`BARK_URL`。
- Android ntfy 主题建议生成高随机度名称，并保存为 Secret：`NTFY_TOPIC`。
- 不要把真实密钥放进 README、源码、普通 Variables、Issue、Pull Request、评论、Actions 日志或截图。
- 推荐定期检查依赖与 Actions 工作流变动，避免在不可信的代码中暴露 Secrets。

## 推送机制

- 未设置任何通知 Secret 时，只更新免费游戏列表，不发送推送。
- Bark 通知通过 HTTPS 请求发送到 Bark 服务器。
- Android ntfy 仅在工作流中取消两处 `NTFY_TOPIC` 注释，并设置对应 Secret 后启用。
- 公共 `ntfy.sh` 主题通常不具备强制访问控制；知道主题名的其他人可能订阅或发送消息，**不要通过公共主题发送私密信息**。
- 项目通知内容仅包含公开的游戏活动信息。

## 密钥泄露处理

1. 在对应服务端更换或撤销已暴露的密钥。
2. 更新 GitHub 仓库中的相应 Secret。
3. 检查公开文件、日志与提交记录是否含敏感信息。
4. 如果密钥已写入 Git 提交，不能仅靠删除文件最新版来消除历史泄露；应按 GitHub 官方安全指引处理仓库历史。

## 漏洞报告

请通过不包含敏感信息的 [GitHub Issue](https://github.com/EpochTX/freegame/issues) 说明可复现问题。若需要分享安全敏感细节，请优先使用 GitHub 提供的私密漏洞报告渠道（若仓库已启用）；切勿在公开 Issue 中发布凭证。

## 免责声明

本项目与 Epic Games、Valve / Steam、GamerPower、Bark、ntfy 无官方关联。使用本项目应遵守游戏平台及数据源的服务条款。

[← 返回 README](./README.md)
