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
EXPIRED_FILE = ROOT / "data" / "expired.json"
ARCHIVE_DAYS = 60
ARCHIVE_LIMIT = 80
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
    # Unexpected response shapes must not be treated as an empty promotion list.
    elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements")
    if not isinstance(elements, list):
        raise ValueError("Epic 促销接口缺少活动列表")
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


def collect_games(now: datetime) -> tuple[list[dict], list[str], set[str]]:
    country = os.environ.get("EPIC_COUNTRY", "CN").strip().upper() or "CN"
    locale = os.environ.get("EPIC_LOCALE", "zh-CN").strip() or "zh-CN"
    if not re.fullmatch(r"[A-Z]{2}", country) or not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", locale):
        raise ValueError("EPIC_COUNTRY / EPIC_LOCALE 配置不正确")
    errors = []
    successes = 0
    verified = set()
    games = []
    try:
        epic_url = EPIC_API + "?" + urlencode(
            {"locale": locale, "country": country, "allowCountries": country}
        )
        games.extend(parse_epic(fetch_json(epic_url), now, locale))
        successes += 1
        verified.add("Epic")
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
        verified.add("Steam")
    except (RuntimeError, ValueError, TypeError) as exc:
        errors.append(f"Steam 数据源失败：{type(exc).__name__}")
    if not successes:
        raise RuntimeError("所有来源均不可用，取消更新以免覆盖有效状态")
    unique = {g["id"]: g for g in games}
    return sorted(unique.values(), key=lambda g: (g["platform"], g["title"].casefold())), errors, verified


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


def reliable_deadline(game: dict) -> datetime | None:
    """Epic or timezone-aware deadlines only; GamerPower naive times stay unknown."""
    raw = str(game.get("end") or "").strip()
    if game.get("platform") == "Epic":
        return parse_date(raw)
    if re.search(r"(?:Z|[+-]\d{2}:?\d{2})$", raw, re.I):
        return parse_date(raw)
    return None


def load_games(path: Path) -> list[dict]:
    """Read our own tracked state; never silently lose history on malformed JSON."""
    if not path.exists():
        return []
    contents = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(contents, list) or any(
        not isinstance(x, dict) or not isinstance(x.get("id"), str)
        for x in contents
    ):
        raise ValueError(f"{path.name} 活动记录格式不正确")
    return contents


def reconcile_games(fresh: list[dict], now: datetime,
                    verified: set[str]) -> tuple[list[dict], list[dict]]:
    """Move vanished/ended giveaways into a bounded archive, keeping uncertain ones separate.

    A successful primary platform scan confirms absence. Epic's GamerPower
    fallback is incomplete, so it must not mark missing Epic games as ended.
    """
    previous = {game["id"]: game for game in load_games(CURRENT_FILE)}
    archived = {game["id"]: game for game in load_games(EXPIRED_FILE)}
    fresh_ids = {game["id"] for game in fresh}
    current = []

    def finish(game: dict, reason: str, at: datetime) -> None:
        copy = dict(game)
        copy.pop("status", None)
        copy["invalid_reason"] = reason
        copy["invalid_at"] = at.isoformat()
        archived[copy["id"]] = copy

    for game in fresh:
        item = dict(game)
        old = previous.get(item["id"]) or archived.get(item["id"], {})
        # Some fallback sources may omit official promotion details.
        for attr in ("start", "added_at"):
            if not item.get(attr) and old.get(attr):
                item[attr] = old[attr]
        deadline = reliable_deadline(item)
        if deadline and now >= deadline:
            finish(item, "已到截止时间", deadline)
        else:
            item["status"] = "active"
            current.append(item)

    for identifier, old in previous.items():
        if identifier in fresh_ids:
            continue
        deadline = reliable_deadline(old)
        if deadline and now >= deadline:
            finish(old, "已到截止时间", deadline)
        elif old.get("platform") in verified:
            finish(old, "来源不再列出", now)
        else:
            waiting = dict(old)
            waiting["status"] = "unverified"
            current.append(waiting)

    for item in current:
        archived.pop(item["id"], None)
    cutoff = now - timedelta(days=ARCHIVE_DAYS)
    expired = [
        item for item in archived.values()
        if (stamp := parse_date(item.get("invalid_at"))) and cutoff <= stamp <= now
    ]
    expired.sort(key=lambda x: (x["invalid_at"], x["title"].casefold()), reverse=True)
    expired = expired[:ARCHIVE_LIMIT]
    current.sort(key=lambda x: (x["status"] != "active", x["platform"], x["title"].casefold()))
    return current, expired


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


