#!/usr/bin/env python3
"""FreeGame Radar: Epic + Steam -> Bark. Python 3.11+, stdlib only."""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
SENT_FILE = ROOT / "data" / "sent.json"
CURRENT_FILE = ROOT / "data" / "current.json"
OUTPUT_FILE = ROOT / "FREE_GAMES.md"
GAMERPOWER = "https://www.gamerpower.com/api/giveaways"
EPIC_API = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"
USER_AGENT = "EpochTX-FreeGame-Radar/1.0 (+https://github.com/EpochTX/freegame)"
UTC = timezone.utc


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_date(raw: str | None) -> datetime | None:
    if not raw or raw in {"N/A", "Unknown"}:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
    except (ValueError, TypeError):
        return None


def fetch_json(url: str):
    """Return JSON with two attempts; HTTP 201 means GamerPower has no offers."""
    error = None
    for attempt in range(2):
        try:
            request = Request(url, headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            })
            with urlopen(request, timeout=20) as response:
                body = response.read()
                if response.status == 201 or not body.strip():
                    return []
                return json.loads(body)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            error = exc
            if attempt == 0:
                time.sleep(2)
    raise RuntimeError(f"数据源请求失败：{type(error).__name__}") from error


def epic_link(item: dict, locale: str) -> str:
    slugs = [m.get("pageSlug") for m in item.get("offerMappings", []) if isinstance(m, dict)]
    slugs += [item.get("productSlug"), item.get("urlSlug")]
    for slug in slugs:
        if slug and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{1,120}", slug):
            return f"https://store.epicgames.com/{locale}/p/{slug}"
    return "https://store.epicgames.com/" + locale + "/browse?" + urlencode(
        {"q": item.get("title", ""), "sortBy": "relevancy"}
    )


def parse_epic(data: dict, now: datetime, locale: str) -> list[dict]:
    elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
    found = []
    for item in elements:
        if not isinstance(item, dict):
            continue
        price = (item.get("price") or {}).get("totalPrice") or {}
        if not (isinstance(price.get("originalPrice"), (int, float))
                and price["originalPrice"] > 0
                and price.get("discountPrice") == 0):
            continue  # Ignore permanently free games and paid games.
        groups = ((item.get("promotions") or {}).get("promotionalOffers") or [])
        for group in groups:
            for promo in (group.get("promotionalOffers") or []):
                start, end = parse_date(promo.get("startDate")), parse_date(promo.get("endDate"))
                if not (start and end and start <= now < end):
                    continue
                identifier = str(item.get("id") or item.get("productSlug") or item.get("title"))
                found.append({
                    "id": f"epic:{identifier}:{start.date().isoformat()}",
                    "platform": "Epic",
                    "title": str(item.get("title") or "未知游戏"),
                    "url": epic_link(item, locale),
                    "end": end.isoformat(),
                    "note": "Epic 官方限时免费；领取时请核对账号所在地区。",
                })
                break
    return found


def parse_gamerpower(data, platform: str) -> list[dict]:
    if not isinstance(data, list):
        raise ValueError("GamerPower 响应格式异常")
    found = []
    for item in data:
        if not isinstance(item, dict) or str(item.get("type", "")).lower() != "game":
            continue
        listed_platforms = str(item.get("platforms", "")).lower()
        if ("steam" if platform == "Steam" else "epic games store") not in listed_platforms:
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        # Ignore rentals, free weekends, demos and common DLC/loot false positives.
        reject = r"\b(free weekend|weekend trial|playtest|free trial|demo|beta test|dlc|loot|in.game|cosmetic|skins?)\b"
        description = str(item.get("description") or "").lower()
        if re.search(reject, title.lower()) or re.search(r"free weekend|limited.time free to play|free trial", description):
            continue
        link = item.get("open_giveaway_url") or item.get("gamerpower_url") or ""
        parsed = urlparse(str(link))
        if parsed.scheme != "https" or not (
            parsed.hostname == "gamerpower.com" or
            (parsed.hostname or "").endswith(".gamerpower.com")
        ):
            continue
        identifier = str(item.get("id") or "")
        if not identifier:
            continue
        found.append({
            "id": f"{platform.lower()}:gamerpower:{identifier}",
            "platform": platform,
            "title": title,
            "url": str(link),
            "end": str(item.get("end_date") or ""),
            "note": "GamerPower 第三方活动；可能需领码、额外账号或满足地区条件。",
        })
    return found


def get_gamerpower(platform: str):
    slug = "steam" if platform == "Steam" else "epic-games-store"
    url = GAMERPOWER + "?" + urlencode({"platform": slug, "type": "game", "sort-by": "date"})
    return parse_gamerpower(fetch_json(url), platform)


