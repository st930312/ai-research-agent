import unittest

from src.editorial_policy import industry_eligible, gaming_eligible
from src.editorial_digest import cap_selection


class EditorialQualityTests(unittest.TestCase):
    def row(self, title, url, category):
        return {"id":1, "title":title, "url":url, "category":category,
                "source":"rss", "importance":2}

    def test_finance_rejects_off_topic_sources_from_actual_preview(self):
        examples = [
            self.row("codon torus syntax", "https://github.com/some/repo", "finance"),
            self.row("TechCrunch Founder Summit 2026 today is the day",
                     "https://techcrunch.com/2026/11/04/founder-summit/", "finance"),
            self.row("AI world model demo", "https://www.youtube.com/watch?v=sample", "finance"),
        ]
        for row in examples:
            self.assertFalse(industry_eligible(row))
        self.assertEqual(cap_selection(examples), [])

    def test_finance_accepts_genuine_global_industry_news(self):
        cases = [
            "SK hynix boosts HBM capacity for data centers",
            "Global semiconductor equipment demand grows",
            "Banking payment network reforms change settlement",
            "ASML expands lithography manufacturing",
            "Revolut announces new digital banking regulation",
            "台積電先進封裝產能調整",
        ]
        for title in cases:
            self.assertTrue(industry_eligible(
                self.row(title, "https://example.com/article", "finance")), title)

    def test_gaming_avoids_ordinary_rereleases_and_promotions(self):
        cases = [
            "經營遊戲合集 Switch 2 盒裝版上市",
            "手遊事前登錄活動啟動",
            "Steam 秋季特價促銷開始",
            "Game bundle physical edition available",
        ]
        for title in cases:
            self.assertFalse(gaming_eligible(
                self.row(title, "https://example.org/game", "gaming")), title)

    def test_gaming_keeps_platform_or_mobile_discovery(self):
        for title in [
            "Epic Games Launcher is coming to SteamOS",
            "創意新作手機遊戲全球上市",
            "Steam announces major update",
            "任天堂新作首度公開獨特玩法",
        ]:
            self.assertTrue(gaming_eligible(
                self.row(title, "https://example.org/game", "gaming")), title)


if __name__ == "__main__":
    unittest.main()
