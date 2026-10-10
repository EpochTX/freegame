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
                patch.object(radar, "OUTPUT_FILE", Path(temp) / "FREE_GAMES.md"),
                patch.object(radar, "collect_games", return_value=([game], [])),
                patch.object(radar, "bark_notify") as bark,
                patch.dict(os.environ, {"BARK_URL": "https://api.day.app/test",
                                        "MAX_PUSH": "8"}),
            ):
                radar.scan()
                radar.scan()
                self.assertEqual(bark.call_count, 1)
                self.assertEqual(len(json.loads(radar.SENT_FILE.read_text())), 1)
                self.assertTrue(radar.OUTPUT_FILE.exists())

    def test_no_bark_secret_does_not_mark_sent(self):
        with patch.dict(os.environ, {"BARK_URL": ""}):
            with self.assertRaises(RuntimeError):
                radar.scan()

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
                patch.object(radar, "OUTPUT_FILE", Path(temp) / "FREE_GAMES.md"),
                patch.object(radar, "collect_games", return_value=([game], [])),
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

if __name__ == "__main__":
    unittest.main()
