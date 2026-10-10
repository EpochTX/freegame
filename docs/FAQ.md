# ❓ FreeGame Radar 常见问题

## 1. 不配置 Bark 或 ntfy，也能使用吗？

**可以。** GitHub Actions 每 6 小时扫描一次，并自动更新 [FREE_GAMES.md](../FREE_GAMES.md)。未配置 `BARK_URL` 和 `NTFY_TOPIC` 时，不会发送任何通知，也不会因为缺少密钥而报错。

## 2. 怎么关闭手机推送但保留定时扫描？

iPhone Bark：删除仓库 Actions Secrets 中的 `BARK_URL`。

Android ntfy：删除 `NTFY_TOPIC` Secret，或在 [工作流](../.github/workflows/radar.yml) 中注释两处 `NTFY_TOPIC` 环境变量。

如果两个通道都未配置，扫描仍正常进行；可以只看游戏清单。

## 3. 这是自动领取游戏的工具吗？

不是。它只负责查找、整理和提醒免费游戏活动；不登录游戏平台，也不自动下单。点击通知进入活动页面后仍需用户自行领取。

## 4. 为什么 Steam 的链接打开 GamerPower？

Steam 活动使用 [GamerPower API](https://www.gamerpower.com/api-read)。其数据可能包含第三方赠送 Key、领取任务及地区要求，不一定能直接在 Steam 商店免费入库。

## 5. 为什么游戏页面不是免费？

地区、促销时间、账号资格及上游数据更新时间均可能产生差异。Epic 默认查询 `CN` 地区，其他地区需配置 `EPIC_COUNTRY`。以真实商店页面和结账价格为准。

## 6. 免费周末、试玩和 DLC 会不会误报？

程序会过滤常见的 Free Weekend、Free Trial、Demo、DLC、Loot 等类型，但由于数据源字段不一致，无法保证完全排除。

## 7. 为什么没有 Bark 消息？

先确认仓库设置了有效的 `BARK_URL` Secret，然后运行 Actions → Free Games Radar → `test`，检查 Bark 通知权限、网络和设备状态。

如果测试成功，但正式扫描没有提示，可能本次没有新活动，或者已经去重。

## 8. 为什么 Bark 历史通知会提前消失？

使用 Bark 完整推送 URL，格式为 `https://api.day.app/YOUR_DEVICE_KEY/`。不要加入示例用的 `/title/body` 或 `?ttl=600`。其中 `ttl=600` 会设置 10 分钟的消息保留期。项目通过 JSON POST 发送真实标题和内容，启用历史存档，且不主动设置短 TTL；最终保留仍受 Bark App 和服务器设置影响。

## 9. 安卓怎么设置？

安装 [ntfy](https://docs.ntfy.sh/subscribe/phone/)，订阅不可预测的随机主题，把主题名称保存为 GitHub Secret `NTFY_TOPIC`，然后取消工作流中两处 `# NTFY_TOPIC:` 注释。详见 [Android 教程](./ANDROID.md)。

## 10. 为什么同一个游戏可能被重复提醒？

程序按活动 ID 和规范化游戏名称、每个通知通道分别去重；同游戏在 45 天内尽量不重复推送。但如果出现新标题、相同游戏的新活动、GitHub 状态提交失败或任务在推送后突然中断，仍可能偶尔重复。

## 11. 为什么重新启用推送后一下子有很多通知？

启用某个此前没有通知记录的通道时，当前仍有效的活动可能被视为首次发现。每次推送数量受 `MAX_PUSH` 限制，默认最多 8 条/通道。

## 12. GitHub Actions 没有准时执行？

GitHub `schedule` 是尽力调度，不保证绝对准时，高峰期可能延迟甚至跳过。可以在 Actions 页面手动选 `scan` 检查。

## 13. 工作流执行成功，游戏清单却没有变化？

没有新活动时清单内容可能不变。若一直为空，请检查扫描日志、上游 API 是否可用、Epic 地区配置和过滤规则。

## 14. 为什么状态文件无法更新？

工作流需具备 `contents: write` 权限，还可能受 GitHub 仓库设置或 `main` 分支保护规则影响。检查失败的 `Commit updated state and game list` 步骤。

## 15. 会上传我的游戏账号或通知密钥吗？

不需要 Epic / Steam 游戏账号凭证。推送密钥需存放在 GitHub Actions Secrets，运行过程中会用于向指定推送服务器发送公开活动信息。请勿将任何真实密钥写进公开仓库文件。公共 `ntfy.sh` 主题默认没有访问控制，需注意其可见性。

[← 返回 README](../README.md) · [完整部署教程](./SETUP.md) · [安全说明](../SECURITY.md)
