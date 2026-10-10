#!/usr/bin/env python3
"""FreeGame Radar: Epic + Steam -> Bark (iOS) and ntfy (Android)."""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse, urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
SENT_FILE = ROOT / "data" / "sent.json"
CURRENT_FILE = ROOT / "data" / "current.json"
OUTPUT_FILE = ROOT / "FREE_GAMES.md"
FIRST_SEEN_FILE = ROOT / "data" / "first_seen.json"
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
                    "start": start.isoformat(),
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


def record_first_seen(games: list[dict], now: datetime) -> dict[str, str]:
    """Persist when this radar first recorded each giveaway, across scan gaps.

    Pre-existing games receive their first tracked timestamp on upgrade; this
    cannot reconstruct the actual first appearance before tracking was added.
    """
    if FIRST_SEEN_FILE.exists():
        seen = json.loads(FIRST_SEEN_FILE.read_text(encoding="utf-8"))
        if not isinstance(seen, dict):
            raise ValueError("data/first_seen.json 需要是 JSON 对象")
    else:
        seen = {}
    cutoff = now - timedelta(days=180)
    recent = {}
    for identifier, raw in seen.items():
        stamp = parse_date(raw) if isinstance(raw, str) else None
        if stamp and cutoff <= stamp <= now:
            recent[str(identifier)] = stamp.isoformat()
    for game in games:
        identifier = game["id"]
        first = parse_date(recent.get(identifier)) or now
        game["added_at"] = first.isoformat()
        recent[identifier] = first.isoformat()
    return recent


def format_beijing(raw: str | None, unknown: str = "尚未记录") -> str:
    stamp = parse_date(raw)
    if stamp is None:
        return unknown
    bjt = stamp.astimezone(timezone(timedelta(hours=8)))
    return bjt.strftime("%Y-%m-%d %H:%M") + "（北京时间）"


def format_deadline(game: dict) -> str:
    """Never invent a timezone for GamerPower's naive end_date strings."""
    raw = str(game.get("end") or "").strip()
    if not raw or raw in {"N/A", "Unknown"}:
        return "未公布（请以活动页面为准）"
    if game.get("platform") == "Epic":
        return format_beijing(raw, "未公布（请以活动页面为准）")
    if re.search(r"(?:Z|[+-]\d{2}:?\d{2})$", raw, re.I):
        return format_beijing(raw, "未公布（请以活动页面为准）")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?", raw):
        return raw[:16].replace("T", " ") + "（来源未注明时区）"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw + "（来源未注明时区）"
    return "时间信息不明确（请以活动页面为准）"


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


