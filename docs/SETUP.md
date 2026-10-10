# 🚀 详细部署教程

> 本项目仅**发现并推送**免费游戏活动，**不会**自动登录或下单领取。最快 5 分钟开始测试。

## 准备工作

- GitHub 账号和可以编辑的仓库（本项目：[EpochTX/freegame](https://github.com/EpochTX/freegame)）。
- iPhone 安装 [Bark](https://github.com/Finb/Bark)，允许通知，并确认 Bark 已提供自己的推送地址。
- 无需 GitHub 付费订阅、VPS、游戏账户密码或额外 API Key。具体 GitHub Actions 免费额度以 GitHub 官方规则为准。

## 1. Fork 或使用现有仓库

**新部署**：Fork [EpochTX/freegame](https://github.com/EpochTX/freegame) 到自己的账户。Fork 后请确认 GitHub 允许该 Fork 运行 Actions。

**当前仓库维护者**：无需 Fork，直接使用已有的 `main` 分支。

## 2. 设置 Bark Secret（最重要）

1. 在你自己的仓库中打开 **Settings**。
2. 左侧点击 **Secrets and variables → Actions**。
3. 点击 **New repository secret**。
4. Name 填 `BARK_URL`。
5. Secret 填入 Bark App 提供的完整 HTTPS URL，例如：
   ```text
   https://api.day.app/YOUR_DEVICE_KEY/
   ```
6. 保存。

请保持末尾完整结构即可；**不要**添加 `/title/body`，本项目使用 POST 发送标题和内容。

**安全：** Key 是发通知用的私密凭证。不要在公开代码、Issue、README、Variables 或聊天截图中暴露。如果曾把实际 Key 发布给他人，建议先更换 Key，并在 GitHub Secret 中同步替换。

## 3. 测试 Bark

1. 打开 [Actions → Free Games Radar](https://github.com/EpochTX/freegame/actions/workflows/radar.yml)（Fork 用户请切换到自己仓库的同名页面）。
2. 点击 **Run workflow**。
3. 将 `mode` 设为 `test` 后运行。
4. 等 Actions 运行结束，确认手机收到「FreeGame Radar 测试成功」。

**如果显示绿色但没收到推送：** 检查手机通知权限、专注模式、Bark 设备状态；也检查是不是把旧 Key 放在 Secret 中。GitHub 成功仅代表 Bark API 接受了请求，不是 Apple 推送一定展示。

## 4. 手动扫描游戏

在同一页面再次选择 **Run workflow** → `scan`。

- 检测 Epic 官方公开促销数据。
- 检测 GamerPower 列出的 Steam 免费完整游戏活动。
- 过滤大部分常见试玩、DLC、道具活动。
- 通知未记录的新活动，更新仓库里的 `FREE_GAMES.md`、`data/current.json`、`data/sent.json`。

如果本次没有新活动，**不会**强制发送「一切正常」通知。可以看 [当前活动清单](../FREE_GAMES.md)。

## 5. 可选：切换 Epic 地区

想看其他地区，例如美国，请进入：

**Settings → Secrets and variables → Actions → Variables → New repository variable**

| 名称 | 示例 | 默认 |
| --- | --- | --- |
| `EPIC_COUNTRY` | `US` | `CN` |
| `EPIC_LOCALE` | `en-US` | `zh-CN` |
| `MAX_PUSH` | `5` | `8` |

请注意 Epic 的商城页面、账号实际地区和网络访问地区可能影响可领取资格。

## 6. 自动运行与修改频率

工作流文件：[`.github/workflows/radar.yml`](../.github/workflows/radar.yml)

默认配置：

```yaml
schedule:
  - cron: "17 1,7,13,19 * * *"
```

每 6 小时扫描一次，北京时间约 09:17、15:17、21:17、次日 03:17。

希望每天 10:00 左右检查一次，可以改为：

```yaml
schedule:
  - cron: "0 2 * * *"
```

因为 GitHub 使用 UTC，且工作流可能晚于预定时间执行，所以这是**大致时刻**而非秒级计划任务。

## 7. 本地调试（可选）

Python 3.11+：

```bash
python -m unittest discover -s tests -v
```

在你的终端环境设置好 `BARK_URL` 后：

```bash
python radar.py --test-push  # 只验证通知
python radar.py              # 正式扫描
```

代码不需要额外 pip 包。Windows PowerShell 可用 `$env:BARK_URL="你的推送 URL"` 临时设置环境变量；不要把它写进提交的脚本。

## 8. 检查运行与故障

- **Actions 页面**可以查看脚本执行成功或失败。
- **绿色通过但没有游戏提醒：** 可能没有新游戏，或者已有去重记录。
- **`Missing BARK_URL`：** Secret 不存在、拼写错、设置到了其他仓库或环境。
- **`Bark 推送失败`：** 检查推送 Key 是否已过期及联网情况，勿公开完整日志中的敏感字段。
- **扫描数据失败：** 上游 API 可能暂时不可用，重试或参考 [FAQ](./FAQ.md)。
- **状态提交失败：** 确认 Action 工作流中的 `permissions: contents: write` 可用，并检查仓库是否启用了阻止 Bot 推送的分支保护。
- **公开仓库停用定时任务：** GitHub 可能在长时间无活动后停用 schedule，需要重新启用。

## 进一步阅读

- [项目首页](../README.md)
- [常见问题](./FAQ.md)
- [安全须知](../SECURITY.md)
- [仓库介绍文案和 Topics 建议](./REPOSITORY.md)
