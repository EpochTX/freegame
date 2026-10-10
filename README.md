# 🎮 FreeGame Radar — Epic / Steam 免费游戏雷达

用 **GitHub Actions + Bark** 自动发现限时免费游戏。无需 VPS、游戏账号密码，也不执行自动领取。

## 功能

- 每 6 小时自动查询 **Epic 当前限时免费入库**（Epic 公开促销接口）和 **Steam 免费游戏赠送**（GamerPower 公共 API）。
- 只关注完整游戏；过滤大部分周末试玩 / DLC / 道具活动。Steam 第三方赠送仍需人工核对条件。
- 发现未通知过的新活动，给 iPhone 的 **Bark** 推送；点通知进入活动页面。
- 用 `data/sent.json` 持久去重；`FREE_GAMES.md` 展示当前活动；支持手动执行和推送测试。
- Python 标准库实现，无额外 pip 依赖。GitHub Actions 的额度与规则以 GitHub 官方为准。

## ✅ 只需一次配置

1. 安装并打开 iPhone **Bark**，复制 App 里的完整推送 URL，形如 `https://api.day.app/你的设备密钥/`。
2. 在本仓库进入 **Settings → Secrets and variables → Actions → New repository secret**：
   - Name: `BARK_URL`
   - Secret: 刚复制的完整 Bark URL。
   - **请不要把 URL、Key 放入 README、Issue 或源码**。仓库目前公开可见。
3. 进入 **Actions → Free Games Radar → Run workflow**，先选 `test` 模式，确认 iPhone 收到测试通知。
4. 再运行 `scan` 模式，检查扫描日志和 [FREE_GAMES.md](./FREE_GAMES.md)；此后每 6 小时自动运行。

GitHub Actions 的 `schedule` 使用 UTC 时间；本项目为 UTC 01:17、07:17、13:17、19:17（北京时间 09:17、15:17、21:17、次日 03:17）；GitHub 高峰期可能延迟。

## 配置参数（可选）

在仓库 **Settings → Secrets and variables → Actions → Variables** 创建：

| 变量 | 默认值 | 含义 |
| --- | --- | --- |
| `EPIC_COUNTRY` | `CN` | Epic 查询地区，如 CN / US；与 Epic 账号实际地区一致 |
| `EPIC_LOCALE` | `zh-CN` | Epic 页面语言，如 zh-CN / en-US |
| `MAX_PUSH` | `8` | 一次扫描最多推送多少条新活动 |

`test` 模式只发一条测试通知，不写去重状态；`scan` 模式会扫描并推送。首次扫描会推送当前已经存在、尚未记录的有效活动。

## 平台与限制

- **Epic**：依据 API 的原价、现价与促销日期判断限时免费；不监控永久免费的普通游戏。公开接口可能不可用或地区数据不一致。
- **Steam**：由 [GamerPower](https://www.gamerpower.com/api-read) 提供公开限免/送 Key 汇总；部分活动可能要求第三方账号或特定地区，不保证 Steam 商店直接入库。**周末免费试玩不属于永久领取**，项目尽力过滤。
- Bark 通知链接是到商店/活动页面，**不是一键自动确认订单**。领取和地区限制均以官方商店实际显示为准。
- Bark 推送失败时，未送达的条目不写入去重文件，下一次扫描会重试。手动删除 `data/sent.json` 将导致重新通知现有活动。
- 查询依赖第三方接口与 GitHub Actions 调度，无法保证秒级发现或 100% 覆盖全部地区与商店。
- 运行前请确认 GitHub Actions 已启用，仓库允许 `GITHUB_TOKEN` 对 contents 写入，以保存状态。

## 代码结构

```text
.github/workflows/radar.yml    # 定时与手动运行、保存状态
radar.py                       # 数据获取、筛选、去重、Bark 推送
tests/test_radar.py            # 离线单元测试
data/sent.json                 # 已推送活动记录（运行后自动生成）
data/current.json              # 最新活动（运行后自动生成）
FREE_GAMES.md                  # 最新活动列表（运行后自动生成）
```

## 本地测试

```bash
python -m unittest discover -s tests -v
# 设置自己的 BARK_URL 后，运行：
python radar.py --test-push
python radar.py
```

**致谢/数据源**：[Epic Games Store](https://store.epicgames.com/) · [GamerPower API](https://www.gamerpower.com/api-read) · [Bark](https://github.com/Finb/Bark)。GamerPower 请求数据用于个人免费通知，保留来源链接与署名。
