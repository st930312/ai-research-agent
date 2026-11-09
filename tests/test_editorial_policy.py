import unittest
from src.editorial_policy import industry_eligible, gaming_eligible
from src.editorial_digest import cap_selection

class EditorialQualityTests(unittest.TestCase):
    def row(self,title,category,publisher="",url="https://example.org/story"):
        return {"id":1,"title":title,"url":url,"category":category,
                "source":"rss","suggested_category":category,
                "publisher":publisher,"importance":2}

    def test_finance_source_provenance_not_keyword(self):
        self.assertTrue(industry_eligible(self.row(
            "Factory capacity outlook", "finance", "Semiconductor Engineering")))
        self.assertFalse(industry_eligible(self.row(
            "Semiconductor market miracle", "finance", "Unknown publisher")))
        self.assertFalse(industry_eligible(self.row(
            "Fintech insights", "finance", "TechCrunch Fintech",
            "https://github.com/owner/repo")))

    def test_games_are_not_keyword_filtered(self):
        a=self.row("Astral Tide: Echoes chapter expansion","gaming","Gematsu")
        b=self.row("Steam price promotion","gaming","Gematsu")
        self.assertTrue(gaming_eligible(a))
        self.assertTrue(gaming_eligible(b))
        self.assertEqual(len(cap_selection([a])),1)

if __name__=="__main__":
    unittest.main()