def normalize_bark_url(url: str) -> str:
    """Remove GET-example placeholders and query settings from a Bark POST URL.

    A copied example such as /KEY/title/body?group=example&ttl=600 can
    override POST content and make history disappear after 10 minutes.
    Never log the original URL: it contains the device key.
    """
    parsed = urlsplit(url.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("BARK_URL 必须是完整的 HTTPS 推送 URL")
    segments = [part for part in parsed.path.split("/") if part]
    if len(segments) >= 3 and segments[-2:] == ["title", "body"]:
        segments = segments[:-2]
    elif len(segments) >= 4 and segments[-3:] == ["title", "subtitle", "body"]:
        segments = segments[:-3]
    if not segments or segments[-1] == "push":
        raise ValueError("请将 BARK_URL 设置为 /设备密钥/，不要使用 /push 或 curl 命令")
    if parsed.hostname == "api.day.app" and len(segments) != 1:
        raise ValueError("BARK_URL 应为 https://api.day.app/设备密钥/，不要附带 title/body")
    # Remove ALL query parameters, especially ttl=600: a push should stay archived.
    # group, title, body and the target page are sent separately in the JSON POST.
    return urlunsplit((parsed.scheme, parsed.netloc, "/" + "/".join(segments), "", ""))


def bark_notify(url: str, title: str, message: str, jump_url: str) -> None:
    safe_endpoint = normalize_bark_url(url)
    payload = json.dumps({
        "title": title,
        "body": message,
        "group": "免费游戏雷达",
        "url": jump_url,
        "level": "active",
        "isArchive": "1",
        # Do not pass ttl: the user should control Bark history retention.
    }, ensure_ascii=False).encode("utf-8")
    request = Request(safe_endpoint, data=payload, method="POST",
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
        # Never log the request URL: it includes the secret Bark device key.
        raise RuntimeError(f"Bark 推送失败（{type(exc).__name__}），请检查 Secret / 网络") from None


def ntfy_notify(topic: str, title: str, message: str, jump_url: str) -> None:
    """Send Android notifications using public ntfy.sh (no new server needed)."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{20,100}", topic):
        raise ValueError("NTFY_TOPIC 应是至少 20 位的随机订阅主题，不能是 URL")
    payload = json.dumps({
        "topic": topic,
        "title": title,
        "message": message,
        "priority": 3,
        "click": jump_url,
    }, ensure_ascii=False).encode("utf-8")
    request = Request("https://ntfy.sh/", data=payload, method="POST",
                      headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urlopen(request, timeout=20) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError("ntfy 返回非成功状态")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        # Do not print the topic in logs: it acts as an access secret.
        raise RuntimeError(f"ntfy 推送失败（{type(exc).__name__}）") from None


def configured_channels(required: bool = True) -> dict[str, str]:
    """Return enabled push channels; scans may run without any secrets.

    When both BARK_URL and NTFY_TOPIC are absent the radar still scans and
    refreshes FREE_GAMES.md, but sends absolutely no notification.
    """
    channels = {}
    bark = os.environ.get("BARK_URL", "").strip()
    ntfy = os.environ.get("NTFY_TOPIC", "").strip()
    if bark:
        channels["bark"] = bark
    if ntfy:
        channels["ntfy"] = ntfy
    if required and not channels:
        raise RuntimeError("请先设置 BARK_URL（iOS）或 NTFY_TOPIC（安卓）Secret")
    return channels


def game_fingerprint(game: dict) -> str:
    """Canonical identity for overlapping giveaways of the same game.

    GamerPower may list the same game under new giveaway IDs or names such
    as '(Steam) Key Giveaway'. The fingerprint prevents repeated alerts for
    the same title within 45 days, while allowing later new promotions.
    """
    title = unicodedata.normalize("NFKC", str(game.get("title") or "")).casefold()
    title = re.sub(
        r"(?:\s*\((?:steam|epic(?: games store)?)\))?\s*(?:key\s*)?(?:giveaway|free game)\s*$",
        "", title,
    )
    title = re.sub(r"\s*\((?:steam|epic(?: games store)?)\)\s*$", "", title)
    name = re.sub(r"[^\w]+", "-", title, flags=re.UNICODE).strip("-")
    if not name:
        name = str(game.get("id", "unknown"))
    return f"game:{str(game.get('platform', '')).casefold()}:{name}"


def game_is_sent(sent: dict[str, str], channel: str, game: dict,
                 now: datetime) -> bool:
    game_id = game["id"]
    if f"{channel}:{game_id}" in sent:
        return True
    # Legacy id-only entries were delivered via Bark before ntfy was added.
    if channel == "bark" and game_id in sent:
        return True
    stamp = parse_date(sent.get(f"{channel}:{game_fingerprint(game)}"))
    return bool(stamp and now - timedelta(days=45) <= stamp <= now)


def mark_game_sent(sent: dict[str, str], channel: str,
                   game: dict, stamp: datetime) -> None:
    sent[f"{channel}:{game['id']}"] = stamp.isoformat()
    sent[f"{channel}:{game_fingerprint(game)}"] = stamp.isoformat()


def upgrade_old_game_state(sent: dict[str, str]) -> None:
    """Backfill fingerprints from last snapshot, without notifying again.

    Old Bark state had bare IDs; early dual-channel state had namespaced IDs.
    """
    if not CURRENT_FILE.exists():
        return
    try:
        previous = json.loads(CURRENT_FILE.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return
    if not isinstance(previous, list):
        return
    for game in previous:
        if not isinstance(game, dict) or not game.get("id"):
            continue
        for channel in ("bark", "ntfy"):
            old = sent.get(f"{channel}:{game['id']}")
            if channel == "bark":
                old = old or sent.get(game["id"])
            key = f"{channel}:{game_fingerprint(game)}"
            if old and key not in sent:
                sent[key] = old


def send_to_channel(channel: str, endpoint: str, title: str,
                    message: str, jump_url: str) -> None:
    if channel == "bark":
        bark_notify(endpoint, title, message, jump_url)
    elif channel == "ntfy":
        ntfy_notify(endpoint, title, message, jump_url)
    else:
        raise ValueError("未知通知渠道")


def make_push_text(game: dict) -> tuple[str, str]:
    """Human-readable notification; do not assume unknown Steam timezone."""
    platform = game["platform"]
    name = str(game["title"]).strip()
    title = f"🎁 {platform} 限免：{name[:65]}"
    lines = [
        f"游戏：{name}",
        f"平台：{platform}",
        "状态：可免费领取（请以活动页面实际显示为准）",
    ]
    end = parse_date(str(game.get("end") or ""))
    if platform == "Epic" and end:
        beijing = end.astimezone(timezone(timedelta(hours=8)))
        lines.append("截止：北京时间 " + beijing.strftime("%m月%d日 %H:%M"))
    else:
        lines.append("截止：以活动页面为准")
    lines.extend([game["note"], "👉 点击通知查看活动与领取方式"])
    return title, "\n".join(lines)


def markdown_games(games: list[dict], errors: list[str]) -> str:
    lines = [
        "# 🎁 当前免费游戏",
        "",
        "> 自动查询 Epic 官方促销和 GamerPower 赠送活动。仅供提醒，以最终领取页面为准。",
        "",
        "> 🕒 **时间说明**：加入时间是雷达首次记录该活动的时间（现有活动可依据仓库首次扫描提交时间补录，其他旧活动从启用后的首次扫描开始计时），不等于游戏活动开始时间。所有时间以领取页面为准。",
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
            lines.append(f"- **[{safe_title}]({game['url']})**")
            lines.append(f"  - 📥 **加入时间**：{format_beijing(game.get('added_at'), '待下次扫描记录')}")
            if platform == "Epic":
                lines.append(f"  - 🕓 **活动开始**：{format_beijing(game.get('start'), '待下次扫描获取')}")
            lines.append(f"  - ⏳ **截止时间**：{format_deadline(game)}")
            lines.extend([f"  - ℹ️ **说明**：{game['note']}", ""])
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
    channels = configured_channels(required=False)
    if not channels:
        print("通知已关闭：未配置任何推送 Secret；只扫描并更新免费游戏列表。")
    now = utc_now()
    games, warnings = collect_games(now)
    seen = record_first_seen(games, now)
    for warning in warnings:
        print("提示：", warning)
    sent = read_sent()
    upgrade_old_game_state(sent)
    cutoff = now - timedelta(days=120)
    sent = {key: value for key, value in sent.items()
            if (parse_date(value) or now) >= cutoff}
    limit = max(1, min(20, int(os.environ.get("MAX_PUSH", "8"))))
    counts = {channel: 0 for channel in channels}
    failures = []
    for game in games:
        title, body = make_push_text(game)
        for channel, endpoint in channels.items():
            if game_is_sent(sent, channel, game, now) or counts[channel] >= limit:
                continue
            try:
                send_to_channel(channel, endpoint, title, body, game["url"])
            except (RuntimeError, ValueError) as exc:
                failures.append(f"{channel} 通知失败：{type(exc).__name__}")
                print("警告：", channel, "未推送成功，稍后将重试")
                continue
            mark_game_sent(sent, channel, game, now)
            counts[channel] += 1
            print("已发送：", channel, game["platform"], game["title"])
    save_json(SENT_FILE, sent)
    save_json(FIRST_SEEN_FILE, seen)
    save_json(CURRENT_FILE, games)
    OUTPUT_FILE.write_text(markdown_games(games, warnings), encoding="utf-8")
    summary = ", ".join(f"{channel}={count}" for channel, count in counts.items()) or "通知关闭（0 条）"
    print(f"检索到 {len(games)} 个活动；{summary}；已更新公开活动清单。")
    if failures:
        print(f"本次有 {len(failures)} 项通知失败，下次扫描将重试。")


def main() -> None:
    parser = argparse.ArgumentParser(description="Epic / Steam FreeGame Radar")
    parser.add_argument("--test-push", action="store_true", help="仅测试 Bark")
    args = parser.parse_args()
    if args.test_push:
        channels = configured_channels(required=False)
        if not channels:
            print("未配置 BARK_URL 或 NTFY_TOPIC；通知测试已跳过（正常状态）。")
        for channel, endpoint in channels.items():
            send_to_channel(
                channel, endpoint,
                "✅ FreeGame Radar 测试成功",
                "GitHub Actions 推送已连接！可以手动运行 scan 模式。",
                "https://github.com/EpochTX/freegame",
            )
            print(channel, "测试通知已发送")
    else:
        scan()


if __name__ == "__main__":
    main()