def collect_games(now: datetime) -> tuple[list[dict], list[str]]:
    country = os.environ.get("EPIC_COUNTRY", "CN").strip().upper() or "CN"
    locale = os.environ.get("EPIC_LOCALE", "zh-CN").strip() or "zh-CN"
    if not re.fullmatch(r"[A-Z]{2}", country) or not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", locale):
        raise ValueError("EPIC_COUNTRY / EPIC_LOCALE 配置不正确")
    errors = []
    successes = 0
    games = []
    try:
        epic_url = EPIC_API + "?" + urlencode(
            {"locale": locale, "country": country, "allowCountries": country}
        )
        games.extend(parse_epic(fetch_json(epic_url), now, locale))
        successes += 1
    except (RuntimeError, ValueError, TypeError, AttributeError, KeyError) as exc:
        errors.append(f"Epic 官方接口失败：{type(exc).__name__}")
        try:
            games.extend(get_gamerpower("Epic"))
            successes += 1
            errors.append("Epic 已使用 GamerPower 备用数据源，可能与官方活动略有差异。")
        except (RuntimeError, ValueError, TypeError) as fallback_exc:
            errors.append(f"Epic 备用接口失败：{type(fallback_exc).__name__}")
    try:
        games.extend(get_gamerpower("Steam"))
        successes += 1
    except (RuntimeError, ValueError, TypeError) as exc:
        errors.append(f"Steam 数据源失败：{type(exc).__name__}")
    if not successes:
        raise RuntimeError("所有来源均不可用，取消更新以免覆盖有效状态")
    unique = {g["id"]: g for g in games}
    return sorted(unique.values(), key=lambda g: (g["platform"], g["title"].casefold())), errors


def read_sent() -> dict[str, str]:
    if not SENT_FILE.exists():
        return {}
    obj = json.loads(SENT_FILE.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("data/sent.json 需要是 JSON 对象")
    return obj


def save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def bark_notify(url: str, title: str, message: str, jump_url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc or not parsed.path.strip("/"):
        raise ValueError("BARK_URL 必须是 Bark App 给出的完整 HTTPS 推送 URL")
    payload = json.dumps({
        "title": title,
        "body": message,
        "group": "免费游戏雷达",
        "url": jump_url,
        "level": "active",
    }, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=payload, method="POST",
                      headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read()
            if response.status < 200 or response.status >= 300:
                raise RuntimeError("Bark 返回非成功状态")
            result = json.loads(raw) if raw else {}
            if isinstance(result, dict) and result.get("code", 200) not in (200,):
                raise RuntimeError("Bark 返回业务错误")
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        # Do not print the URL: its path contains the secret Bark push key.
        raise RuntimeError(f"Bark 推送失败（{type(exc).__name__}），请检查 Secret / 网络") from None


def markdown_games(games: list[dict], errors: list[str]) -> str:
    lines = [
        "# 🎁 当前免费游戏",
        "",
        "> 自动查询 Epic 官方促销和 GamerPower 赠送活动。仅供提醒，以最终领取页面为准。",
        "",
    ]
    for platform in ("Epic", "Steam"):
        lines += [f"## {platform}", ""]
        group = [g for g in games if g["platform"] == platform]
        if not group:
            lines += ["当前未发现符合筛选条件的活动（也可能是来源暂时不可用）。", ""]
            continue
        for game in group:
            safe_title = game["title"].replace("[", "［").replace("]", "］").replace("\n", " ")
            lines += [f"- **[{safe_title}]({game['url']})** — {game['note']}", ""]
    if errors:
        lines += ["## 数据源提示", ""]
        lines += [f"- {warning}" for warning in errors]
        lines += [""]
    lines += [
        "---", "",
        "来源：[Epic Games Store](https://store.epicgames.com/) · "
        "[GamerPower](https://www.gamerpower.com/api-read) · "
        "[返回项目说明](./README.md)", "",
    ]
    return "\n".join(lines)


def scan() -> None:
    bark_url = os.environ.get("BARK_URL", "").strip()
    if not bark_url:
        raise RuntimeError("尚未设置 Actions Secret：BARK_URL；取消扫描，避免丢失未推送状态")
    now = utc_now()
    games, warnings = collect_games(now)
    for warning in warnings:
        print("提示：", warning)
    sent = read_sent()
    cutoff = now - timedelta(days=120)
    sent = {key: value for key, value in sent.items()
            if (parse_date(value) or now) >= cutoff}
    limit = max(1, min(20, int(os.environ.get("MAX_PUSH", "8"))))
    count = 0
    for game in games:
        if game["id"] in sent or count >= limit:
            continue
        title = "🎁 " + game["platform"] + " 限时免费：" + game["title"][:75]
        body = game["note"]
        if game.get("end"):
            body += "\n结束时间（数据源原样）： " + str(game["end"])
        bark_notify(bark_url, title, body, game["url"])
        sent[game["id"]] = now.isoformat()
        count += 1
        print("已发送：", game["platform"], game["title"])
    save_json(SENT_FILE, sent)
    save_json(CURRENT_FILE, games)
    OUTPUT_FILE.write_text(markdown_games(games, warnings), encoding="utf-8")
    print(f"本次检索到 {len(games)} 个活动，推送 {count} 个，剩余待推送 "
          f"{sum(g['id'] not in sent for g in games)} 个")


def main() -> None:
    parser = argparse.ArgumentParser(description="Epic / Steam FreeGame Radar")
    parser.add_argument("--test-push", action="store_true", help="仅测试 Bark")
    args = parser.parse_args()
    if args.test_push:
        url = os.environ.get("BARK_URL", "").strip()
        if not url:
            raise RuntimeError("缺少 BARK_URL Secret")
        bark_notify(url, "✅ FreeGame Radar 测试成功",
                    "GitHub Actions 已连接 Bark！下一步可以手动运行 scan 模式。",
                    "https://github.com/EpochTX/freegame")
        print("测试通知已发送")
    else:
        scan()


if __name__ == "__main__":
    main()
