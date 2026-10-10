# 🤖 安卓接入指南：ntfy

免费游戏雷达支持两个独立的通知渠道：

- iPhone：**Bark**（`BARK_URL`）。
- Android：**ntfy**（`NTFY_TOPIC`）。

**目前仓库默认启用 iPhone Bark、关闭安卓 ntfy。** 安卓实现代码已保留，但 GitHub Actions 中有两行 `NTFY_TOPIC` 被注释，需要使用者自行取消注释启用。启用后两个渠道可同时使用，也可只用其中一个。不需要部署服务器或提供游戏账号 Cookie。

## 1. 安装 ntfy

官方项目：[ntfy](https://github.com/binwiederhier/ntfy) · [Android 客户端说明](https://docs.ntfy.sh/subscribe/phone/)

Android 应用可通过 Google Play 或 F-Droid 安装。打开 App 后允许通知权限。

- Google Play 版本通常借助 FCM 处理推送；请确保设备具备可用的相关服务。
- F-Droid 版本可使用后台连接，不依赖 Google 服务；可能更耗电，需注意国产系统的后台限制。
- 使用公共服务 `ntfy.sh` 需要设备能连接该域名；具体取决于网络环境。

## 2. 生成一个不容易被猜到的主题名

ntfy 公共服务器上的主题**默认没有访问控制**，任何知道主题名的人都可能订阅和发送消息，所以**千万不要用** `games`、`freegame`、手机号等简单名称。

可在电脑终端运行以下命令生成随机主题（只是生成字符串，不联网）：

```bash
python -c "import secrets; print('freegame_' + secrets.token_urlsafe(24))"
```

得到类似 `freegame_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX` 的随机值，**不要公开分享或提交到仓库**。

> ntfy 的随机主题不等于真正的端到端加密。适合推送公开游戏信息；如需保护隐私，应使用有访问控制的服务器。

## 3. 在安卓订阅主题

1. 打开 ntfy App → 点击新增订阅（**Subscribe to topic**）。
2. 服务器保持 `ntfy.sh`。
3. 输入你生成的**完整主题名**并订阅。
4. 允许后台通知；必要时解除系统对 ntfy 的省电限制。

同一个主题可以在多台安卓设备订阅，便于同步接收，但所有持有主题的人也可能收到消息。

## 4. GitHub 设置 Secret

打开自己的 GitHub 仓库：

**Settings → Secrets and variables → Actions → New repository secret**

填写：

| 字段 | 内容 |
| --- | --- |
| Name | `NTFY_TOPIC` |
| Secret | 刚才生成的**主题名本身**，不要带 `https://ntfy.sh/` |

如果你之前已经配置了 Bark，请保留 `BARK_URL`：两台设备启用后会分别接收同一批活动通知。**仅新增 Secret 不会开启安卓推送，仍需下一步取消注释。**

仓库入口：[freegame Secrets](https://github.com/EpochTX/freegame/settings/secrets/actions)

## 5. 取消 GitHub Actions 中的两处注释（必做）

只有设置 Secret 还不够。**默认的安卓推送处于关闭状态**，需要让工作流把 `NTFY_TOPIC` 传给脚本。

1. 在你自己的仓库打开 [`.github/workflows/radar.yml`](../.github/workflows/radar.yml)。
2. 点击铅笔按钮编辑。
3. 找到 `Test configured push channels` 下方 `env:` 中的注释行。
4. 再找到 `Scan free games and notify` 下方 `env:` 中的同一行。
5. **两处都删除行首的 `# `**，使配置变成：

```yaml
env:
  BARK_URL: ${{ secrets.BARK_URL }}
  NTFY_TOPIC: ${{ secrets.NTFY_TOPIC }}
```

上面只展示 `env` 的相关两行；原有 `EPIC_COUNTRY`、`EPIC_LOCALE`、`MAX_PUSH` 配置请保留。

6. 提交更改，回到 Actions 页面测试。这里的 `NTFY_TOPIC` 是 **Secret 名称**，不要把实际随机主题值写进工作流文件。

**关闭安卓通知：** 把上述两处 `NTFY_TOPIC` 的行首重新加上 `# `，提交即可。不会影响 iPhone Bark。

**只用安卓：** 取消两处 `NTFY_TOPIC` 注释、设置 Secret；`BARK_URL` 这个 Secret 没有配置也能运行。

## 6. 测试与正常扫描

1. 先确认已取消 **两处** `NTFY_TOPIC` 注释，再进入 [Actions → Free Games Radar](https://github.com/EpochTX/freegame/actions/workflows/radar.yml)。
2. `Run workflow` → 选 `test`：向**所有已配置通道**各发一条测试消息。
3. 确认安卓能收到「FreeGame Radar 测试成功」，点击可打开 GitHub 项目。
4. `Run workflow` → 选 `scan`：检查当前免费游戏，推送给尚未通知过的各个通道。

新的 ntfy 渠道在首次扫描时，可能会收到几个当前有效活动；之后按通道与游戏活动去重。即使 Bark 已收到过，安卓仍能收到自己第一次的活动通知。

## 7. 常见问题

**安卓收不到通知：** 先确认工作流中两处 `NTFY_TOPIC` 已取消注释，再检查 ntfy App 订阅主题是否和 GitHub Secret 完全一致、通知权限、后台/省电策略、`ntfy.sh` 的网络可达性。尝试保持 App 打开，再运行 `test`。

**有没有时效限制：** 公共 ntfy 服务可能限制消息存储时长；免费游戏雷达仓库中的 [当前活动清单](../FREE_GAMES.md) 会持续更新，便于回看。不能承诺 ntfy 服务永久保存历史。

**能只用安卓、不用 iPhone 吗：** 可以，删除 `BARK_URL` Secret 或留空，只保留 `NTFY_TOPIC`。反过来仅用 Bark 也可正常运行。

**同一个游戏重复通知？** 代码会按「通道 + 活动 ID」去重，并用游戏名称指纹在 45 天内抑制相同游戏的多条赠送活动。某些数据源更名或仓库状态写回失败仍可能造成少量重复，不承诺绝对零重复。

**能点通知直接领取吗？** 点击通知可以打开游戏活动页；仍需要手动确认领取，不能自动入库。

[← 返回项目首页](../README.md) · [常见问题](./FAQ.md) · [安全说明](../SECURITY.md)
