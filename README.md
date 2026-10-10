<div align="center">

# 🎮 FreeGame Radar

**Epic / Steam 免费游戏雷达 · 自动推送到 iPhone 和 Android**

![Status](https://img.shields.io/badge/Status-Paused-lightgrey)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/Automation-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)
![Bark](https://img.shields.io/badge/iOS-Bark-27AE60)
![ntfy](https://img.shields.io/badge/Android-ntfy-2581C4)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

**当前暂停运行 · 以后按需启用 iOS Bark / Android ntfy · 完整源码及注释均保留**

[🔌 恢复运行](./docs/SETUP.md) · [🧩 注释版工作流](./templates/radar.yml) · [🤖 安卓 ntfy](./docs/ANDROID.md) · [📖 部署教程](./docs/SETUP.md) · [❓ 常见问题](./docs/FAQ.md)

</div>

---

## ⏸️ 当前状态：默认停用

> **当前仓库不会运行任何 GitHub Actions，也不会自动扫描或推送消息。**
>
> 为避免不必要的自动运行与 Bark 通知，原本的 `.github/workflows/radar.yml` 已移走，全部保留为 [`templates/radar.yml`](./templates/radar.yml) **注释版模板**。GitHub 只会从 `.github/workflows/` 读取工作流，所以模板不会执行。
>
> **想启用？** 将 `templates/radar.yml` 复制为 `.github/workflows/radar.yml`，再把文件顶部 `# on:` 开始的触发器配置块前的 `# ` 注释删除，设置对应的 GitHub Secrets，提交后才会启用。**只删除注释而不复制到工作流目录，也不会运行。**
>
> 启用前不需要输入 Bark Key、也不用担心收到游戏通知。完整操作见 [恢复运行教程](./docs/SETUP.md)。

## ✨ 这是什么？

不想每周手动打开 Epic 和 Steam 翻免费游戏？**FreeGame Radar** 帮你定时检查公开活动信息：

> 🎁 **Epic / Steam 发现限时免费游戏！**
>
> 《示例游戏》现可免费领取，具体截止时间以活动页为准。
>
> **轻点手机通知 → 打开活动页面 → 自己确认领取。**
>
> *以上是通知效果示意，并非当前真实活动。*

启用后项目可以运行在 **GitHub Actions** 上，不用自己买服务器、提供游戏账号密码或让电脑一直开机；**当前仓库未启用该功能**。

## 📦 能做什么？

| 功能 | 支持情况 | 说明 |
| :--- | :---: | :--- |
| 🎮 Epic 限时免费 | ✅ | 根据 Epic 公开促销接口筛选“原价大于 0、当前 0 元且促销有效”的商品 |
| 🚂 Steam 赠送活动 | ✅ | 读取 GamerPower 的 Steam 活动列表；可能包含第三方领码活动 |
| 📲 iOS Bark / Android ntfy | ⏸️ | 目前均停用；代码已保留，恢复工作流时由使用者自行选择 |
| ⏰ 定时监控 | ⏸️ | 工作流模板已保留；仓库当前不运行，启用后默认每 6 小时一次 |
| 🔁 双重防重复 | ✅ | 各通道独立记录活动 ID，同游戏名 45 天内避免重复提醒 |
| 🧪 一键测试 | ⏸️ | 恢复工作流后才可运行测试推送 |
| 📋 当前活动清单 | ✅ | 扫描后自动更新 [FREE_GAMES.md](./FREE_GAMES.md) |
| 🆓 免费部署 | ✅ | 不需要额外付费服务；受 GitHub Actions 免费额度与政策约束 |
| 🛒 自动下单入库 | ❌ | **不会**登录游戏账号或代替你确认领取 |

**重要区别：** 这里的“免费”是发现活动，并不意味着每个地区、每个账号都有资格；Steam 数据源也可能包含第三方送 Key，而非 Steam 商店直接 0 元购买。请以活动原页面为准。

## 🚀 快速开始

**项目当前已暂停。** 新用户可 Fork 仓库、按下面步骤手动恢复工作流；不恢复就不会触发任何扫描和推送。

### 1. 获取项目

打开 [EpochTX/freegame](https://github.com/EpochTX/freegame)，选择 **Fork**。然后把仓库的 `templates/radar.yml` 复制为 `.github/workflows/radar.yml`，去掉模板顶部事件触发器配置块各行前面的 `# `。如果不做这两步，**GitHub Actions 不会运行**。不需要 VPS 或自建数据库。

### 2. 自行启用工作流后，再配置手机通知（任选其一）

在你的仓库打开 **Settings → Secrets and variables → Actions → New repository secret**。

| 字段 | 填写内容 |
| --- | --- |
| **Name** | `BARK_URL` |
| **Secret** | Bark App 提供的完整 HTTPS 推送 URL，如 `https://api.day.app/YOUR_DEVICE_KEY/` |

安卓：安装 [ntfy](https://docs.ntfy.sh/subscribe/phone/)，创建一个**高随机度**的订阅主题，仓库增加 Secret `NTFY_TOPIC`；启用工作流后，再将其测试、扫描任务中的两处 `# NTFY_TOPIC:` 取消注释。详见 [安卓接入指南](./docs/ANDROID.md)。**公共 ntfy.sh 主题默认不设访问控制。**

> 🔐 **不要**把真实 Bark Key、账号密码、Cookie、Token 填入源码、README、Issue 或 Actions Variables。请放在 **Secrets** 中。曾公开过的 Key 应先在 Bark 中轮换。

> 🕒 **历史消息不再短时过期：** 推送时使用 `isArchive=1` 且不设置 `ttl`。如果你从 Bark 的示例命令复制了 `/title/body?group=example&ttl=600`，请把 Secret 更正为**仅含设备密钥**的完整 HTTPS 地址（`https://api.day.app/YOUR_DEVICE_KEY/`）；脚本也会自动去除这类误带的示例参数。最终历史保留仍受 Bark App 数据和清理设置影响。

### 3. 测试是否收到通知

完成工作流恢复及 Secret 配置后，打开自己仓库的 **Actions → Free Games Radar**，选择：

1. **Run workflow** → **mode: `test`**：检查所有已配置的手机是否收到「测试成功」推送。
2. 再执行 **mode: `scan`**：真正查询 Epic / Steam，更新 [活动清单](./FREE_GAMES.md) 并推送尚未记录的新活动。

新设备首次启用推送时，可能收到当前已经存在的活动；之后按通道分别去重。同款游戏在 45 天内即使上游换了赠送 ID，也会尝试抑制重复提醒。

### 4. 只有恢复并启用定时触发器后才自动运行

**目前不会执行。** 未来使用者按教程恢复并取消注释 `schedule` 后，GitHub Actions 才会按下面的 UTC 时刻触发：

| UTC | 北京时间（UTC+8） |
| --- | --- |
| 01:17 | 09:17 |
| 07:17 | 15:17 |
| 13:17 | 21:17 |
| 19:17 | 次日 03:17 |

> GitHub 的定时执行**不是实时任务**，高峰时可能延迟、偶发跳过；监控依赖上游第三方接口。

更完整的图文路径及排错步骤见 **[部署教程](./docs/SETUP.md)**。

## 🧩 工作原理

```mermaid
flowchart LR
    A["GitHub Actions<br/>每 6 小时"] --> B["Epic 促销接口"]
    A --> C["GamerPower<br/>Steam 赠送"]
    B --> D["筛选有效活动"]
    C --> D
    D --> E{"当前设备已通知 / 45天内同游戏？"}
    E -->|否| F["Bark iOS + ntfy Android（分别判断）"]
    E -->|是| G["跳过重复"]
    F --> H["按通道记录成功推送状态"]
    H --> I["更新免费游戏清单"]
    G --> I
```

- **无额外依赖：** 核心脚本仅用 Python 标准库。
- **双重防重复：** `data/sent.json` 按 Bark、ntfy 单独保存活动 ID 与规范化游戏名；同一游戏 45 天内抑制重复赠送活动，`data/current.json` 保存最新扫描结果。仓库推送状态失败时仍可能少量重复。
- **消息到达确认：** 仅在对应通道的推送接口响应成功后写入去重状态；接口成功不保证手机系统一定展示通知。
- **隐私与安全：** 不需要 Epic / Steam 账号凭证；Bark 和 ntfy Secret 由 GitHub Actions 读取。公共 ntfy 主题默认不具备真正的访问控制，请务必使用随机主题。

## ⚙️ 可选配置

在 **Settings → Secrets and variables → Actions → Variables** 添加以下普通变量：

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `EPIC_COUNTRY` | `CN` | Epic 查询地区（如 `CN`、`US`） |
| `EPIC_LOCALE` | `zh-CN` | Epic 页面语言（如 `zh-CN`、`en-US`） |
| `MAX_PUSH` | `8` | 每次最多推送的新活动数，允许 1～20 |

更改 `MAX_PUSH` 并不改变扫描频率。更改地区后，同一商品可能仍因去重状态而不再次提醒。

## 📁 项目结构

```text
templates/radar.yml           # 暂停状态的完整工作流模板（触发器已注释）
radar.py                      # Epic、Steam 检测 + Bark / ntfy 推送
tests/test_radar.py           # 无需联网的单元测试
data/sent.json                # 已通知活动 ID + 游戏指纹、双端独立去重
data/current.json             # 最新扫描结果
FREE_GAMES.md                 # 自动生成的活动页
docs/SETUP.md                 # 完整部署步骤
docs/FAQ.md                   # 常见问题与故障排查
docs/ANDROID.md               # Android ntfy 配置教程（含取消注释说明）
SECURITY.md                   # 安全须知
CONTRIBUTING.md               # 贡献指南
LICENSE                       # MIT 开源协议
```

## 🛠️ 本地调试

需要 Python 3.11+，不需要 `pip install`：

```bash
python -m unittest discover -s tests -v
```

设置好自己的环境变量 `BARK_URL` 之后可执行：

```bash
python radar.py --test-push
python radar.py
```

**注意：** 在本地运行会改写 `data/sent.json`、`data/current.json`、`FREE_GAMES.md`。

## ❓ 常见问题

**它会自动把游戏放进我的 Epic / Steam 库吗？** 不会。它只发官方/活动页面链接，让你自行确认领取。

**Steam 为什么跳到 GamerPower？** Steam 活动来自公开聚合接口，可能包含第三方领码任务，项目不能保证 Steam 官方商店直接免费入库。

**为什么 Actions 页面没有自动执行？** 仓库默认停用，工作流被移到 `templates/`。需要先按 [恢复教程](./docs/SETUP.md) 将文件复制进 `.github/workflows/` 并解除触发器注释；启用后无新游戏也不会发通知。

**能改成每天只推送一次吗？** 可以编辑 [工作流模板](./templates/radar.yml) 中的 cron，启用时再取消对应注释。请注意 UTC 时间与 GitHub 调度延迟。

更多见 [FAQ](./docs/FAQ.md)。

## 🔒 安全与免责声明

- 本项目不需要游戏账号登录信息。**不要**把游戏账号密码、浏览器 Cookie、第三方登录 Token 交给来历不明的领取脚本。
- 所有项目内容仅作为活动信息提示，实际价格、有效期、领取方式、地区限制以原站为准；并非 Epic、Valve 或 Bark 官方产品。
- 数据源可能故障、调整、延迟，无法承诺 100% 命中所有限免活动。
- 发现安全问题请参见 [SECURITY.md](./SECURITY.md)。

## ❤️ 开源与致谢

数据来源：[Epic Games Store](https://store.epicgames.com/) · [GamerPower API](https://www.gamerpower.com/api-read)。消息推送：[Bark](https://github.com/Finb/Bark)。云端自动化：[GitHub Actions](https://docs.github.com/en/actions)。

欢迎提 [Issue](https://github.com/EpochTX/freegame/issues) 或 [Pull Request](https://github.com/EpochTX/freegame/pulls)；提交前请先阅读 [贡献指南](./CONTRIBUTING.md)。

**License：** [MIT](./LICENSE)。