def markdown_games(games: list[dict], errors: list[str],
                   expired: list[dict] | None = None) -> str:
    expired = expired or []
    active = [g for g in games if g.get("status", "active") == "active"]
    pending = [g for g in games if g.get("status") == "unverified"]
    lines = [
        "# 🎁 免费游戏雷达｜领取状态",
        "",
        "> 自动查询 Epic 官方限免和 GamerPower 赠送活动。所有时间和领取资格以活动页面为准。",
        "",
        "> 🕒 **加入时间**指本雷达首次收录时间；Epic 已知起止时间显示为北京时间。"
        " Steam 未提供时区的截止时间保留来源原文，不擅自换算。",
        "",
        f"**当前：{len(active)} 款可领取 · {len(expired)} 款已失效 · {len(pending)} 款待核实**",
        "",
        "## ✅ 正在免费领取（" + str(len(active)) + "）",
        "",
    ]

    def add_game(game: dict, kind: str) -> None:
        title = str(game["title"]).replace("[", "［").replace("]", "］").replace("\n", " ")
        lines.append(f"- **[{title}]({game['url']})**")
        lines.append(f"  - 📥 **加入时间**：{format_beijing(game.get('added_at'), '尚未记录')}")
        if game["platform"] == "Epic":
            lines.append(f"  - 🕓 **活动开始**：{format_beijing(game.get('start'), '来源未提供')}")
        lines.append(f"  - ⏳ **截止时间**：{format_deadline(game)}")
        if kind == "expired":
            lines.append(f"  - ⛔ **状态**：{game.get('invalid_reason', '已失效')}")
            lines.append("  - 📅 **记录时间**：" + format_beijing(game.get("invalid_at")))
        elif kind == "pending":
            lines.append("  - ⚠️ **状态**：数据源暂不可核实，不能保证仍可领取")
        lines.extend([f"  - ℹ️ {game.get('note', '活动以来源页面为准。')}", ""])

    def add_group(items: list[dict], kind: str) -> None:
        if not items:
            lines.extend(["暂无符合条件的活动。", ""])
            return
        for platform in ("Epic", "Steam"):
            group = [g for g in items if g.get("platform") == platform]
            if not group:
                continue
            lines.extend([f"### {platform}（{len(group)}）", ""])
            for game in group:
                add_game(game, kind)

    add_group(active, "active")
    lines += [
        "## ⛔ 已结束 / 已失效（" + str(len(expired)) + "）",
        "",
        "> 保留最近 60 天内最多 80 条失效记录。"
        "“来源不再列出”表示本雷达已无法确认该优惠，并非官方宣布结束。",
        "",
    ]
    add_group(expired, "expired")
    if pending:
        lines += ["## ⚠️ 状态待核实（" + str(len(pending)) + "）", "",
                  "> 数据源暂时不可用；为了避免误报，这些活动暂不归入可领取或失效列表。", ""]
        add_group(pending, "pending")
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
    fresh, warnings, verified = collect_games(now)
    seen = record_first_seen(fresh, now)
    games, expired = reconcile_games(fresh, now, verified)
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
    fresh_ids = {g["id"] for g in fresh}
    for game in games:
        if game.get("status") != "active" or game["id"] not in fresh_ids:
            continue
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
    save_json(EXPIRED_FILE, expired)
    OUTPUT_FILE.write_text(markdown_games(games, warnings, expired), encoding="utf-8")
    summary = ", ".join(f"{channel}={count}" for channel, count in counts.items()) or "通知关闭（0 条）"
    print(f"检索到 {len(fresh)} 个活动；已失效存档 {len(expired)} 个；{summary}；已更新公开活动清单。")
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
