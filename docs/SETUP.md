# 🚀 详细部署教程

> 本项目仅**发现并推送**免费游戏活动，**不会**自动登录或下单领取。支持 iPhone Bark 和安卓 ntfy，最快 5 分钟开始测试。

> **⏸️ 注意：本仓库目前完全暂停运行。** 未注册活动的 GitHub Actions 工作流，也不会向 Bark/ntfy 发送消息。以下是未来使用者的自助启用教程，不代表仓库当前在运行。

## 0. 恢复被注释的工作流（必须先做）

为了确保默认不会自动运行，项目把工作流从 `.github/workflows/` 移到了 [`templates/radar.yml`](../templates/radar.yml)。**GitHub 不会执行 `templates/` 下的文件。**

如需自行启用，Fork 本仓库后：

1. 进入 `templates/radar.yml`，点击 GitHub 文件右上角的编辑（铅笔）按钮。
2. 把文件路径由 `templates/radar.yml` 更改为 `.github/workflows/radar.yml`（也可以新建目标文件，复制模板完整内容，然后保留原模板）。
3. 找到开头被注释的事件配置：`# on:`、`#   schedule:`、`#   workflow_dispatch:` 等。在整个触发器配置块（从 `# on:` 到 `#         - test`）中，每行前面的 `# ` **都要去掉**，变成有效 YAML。
4. **只想手动运行**：先取消 `on:` 和 `workflow_dispatch:` 相关行的注释，保持 `schedule` 配置块为注释。**想每 6 小时自动运行**：两组事件都取消注释。
5. 需要 iOS 通知就在 Secrets 设置 `BARK_URL`；需要安卓通知就设置 `NTFY_TOPIC` 并把任务里两行 `# NTFY_TOPIC:` 同时取消注释（见 [安卓说明](./ANDROID.md)）。
6. 提交后 GitHub 才会把文件识别为工作流。进入 Actions 页面手动 `test` 验证。

> **停用方式**：将 `.github/workflows/radar.yml` 再移出工作流目录（放回 `templates/radar.yml`）或删除活动工作流文件。仅删 Secret 可能使任务继续触发但失败，不等于停用。

## 准备工作

- GitHub 账号和可以编辑的仓库（本项目：[EpochTX/freegame](https://github.com/EpochTX/freegame)）。
- iPhone：安装 [Bark](https://github.com/Finb/Bark)，允许通知，获取推送 URL。
- 安卓：安装 [ntfy](https://docs.ntfy.sh/subscribe/phone/)，并订阅随机主题；具体见 [安卓接入指南](./ANDROID.md)。
- **只需任选一种推送方式，也可以同时使用两种。**
- 无需 GitHub 付费订阅、VPS、游戏账户密码或额外 API Key。具体 GitHub Actions 免费额度以 GitHub 官方规则为准。

## 1. Fork 或使用现有仓库

**新部署**：Fork [EpochTX/freegame](https://github.com/EpochTX/freegame) 到自己的账户，然后按上面的第 0 步手动恢复工作流。Fork 后工作流默认不存在，不会自动运行。

**仓库维护者**：不需要 Fork；本仓库当前仍保持完全暂停状态，不必做任何操作。

## 2. 设置推送 Secret（任选 Bark 或 ntfy，也可以都设置）

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

安卓：创建一个至少 20 字符的**随机主题**，在 GitHub Secrets 中添加 `NTFY_TOPIC`，值为主题名（不是 URL），并在 ntfy App 中订阅。详细步骤：[安卓推送指南](./ANDROID.md)。**公共 ntfy.sh 主题默认公开，知道主题名的人可能订阅或发送消息。**

**避免十分钟自动过期：** 请仅填写 `https://api.day.app/YOUR_DEVICE_KEY/`，**不要**直接粘贴 Bark 示例 GET 命令、`/title/body` 或 `?group=example&ttl=600`。本项目会自动清理这些常见误输入，但建议在 GitHub Secret 中更正源地址。推送 JSON 使用 `isArchive=1`，且**不传 `ttl`**，让消息交由 Bark 历史记录管理。

**安全：** Key 是发通知用的私密凭证。不要在公开代码、Issue、README、Variables 或聊天截图中暴露。如果曾把实际 Key 发布给他人，建议先更换 Key，并在 GitHub Secret 中同步替换。

## 3. 启用工作流后的推送测试

1. 确保第 0 步已经完成；打开**你自己仓库**的 Actions → Free Games Radar。尚未恢复工作流时，这个入口不会出现。
2. 点击 **Run workflow**。
3. 将 `mode` 设为 `test` 后运行。
4. 等 Actions 运行结束，确认所有已配置的手机都收到「FreeGame Radar 测试成功」，标题应是实际发送的测试标题，不应是字面量 `title` / `body`。

**如果显示绿色但没收到推送：** 检查手机通知权限、专注模式、Bark 设备状态；也检查是不是把旧 Key 放在 Secret 中。GitHub 成功仅代表 Bark API 接受了请求，不是 Apple 推送一定展示。

## 4. 手动扫描游戏

在同一页面再次选择 **Run workflow** → `scan`。

- 检测 Epic 官方公开促销数据。
- 检测 GamerPower 列出的 Steam 免费完整游戏活动。
- 过滤大部分常见试玩、DLC、道具活动。
- 向各自**尚未通知**的设备推送新活动；每个通道按活动 ID、游戏名分别去重；相同游戏 45 天内尽量不重复提醒。
- 更新仓库里的 `FREE_GAMES.md`、`data/current.json`、`data/sent.json`。

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

当前停用模板：[`templates/radar.yml`](../templates/radar.yml)。**不在 `.github/workflows/` 中就不会执行。**

默认配置：

```yaml
schedule:
  - cron: "17 1,7,13,19 * * *"
```

**只有正式启用后**，才会每 6 小时扫描一次，北京时间约 09:17、15:17、21:17、次日 03:17。目前没有自动扫描。

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

- **当前仓库没新的 Actions 运行：** 这是正常的，工作流已移到 `templates/` 且事件块有 `#` 注释。
- **启用后**：在 Actions 页面可查看运行成功或失败。
- **绿色通过但没有游戏提醒：** 可能没有新游戏，或者已有去重记录。
- **未设置推送 Secret：** 至少需要 `BARK_URL` 或 `NTFY_TOPIC` 之一；注意 Secret 所属仓库。
- **Bark 推送失败：** 检查推送 Key 是否已过期及联网情况。
- **ntfy 无法送达：** 核对 App 主题和 `NTFY_TOPIC`、安卓通知权限、后台电池限制、`ntfy.sh` 访问是否畅通。
- **偶尔重复提醒：** 以前更新仓库文档时可能导致状态提交冲突，现已增加重试提交、按通道分离和 45 天同游戏指纹；若任务中断在「通知已发、状态尚未提交」之间仍可能重复。
- **扫描数据失败：** 上游 API 可能暂时不可用，重试或参考 [FAQ](./FAQ.md)。
- **状态提交失败：** 确认 Action 工作流中的 `permissions: contents: write` 可用，并检查仓库是否启用了阻止 Bot 推送的分支保护。
- **公开仓库停用定时任务：** GitHub 可能在长时间无活动后停用 schedule，需要重新启用。

## 进一步阅读

- [项目首页](../README.md)
- [常见问题](./FAQ.md)
- [安全须知](../SECURITY.md)
- [仓库介绍文案和 Topics 建议](./REPOSITORY.md)
