# ❓ 常见问题（FAQ）

## ⏸️ 0. 为什么这个仓库没有运行 GitHub Actions，也不会推送 Bark？

**仓库作者已暂停整个项目。** 当前没有任何活动工作流，原来的文件已放在 [`templates/radar.yml`](../templates/radar.yml)，并把 `on` 触发器事件块用 `#` 注释掉。**Bark 和安卓 ntfy 都不会自动推送**。

想要自己使用：先 Fork，复制模板到 `.github/workflows/radar.yml`，取消模板顶部 `on` 事件块的注释，按照 [恢复教程](./SETUP.md) 在自己的仓库设置对应 Secrets，才能启用。仅填写 `BARK_URL` 或 `NTFY_TOPIC` 不会让当前仓库运行。

## 0. Bark 历史消息为什么显示「几分钟后过期」，且标题是 title / body？

如果 Secret 填的是 Bark 示例 URL `https://api.day.app/YOUR_DEVICE_KEY/title/body?group=example&ttl=600`，其中 `title/body` 是示例标题正文，`ttl=600` 会让已存档通知在 10 分钟后自动过期。现在项目会自动清除 URL 中的示例路径和查询参数，用 JSON POST 发送真实游戏名称；明确设置 `isArchive=1` 且**不指定 `ttl`**。建议你也把 GitHub Secret `BARK_URL` 修改为不含额外参数的基础地址。注意已过期的历史通知无法自动找回。

## 1. 这是自动领取 Epic / Steam 游戏的工具吗？

**不是。** 项目只做「监控活动 → Bark 推送 → 点击打开活动页面」，不会执行登录、支付、下单或自动添加游戏到账号库。不要为了获得自动领取功能把账号密码交给陌生项目。

## 2. Steam 免费游戏为什么有时跳转 GamerPower？

当前 Steam 端的列表来自公开 [GamerPower API](https://www.gamerpower.com/api-read)。可能是 Steam 商店活动，也可能是需要注册第三方网站领取 Key 的促销，无法保证全部是 Steam 商店 0 元直接入库。请确认活动页面的领取条件、地区限制和结束时间。

## 3. 周末试玩会被推送吗？

脚本会按活动类型和关键词尽力过滤「Free Weekend」「Free Trial」「Demo」「DLC」「Loot」等，但第三方信息可能标注不规范，偶尔会出现误报。欢迎携带**公开活动链接**反馈；不要附账号 Cookie 或私人资料。

## 4. 为什么 Epic 的游戏在我账户里不是免费的？

Epic 的促销可能有地区限制、时段差异或页面缓存。脚本默认 `EPIC_COUNTRY=CN`，但无法代替账户登录后最终的价格验证。请以你的 Epic 账户结账页面为准。

## 4.5 Android 怎么接收免费游戏提醒？

**先按 [启用教程](./SETUP.md) 恢复自己仓库中的工作流**。然后安装 [ntfy](https://docs.ntfy.sh/subscribe/phone/)，在 App 里订阅你生成的随机主题，在 GitHub Actions Secrets 中设置 `NTFY_TOPIC`，取消两处环境变量注释，再运行 `test`。已有 iOS Bark 不受影响。完整步骤见 [安卓 ntfy 教程](./ANDROID.md)。公共主题默认不设访问控制，切勿用于私密账号信息。

## 5. 没有 Bark 消息，是不是坏了？

未必。只有出现**对该设备通道而言尚未通知过的活动**时才发消息。先运行 Actions → `Free Games Radar` → `Run workflow` → `test`，确认手机能接收；再运行 `scan` 检查日志和 [FREE_GAMES.md](../FREE_GAMES.md)。

## 6. GitHub Actions 显示成功，但为什么 Bark 没弹窗？

检查 Bark App 自身是否能收到测试消息、通知权限、专注模式、系统通知摘要；若有更换设备或重置 Bark，需更新 `BARK_URL`。Actions 绿色并不保证 iOS 端一定展示通知。

## 7. 第一次运行收到多条通知？

这是预期行为：脚本首次看到当前有效的活动时尚无去重记录，会按默认 `MAX_PUSH=8` 上限依次通知；未推送的活动可能在下次扫描补发。之后相同活动不再重复推送。

## 8. 同一游戏为什么不再提示？

`data/sent.json` 会分别记录 Bark、ntfy 成功推送的活动 ID，还增加了规范化的游戏名指纹。例如「Pony Island (Steam) Giveaway」和「Pony Island (Steam) Key Giveaway」在 45 天内会被视为同一游戏，从而避免重复提醒。该冷却期也可能过滤 45 天内真正重新开放的同款游戏活动。如果清空状态文件，当前活动会再次触发推送。

## 8.5 为什么以前会重复提醒？

曾发生「推送成功但 GitHub 在回写状态文件时遭遇并发更新失败」的情况，导致下一轮重复推送。现已增加 Git 提交重试、按通知渠道单独保存状态、游戏名 45 天冷却去重。仍有极端情况（例如进程在推送成功与 Git 提交之间突然退出）无法保证 100% 不重复。

## 9. 怎样改变监控频率？

编辑 [`.github/workflows/radar.yml`](../.github/workflows/radar.yml) 中的 `schedule.cron`。GitHub 定时任务基于 UTC，可能延迟。过于频繁轮询可能触发数据源限流，也会浪费 Actions 额度。

## 10. 监控会使用我的 Epic / Steam 账号吗？

**不会。** 脚本不需要游戏账号密码、验证码、Cookie、Token。私密配置是 Bark 推送 URL 或 ntfy 随机主题，需要保存在 GitHub Secrets 中；游戏活动信息来自公开接口。

## 11. 为什么不能把 Bark 地址直接写进仓库？

它含有设备推送 Key。泄露者可能向你的手机发送垃圾推送或骚扰消息，因此要使用 GitHub Actions Secrets 保存。**如果 Key 已暴露，请更换**；不要仅仅删除明文提交，因为 Git 历史可能保留旧版本。

## 12. Actions 提示工作流没有权限回写文件怎么办？

工作流已经声明 `permissions: contents: write`，但仓库级别策略或分支保护仍可能阻止自动提交。查看失败步骤 `Commit updated state and game list` 的日志，并检查仓库的 Actions 权限与 `main` 分支保护规则。你也可以只执行测试模式，先确认 Bark 工作正常。

## 13. 明明有免费游戏，但列表为什么为空？

脚本为减少误报只识别符合条件的当前促销，且依赖 Epic/GamerPower 数据覆盖率；有些限免是零售价长期为 0、礼包/试玩/道具或尚未被上游收录，可能不会列出。Epic 公开接口还可能有暂时不可用的情况。

## 14. 运行时显示数据源错误怎么办？

先在 Actions 里重试一次；Epic 与 Steam 数据源都依赖外部服务。脚本不会在所有来源失败时用空列表覆盖状态文件。若问题长期存在，请提交 Issue，附上**脱敏后的报错摘要、发生时间、预期平台**。

## 15. 可以用 Android / 自建 Bark 服务器吗？

可以修改 `BARK_URL` 指向你可信任、兼容 Bark 推送接口的 HTTPS 端点。但官方 Bark 的 iOS 推送体验是默认目标；其他端点的返回行为和通知机制请自行核实。

[← 返回项目首页](../README.md) · [详细部署教程](./SETUP.md) · [安全须知](../SECURITY.md)
