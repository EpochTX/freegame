# 📲 Android 推送接入：ntfy

FreeGame Radar 默认可直接扫描并更新免费游戏列表，**安卓通知为可选功能**。需要安卓推送时，可使用开源 [ntfy](https://github.com/binwiederhier/ntfy) 服务，无需单独部署服务器。

> 默认不开启 ntfy。仅设置 GitHub Secret 还不够，需要在工作流中取消两处注释。

## 1. 安装 ntfy App

- 官方文档：[ntfy Android 推送](https://docs.ntfy.sh/subscribe/phone/)
- 安装途径：Google Play 或 F-Droid。
- 开启通知权限，并确认手机网络可以访问 `ntfy.sh`。

使用 F-Droid 版本可能需要保持后台连接；Android 的电池优化或后台管理规则可能影响实时收信。

## 2. 创建随机主题

公共 `ntfy.sh` 服务上的主题默认没有账号访问控制；**知道主题名的人可能订阅或发送通知**。请使用随机且不可预测的主题，避免手机号或常见单词。

可在电脑上运行：

```bash
python -c "import secrets; print('freegame_' + secrets.token_urlsafe(24))"
```

得到一串如 `freegame_RANDOM_TOPIC_FROM_GENERATOR` 的名称。该示例是占位文字，不可直接当作密钥使用。

在 ntfy App 里点击 **Subscribe to topic**，服务器选 `ntfy.sh`，填入生成的完整主题名。

## 3. 添加 GitHub Secret

在自己仓库的 **Settings → Secrets and variables → Actions → New repository secret** 中创建：

| 参数 | 填写值 |
| --- | --- |
| Name | `NTFY_TOPIC` |
| Secret | 生成的随机主题名，不加 `https://ntfy.sh/` |

不要把真实主题写进 `.yml`、README、Issue、Pull Request 或公开日志中。

## 4. 启用两处配置注释

编辑本仓库的 [`.github/workflows/radar.yml`](../.github/workflows/radar.yml)。

在 **Test configured push channels** 和 **Scan free games and notify** 两个任务下，分别找到注释：

```yaml
# NTFY_TOPIC: ${{ secrets.NTFY_TOPIC }}
```

将两处都改为有效配置（去掉行首 `# `）：

```yaml
NTFY_TOPIC: ${{ secrets.NTFY_TOPIC }}
```

注意保持与所在 `env:` 中其他字段相同的缩进。**只改一处可能导致测试可用，但定时扫描不推送，或反过来。**

Bark 的配置不需要修改。可以只用 ntfy，也可以 Bark 和 ntfy 同时启用。

## 5. 测试

1. 打开自己仓库的 **Actions → Free Games Radar**。
2. 点击 **Run workflow**，选择 `test`。
3. 安卓应收到「FreeGame Radar 测试成功」，点击后打开项目页面。
4. 选择 `scan`，扫描免费游戏；发现新活动时，向已配置的通道推送。

相同游戏在不同设备通道独立去重，支持多台安卓通过同一主题订阅。

## 6. 停用 ntfy（保留 Actions 扫描）

重新注释工作流中的两处 `NTFY_TOPIC` 环境变量，或删除 GitHub Secret。无推送通道时，程序继续扫描并更新 [免费游戏清单](../FREE_GAMES.md)，不会发送消息。

## 7. 常见问题

**安卓没有通知：** 核对主题名、Secret、两处环境变量、ntfy App 通知权限、网络访问和系统后台限制。

**通知会永久保存吗？** 无法保证。公共 ntfy 服务有自身的消息存储策略，可以通过仓库 [活动清单](../FREE_GAMES.md) 查看扫描结果。

**免费游戏会自动入库吗？** 不会。点击 ntfy 通知只会打开活动页面，仍需按平台规则自行领取。

**会泄露个人信息吗？** 系统仅推送公开游戏名称与活动链接，不应把账号密码或私人内容发到公共 ntfy 主题。主题随机化降低被猜到的可能，不等于身份认证或端到端加密。

[← 返回 README](../README.md) · [完整部署指南](./SETUP.md) · [安全说明](../SECURITY.md)
