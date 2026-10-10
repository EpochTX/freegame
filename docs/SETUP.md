# 🚀 FreeGame Radar：部署与配置

无需自建服务器或游戏账号登录信息。项目使用 GitHub Actions 定时生成 [免费游戏清单](../FREE_GAMES.md)，手机通知完全可选。

## 一、启用免费扫描

1. Fork [EpochTX/freegame](https://github.com/EpochTX/freegame) 到自己的 GitHub 账号。
2. 确认仓库存在 [`.github/workflows/radar.yml`](../.github/workflows/radar.yml)。
3. 如 GitHub 对 Fork 禁用了 Actions，请在仓库 **Actions** 页面手动启用。
4. 运行 **Actions → Free Games Radar → Run workflow → mode: scan**。
5. 查看运行日志，并打开 [`FREE_GAMES.md`](../FREE_GAMES.md) 检查是否更新。

**没有推送密钥也完全可以使用。** 脚本会正常抓取、过滤、更新活动清单，且不会发送任何手机通知。

## 二、可选：iOS / iPadOS Bark 推送

希望收到游戏通知时再配置。

1. 安装 [Bark](https://github.com/Finb/Bark)，允许手机通知。
2. 复制 Bark App 中的**完整 HTTPS 推送 URL**，其格式为：
   ```text
   https://api.day.app/YOUR_DEVICE_KEY/
   ```
3. 前往自己的 GitHub 仓库 **Settings → Secrets and variables → Actions → New repository secret**。
4. Name 填 `BARK_URL`，Secret 填完整 URL。
5. 打开 Actions → Free Games Radar → Run workflow，选择 `test` 测试。

**关闭 Bark 通知而保留免费扫描：** 删除仓库的 `BARK_URL` Secret 即可。若没有配置安卓 ntfy，就不会有任何手机推送。

注意：请勿复制整段 `curl` 命令；Bark 示例路径的 `/title/body` 和 `?ttl=600` 也不要填入 Secret。脚本会清理常见示例参数，以真正的游戏信息发送 JSON POST，并使用存档设置，不主动指定短期 TTL。

## 三、可选：Android ntfy 推送

参见 [Android ntfy 详细教程](./ANDROID.md)。概括为：

1. 在安卓安装 ntfy App，并订阅高随机度主题。
2. 在仓库 Secrets 新增 `NTFY_TOPIC`，填入主题名，不包含 URL。
3. 编辑 [`.github/workflows/radar.yml`](../.github/workflows/radar.yml)。
4. 在测试任务和扫描任务中，分别取消一行 `# NTFY_TOPIC: ${{ secrets.NTFY_TOPIC }}` 前的 `# `，**共两处**。
5. 运行 `test` 检查安卓通知。

无需同时安装 Bark 和 ntfy；也可双端使用。公共 ntfy 主题默认没有访问控制，请勿发送隐私信息。

## 四、运行模式

**手动运行：** GitHub → Actions → Free Games Radar → Run workflow。

| mode | 说明 |
| --- | --- |
| `scan` | 立即检查限免活动，更新清单；已配置通知通道时只推送新活动 |
| `test` | 仅发送测试通知；无推送密钥时正常跳过 |

**定时运行：** 每 6 小时扫描一次，配置位于 [工作流](../.github/workflows/radar.yml)。时间为 UTC 01:17、07:17、13:17、19:17，换算为北京时间 09:17、15:17、21:17、次日 03:17。

GitHub 定时触发可能延迟。提交代码导致的 `push` 事件只运行离线测试，不进行游戏扫描或推送。

## 五、可选变量

GitHub **Settings → Secrets and variables → Actions → Variables**：

| Variable | 默认值 | 说明 |
| --- | --- | --- |
| `EPIC_COUNTRY` | `CN` | Epic 查询地区，如 `US` |
| `EPIC_LOCALE` | `zh-CN` | Epic 语言，如 `en-US` |
| `MAX_PUSH` | `8` | 每通道每次推送数量上限（1–20） |

以上属于非敏感配置，可放在 Variables。真实 Bark URL 和 ntfy 随机主题仍应使用 Secrets。

## 六、本地测试

需要 Python 3.11+，无需安装额外 Python 依赖：

```bash
python -m unittest discover -s tests -v
python radar.py
```

不设置任何推送环境变量时，第二个命令只会更新本地清单文件，不会通知手机。要测试通知，请先通过环境变量安全提供个人密钥，再运行 `python radar.py --test-push`，避免将密钥写入脚本或上传到仓库。

## 七、排错

- **扫描成功，没有推送：** 如果未配置 `BARK_URL` / `NTFY_TOPIC`，属于预期行为。
- **有推送 Secret 但没收到：** 用 `test` 模式检查应用通知权限、Secret 名称与地址是否正确。
- **安卓未推送：** 检查工作流的两处 ntfy 变量是否已经取消注释。
- **清单没有更新：** 检查 Epic / GamerPower 数据源连接与 Actions 扫描日志。
- **状态无法保存：** 检查仓库对 GitHub Actions 的 `contents: write` 权限与 `main` 分支保护。
- **偶有重复提醒：** 推送成功后状态提交未完成时，仍可能再次发送。系统按活动 ID 与同游戏 45 天冷却期尽量减少重复。

## 安全提示

本项目不需要 Epic / Steam 账号密码、浏览器 Cookie、短信验证码或游戏登录 Token。不要在仓库、Issue、PR、公开日志中上传真实密钥；任何泄露的密钥都应在服务提供方轮换。

[← 返回 README](../README.md) · [FAQ](./FAQ.md) · [安全说明](../SECURITY.md)
