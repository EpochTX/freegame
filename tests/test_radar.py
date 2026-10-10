"""Unit tests require no network or login credentials."""
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import radar


NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


def epic_offer(title, identifier, original=1999, discount=0,
               start="2026-10-09T15:00:00.000Z", end="2026-10-16T15:00:00.000Z"):
    return {
        "id": identifier,
        "title": title,
        "productSlug": "good-game",
        "price": {"totalPrice": {"originalPrice": original, "discountPrice": discount}},
        "promotions": {"promotionalOffers": [
            {"promotionalOffers": [{"startDate": start, "endDate": end}]}
        ]},
    }


class RadarTests(unittest.TestCase):
    def test_epic_only_current_paid_to_free(self):
        data = {"data": {"Catalog": {"searchStore": {"elements": [
            epic_offer("Free this week", "123"),
            epic_offer("Always free", "234", original=0),
            epic_offer("Paid sale", "345", discount=99),
            epic_offer("Expired", "456", start="2026-10-01T00:00:00Z",
                       end="2026-10-02T00:00:00Z"),
            epic_offer("Upcoming", "789", start="2026-10-12T00:00:00Z",
                       end="2026-10-20T00:00:00Z"),
        ]}}}}
        games = radar.parse_epic(data, NOW, "zh-CN")
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["title"], "Free this week")
        self.assertEqual(games[0]["url"], "https://store.epicgames.com/zh-CN/p/good-game")
        self.assertTrue(games[0]["id"].startswith("epic:123:"))
        self.assertEqual(games[0]["start"], "2026-10-09T15:00:00+00:00")

    def test_epic_safe_search_link_fallback(self):
        link = radar.epic_link({"title": "Hello World", "productSlug": "games/bad-path"},
                               "zh-CN")
        self.assertIn("browse?", link)
        self.assertIn("Hello+World", link)

    def test_steam_filters_weekends_and_other_loot(self):
        data = [
            {"id": 1, "title": "Great Game (Steam) Giveaway", "type": "Game",
             "platforms": "PC, Steam",
             "open_giveaway_url": "https://www.gamerpower.com/open/great-game",
             "description": "Free copy of full game", "end_date": "2026-10-20 00:00:00"},
            {"id": 2, "title": "Free Weekend", "type": "Game",
             "platforms": "Steam", "open_giveaway_url": "https://www.gamerpower.com/open/weekend"},
            {"id": 3, "title": "Skin Giveaway", "type": "Loot",
             "platforms": "Steam", "open_giveaway_url": "https://www.gamerpower.com/open/skin"},
            {"id": 4, "title": "Another Game", "type": "Game",
             "platforms": "Epic Games Store", "open_giveaway_url": "https://www.gamerpower.com/open/other"},
            {"id": 5, "title": "Wrong Link", "type": "Game",
             "platforms": "Steam", "open_giveaway_url": "http://example.com/secret"},
        ]
        games = radar.parse_gamerpower(data, "Steam")
        self.assertEqual([g["id"] for g in games], ["steam:gamerpower:1"])
        self.assertIn("领码", games[0]["note"])

    def test_date_parser(self):
        self.assertEqual(radar.parse_date("2026-10-10T12:00:00Z"), NOW)
        self.assertIsNone(radar.parse_date("N/A"))

    def test_dedupe_across_runs(self):
        game = {"id": "epic:123:2026-10-09", "platform": "Epic",
                "title": "Test game", "url": "https://store.epicgames.com/en-US/p/test-game",
                "end": "2026-10-16T15:00:00Z", "note": "Test"}
        with tempfile.TemporaryDirectory() as temp:
            with (
                patch.object(radar, "SENT_FILE", Path(temp) / "data" / "sent.json"),
                patch.object(radar, "CURRENT_FILE", Path(temp) / "data" / "current.json"),
                patch.object(radar, "FIRST_SEEN_FILE", Path(temp) / "first_seen.json"),
                patch.object(radar, "OUTPUT_FILE", Path(temp) / "FREE_GAMES.md"),
                patch.object(radar, "collect_games", return_value=([game], [], {"Epic"})),
                patch.object(radar, "bark_notify") as bark,
                patch.dict(os.environ, {"BARK_URL": "https://api.day.app/test",
                                        "MAX_PUSH": "8"}),
            ):
                radar.scan()
                radar.scan()
                self.assertEqual(bark.call_count, 1)
                self.assertIn("bark:" + game["id"], json.loads(radar.SENT_FILE.read_text()))
                self.assertIn("bark:" + radar.game_fingerprint(game), json.loads(radar.SENT_FILE.read_text()))
                self.assertTrue(radar.OUTPUT_FILE.exists())

    def test_no_push_secret_still_updates_free_games(self):
        game = {"id": "epic:zero-channel", "platform": "Epic",
                "title": "No Push Needed",
                "url": "https://store.epicgames.com/p/no-push",
                "end": "2026-10-16T15:00:00Z", "note": "Test"}
        with tempfile.TemporaryDirectory() as temp:
            sent_path = Path(temp) / "data" / "sent.json"
            current_path = Path(temp) / "data" / "current.json"
            md_path = Path(temp) / "FREE_GAMES.md"
            with (
                patch.object(radar, "SENT_FILE", sent_path),
                patch.object(radar, "CURRENT_FILE", current_path),
                patch.object(radar, "FIRST_SEEN_FILE", Path(temp) / "first_seen.json"),
                patch.object(radar, "OUTPUT_FILE", md_path),
                patch.object(radar, "collect_games", return_value=([game], [], {"Epic"})),
                patch.object(radar, "bark_notify") as bark,
                patch.object(radar, "ntfy_notify") as ntfy,
                patch.dict(os.environ, {"BARK_URL": "", "NTFY_TOPIC": ""}),
            ):
                radar.scan()
                self.assertTrue(md_path.exists())
                self.assertIn("No Push Needed", md_path.read_text())
                saved_games = json.loads(current_path.read_text())
                self.assertEqual(saved_games[0]["id"], game["id"])
                self.assertIsNotNone(radar.parse_date(saved_games[0]["added_at"]))
                self.assertTrue((Path(temp) / "first_seen.json").exists())
                self.assertEqual(json.loads(sent_path.read_text()), {})
                bark.assert_not_called()
                ntfy.assert_not_called()

    def test_bark_json_and_url(self):
        class FakeResponse:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self):
                return b'{"code":200,"message":"success"}'
        with patch.object(radar, "urlopen", return_value=FakeResponse()) as mock_open:
            radar.bark_notify("https://api.day.app/testkey", "title", "body",
                              "https://store.epicgames.com/")
            request = mock_open.call_args.args[0]
            payload = json.loads(request.data)
            self.assertEqual(payload["group"], "免费游戏雷达")
            self.assertEqual(payload["url"], "https://store.epicgames.com/")
            self.assertEqual(payload["title"], "title")
            self.assertEqual(payload["body"], "body")
            self.assertEqual(payload["isArchive"], "1")
            self.assertNotIn("ttl", payload)
        with self.assertRaises(ValueError):
            radar.bark_notify("http://api.day.app/testkey", "title", "body",
                              "https://store.epicgames.com/")


    def test_normalize_bark_example_removes_ttl_and_placeholder(self):
        example = "https://api.day.app/testkey/title/body?group=example&ttl=600"
        self.assertEqual(radar.normalize_bark_url(example),
                         "https://api.day.app/testkey")
        self.assertEqual(radar.normalize_bark_url("https://api.day.app/testkey/"),
                         "https://api.day.app/testkey")
        with self.assertRaises(ValueError):
            radar.normalize_bark_url("https://api.day.app/push")

    def test_full_example_posts_real_game_title_and_archive(self):
        class FakeResponse:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self):
                return b'{"code":200}'
        game = {"platform": "Epic", "title": "Pony Island",
                "end": "2026-10-16T15:00:00Z",
                "note": "Epic 官方限时免费；领取时请核对账号所在地区。"}
        title, body = radar.make_push_text(game)
        self.assertIn("Pony Island", title)
        self.assertIn("北京时间 10月16日 23:00", body)
        with patch.object(radar, "urlopen", return_value=FakeResponse()) as mock_open:
            radar.bark_notify("https://api.day.app/testkey/title/body?group=example&ttl=600",
                              title, body, "https://store.epicgames.com/")
            request = mock_open.call_args.args[0]
            self.assertEqual(request.full_url, "https://api.day.app/testkey")
            self.assertEqual(json.loads(request.data)["title"], title)
            self.assertNotIn("ttl", json.loads(request.data))

    def test_steam_deadline_not_falsely_converted_to_beijing(self):
        game = {"platform": "Steam", "title": "Free Steam Game",
                "end": "2026-10-20 00:00:00", "note": "第三方免费游戏"}
        title, body = radar.make_push_text(game)
        self.assertIn("Steam", title)
        self.assertIn("以活动页面为准", body)
        self.assertNotIn("北京时间", body)


    def test_ntfy_json_push_and_click(self):
        class FakeResponse:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self):
                return b'{"id":"test"}'
        topic = "freegame_" + ("a" * 24)
        with patch.object(radar, "urlopen", return_value=FakeResponse()) as call:
            radar.ntfy_notify(topic, "游戏测试", "点击打开", "https://store.epicgames.com/")
            request = call.call_args.args[0]
            self.assertEqual(request.full_url, "https://ntfy.sh/")
            content = json.loads(request.data)
            self.assertEqual(content["topic"], topic)
            self.assertEqual(content["title"], "游戏测试")
            self.assertEqual(content["click"], "https://store.epicgames.com/")
        with self.assertRaises(ValueError):
            radar.ntfy_notify("short", "title", "body", "https://example.com")

    def test_two_channels_dedupe_and_legacy_bark_state(self):
        game = {"id": "epic:test:2026-10-10", "platform": "Epic",
                "title": "Two-channel test",
                "url": "https://store.epicgames.com/p/something",
                "end": "2026-10-20T00:00:00Z", "note": "Test"}
        with tempfile.TemporaryDirectory() as temp:
            sent_path = Path(temp) / "sent.json"
            sent_path.write_text(json.dumps({game["id"]: radar.utc_now().isoformat()}),
                                 encoding="utf-8")
            with (
                patch.object(radar, "SENT_FILE", sent_path),
                patch.object(radar, "CURRENT_FILE", Path(temp) / "current.json"),
                patch.object(radar, "FIRST_SEEN_FILE", Path(temp) / "first_seen.json"),
                patch.object(radar, "OUTPUT_FILE", Path(temp) / "FREE_GAMES.md"),
                patch.object(radar, "collect_games", return_value=([game], [], {"Epic"})),
                patch.object(radar, "bark_notify") as bark,
                patch.object(radar, "ntfy_notify") as ntfy,
                patch.dict(os.environ, {"BARK_URL": "https://api.day.app/test",
                                        "NTFY_TOPIC": "freegame_" + "z" * 25,
                                        "MAX_PUSH": "8"}),
            ):
                radar.scan()
                radar.scan()
                self.assertEqual(bark.call_count, 0)
                self.assertEqual(ntfy.call_count, 1)
                state = json.loads(sent_path.read_text())
                self.assertIn("ntfy:" + game["id"], state)

    def test_no_channel_raises(self):
        with patch.dict(os.environ, {"BARK_URL": "", "NTFY_TOPIC": ""}):
            with self.assertRaises(RuntimeError):
                radar.configured_channels()


    def test_new_giveaway_id_same_game_is_suppressed(self):
        game = {"id": "steam:gamerpower:100", "platform": "Steam",
                "title": "Pony Island (Steam) Giveaway"}
        duplicate = {"id": "steam:gamerpower:101", "platform": "Steam",
                     "title": "Pony Island (Steam) Key Giveaway"}
        self.assertEqual(radar.game_fingerprint(game), radar.game_fingerprint(duplicate))
        now = radar.utc_now()
        sent = {}
        radar.mark_game_sent(sent, "bark", game, now)
        self.assertTrue(radar.game_is_sent(sent, "bark", duplicate, now))
        self.assertFalse(radar.game_is_sent(sent, "ntfy", duplicate, now))
        self.assertFalse(radar.game_is_sent(sent, "bark", duplicate,
                                            now + radar.timedelta(days=46)))

    def test_backfill_legacy_state_for_new_id(self):
        original = {"id": "steam:gamerpower:3716", "platform": "Steam",
                    "title": "Dwarven Realms (Steam) Key Giveaway"}
        same = {"id": "steam:gamerpower:3816", "platform": "Steam",
                "title": "Dwarven Realms (Steam) Giveaway"}
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "current.json"
            state.write_text(json.dumps([original]), encoding="utf-8")
            with patch.object(radar, "CURRENT_FILE", state):
                sent = {original["id"]: radar.utc_now().isoformat()}
                radar.upgrade_old_game_state(sent)
            self.assertTrue(radar.game_is_sent(sent, "bark", same, radar.utc_now()))


    def test_first_seen_survives_scan_gap_and_does_not_reset(self):
        game = {"id": "steam:gamerpower:42", "platform": "Steam", "title": "Test"}
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(radar, "FIRST_SEEN_FILE", Path(temp) / "seen.json"):
                first = radar.record_first_seen([game.copy()], NOW)
                radar.save_json(radar.FIRST_SEEN_FILE, first)
                next_day = NOW + radar.timedelta(days=1)
                empty = radar.record_first_seen([], next_day)
                radar.save_json(radar.FIRST_SEEN_FILE, empty)
                again = [game.copy()]
                radar.record_first_seen(again, next_day + radar.timedelta(days=1))
                self.assertEqual(again[0]["added_at"], NOW.isoformat())

    def test_markdown_shows_added_start_end_and_steam_unknown_timezone(self):
        epic = {"platform": "Epic", "title": "Epic game",
                "url": "https://store.epicgames.com/p/game",
                "added_at": "2026-10-10T12:00:00Z",
                "start": "2026-10-09T15:00:00Z",
                "end": "2026-10-16T15:00:00Z", "note": "Epic promotion"}
        steam = {"platform": "Steam", "title": "Steam game",
                 "url": "https://www.gamerpower.com/open/game",
                 "added_at": "2026-10-10T12:00:00Z",
                 "end": "2026-10-12 23:59:00", "note": "Third party"}
        md = radar.markdown_games([epic, steam], [])
        self.assertIn("**加入时间**：2026-10-10 20:00（北京时间）", md)
        self.assertIn("**活动开始**：2026-10-09 23:00（北京时间）", md)
        self.assertIn("**截止时间**：2026-10-16 23:00（北京时间）", md)
        self.assertIn("**截止时间**：2026-10-12 23:59（来源未注明时区）", md)
        self.assertNotIn("2026-10-13 07:59", md)

    def test_steam_unknown_deadline_is_not_guessed(self):
        game = {"platform": "Steam", "end": "N/A"}
        self.assertIn("未公布", radar.format_deadline(game))
        self.assertEqual(
            radar.format_deadline({"platform": "Steam", "end": "2026-10-12T15:00:00Z"}),
            "2026-10-12 23:00（北京时间）"
        )


    def test_source_disappearance_moves_to_expired_and_keeps_first_seen(self):
        old = {"id": "epic:old", "platform": "Epic", "title": "Old promotion",
               "url": "https://store.epicgames.com/p/old",
               "added_at": "2026-10-09T12:00:00Z", "end": "2026-10-16T15:00:00Z",
               "note": "Promotion"}
        with tempfile.TemporaryDirectory() as temp:
            current = Path(temp) / "current.json"
            archived = Path(temp) / "expired.json"
            current.write_text(json.dumps([old]), encoding="utf-8")
            with (patch.object(radar, "CURRENT_FILE", current),
                  patch.object(radar, "EXPIRED_FILE", archived)):
                active, expired = radar.reconcile_games([], NOW, {"Epic", "Steam"})
                self.assertEqual(active, [])
                self.assertEqual(len(expired), 1)
                self.assertEqual(expired[0]["invalid_reason"], "来源不再列出")
                self.assertEqual(expired[0]["added_at"], old["added_at"])
                self.assertIn("已结束 / 已失效（1）", radar.markdown_games(active, [], expired))

    def test_failed_platform_is_unverified_not_expired(self):
        game = {"id": "epic:old", "platform": "Epic", "title": "Retained",
                "url": "https://store.epicgames.com/p/old",
                "end": "2026-10-16T15:00:00Z", "note": "Valid"}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "current.json"
            path.write_text(json.dumps([game]), encoding="utf-8")
            with (patch.object(radar, "CURRENT_FILE", path),
                  patch.object(radar, "EXPIRED_FILE", Path(temp) / "expired.json")):
                active, expired = radar.reconcile_games([], NOW, {"Steam"})
                self.assertEqual(active[0]["status"], "unverified")
                self.assertEqual(expired, [])
                md = radar.markdown_games(active, ["Epic 查询失败"], expired)
                self.assertIn("状态待核实（1）", md)
                self.assertIn("正在免费领取（0）", md)
                self.assertNotIn("已结束 / 已失效（1）", md)

    def test_expired_by_reliable_deadline_even_if_source_fails(self):
        game = {"id": "epic:late", "platform": "Epic", "title": "Ended",
                "url": "https://store.epicgames.com/p/late",
                "end": "2026-10-10T11:00:00Z", "note": "Promotion"}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "current.json"
            path.write_text(json.dumps([game]), encoding="utf-8")
            with (patch.object(radar, "CURRENT_FILE", path),
                  patch.object(radar, "EXPIRED_FILE", Path(temp) / "expired.json")):
                active, expired = radar.reconcile_games([], NOW, set())
                self.assertEqual(active, [])
                self.assertEqual(expired[0]["invalid_reason"], "已到截止时间")
                self.assertEqual(expired[0]["invalid_at"], "2026-10-10T11:00:00+00:00")

    def test_steam_naive_deadline_requires_source_absence(self):
        game = {"id": "steam:old", "platform": "Steam", "title": "No TZ",
                "url": "https://www.gamerpower.com/open/steam",
                "end": "2026-10-01 23:59:00", "note": "Giveaway"}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "current.json"
            path.write_text(json.dumps([game]), encoding="utf-8")
            with (patch.object(radar, "CURRENT_FILE", path),
                  patch.object(radar, "EXPIRED_FILE", Path(temp) / "expired.json")):
                active, archived = radar.reconcile_games([game], NOW, {"Steam"})
                self.assertEqual(active[0]["status"], "active")
                self.assertEqual(archived, [])
                active, archived = radar.reconcile_games([], NOW, {"Steam"})
                self.assertFalse(active)
                self.assertEqual(archived[0]["invalid_reason"], "来源不再列出")

    def test_expired_reappearance_is_restored_and_archive_deduped(self):
        game = {"id": "epic:back", "platform": "Epic", "title": "Returned",
                "url": "https://store.epicgames.com/p/back",
                "end": "2026-10-16T15:00:00Z",
                "added_at": "2026-10-09T12:00:00Z", "note": "Promotion"}
        archive = dict(game, invalid_reason="来源不再列出",
                       invalid_at="2026-10-10T11:00:00Z")
        with tempfile.TemporaryDirectory() as temp:
            current = Path(temp) / "current.json"
            archived = Path(temp) / "expired.json"
            current.write_text("[]", encoding="utf-8")
            archived.write_text(json.dumps([archive]), encoding="utf-8")
            with (patch.object(radar, "CURRENT_FILE", current),
                  patch.object(radar, "EXPIRED_FILE", archived)):
                active, expired = radar.reconcile_games([game], NOW, {"Epic"})
                self.assertEqual(len(active), 1)
                self.assertEqual(active[0]["status"], "active")
                self.assertEqual(active[0]["added_at"], game["added_at"])
                self.assertEqual(expired, [])

    def test_archive_retention_and_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            recent = [
                {"id": f"epic:{i}", "platform": "Epic", "title": f"Game{i}",
                 "url": "https://store.epicgames.com/",
                 "invalid_at": "2026-10-10T11:00:00Z",
                 "invalid_reason": "来源不再列出"}
                for i in range(90)
            ]
            recent.append({"id": "epic:veryold", "platform": "Epic",
                           "title": "Old", "url": "https://store.epicgames.com/",
                           "invalid_at": "2026-07-01T10:00:00Z",
                           "invalid_reason": "来源不再列出"})
            archive = Path(temp) / "expired.json"
            archive.write_text(json.dumps(recent), encoding="utf-8")
            with (patch.object(radar, "CURRENT_FILE", Path(temp) / "current.json"),
                  patch.object(radar, "EXPIRED_FILE", archive)):
                active, expired = radar.reconcile_games([], NOW, set())
                self.assertEqual(active, [])
                self.assertEqual(len(expired), 80)
                self.assertNotIn("epic:veryold", {x["id"] for x in expired})

    def test_scan_sends_only_new_confirmed_active_not_unverified(self):
        old = {"id": "epic:pending", "platform": "Epic", "title": "Pending",
               "url": "https://store.epicgames.com/p/pending",
               "end": "2026-10-16T15:00:00Z", "note": "Promotion"}
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "current.json").write_text(json.dumps([old]), encoding="utf-8")
            with (patch.object(radar, "SENT_FILE", directory / "sent.json"),
                  patch.object(radar, "FIRST_SEEN_FILE", directory / "first_seen.json"),
                  patch.object(radar, "CURRENT_FILE", directory / "current.json"),
                  patch.object(radar, "EXPIRED_FILE", directory / "expired.json"),
                  patch.object(radar, "OUTPUT_FILE", directory / "FREE_GAMES.md"),
                  patch.object(radar, "collect_games", return_value=([], ["Epic 网络错误"], set())),
                  patch.object(radar, "bark_notify") as bark,
                  patch.dict(os.environ, {"BARK_URL": "https://api.day.app/test",
                                          "NTFY_TOPIC": ""})):
                radar.scan()
                bark.assert_not_called()
                md = radar.OUTPUT_FILE.read_text(encoding="utf-8")
                self.assertIn("待核实（1）", md)
                self.assertIn("正在免费领取（0）", md)

    def test_epic_malformed_payload_is_error_not_zero_offers(self):
        with self.assertRaises(ValueError):
            radar.parse_epic({"data": {"Catalog": {}}}, NOW, "zh-CN")



if __name__ == "__main__":
    unittest.main()
