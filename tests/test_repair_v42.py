import unittest
from unittest.mock import Mock,patch
from datetime import datetime,timezone
from src.repair_v42_roundups import START, get_repair_rows, valid_body, build_correction

class RepairTests(unittest.TestCase):
    def db(self):
        items=[]
        for cat in ("gaming","finance"):
            for i in range(3):
                items.append({
                    "url":f"https://example.org/{cat}/{i}",
                    "title":f"{cat} verified event {i}",
                    "category":cat,"source":"rss",
                    "event_summary":f"Verified report {i}",
                    "published_at":datetime(2026,11,9,9,19,15,tzinfo=timezone.utc),
                })
        return Mock(recent=Mock(return_value=items))

    def test_only_corrects_known_previous_stories(self):
        rows=get_repair_rows(self.db())
        self.assertEqual(len(rows["gaming"]),3)
        self.assertEqual(len(rows["finance"]),3)

    def test_no_placeholders_or_missing_sections(self):
        for body in ("本則 AI 摘要未完整產生"*40,"新聞摘要"*5,
                     "①資料"*100+"②資料"*30):
            with self.assertRaises(RuntimeError):
                valid_body(body)

    def test_draft_both_before_any_send(self):
        db=self.db()
        draft="① "+("已發生事件及其重要性。"*12)+"\n② "+("另一事件可確認事實。"*12)+"\n③ "+("第三事件與影響。"*12)
        with patch("src.repair_v42_roundups.enrich",side_effect=lambda row:{
             **row,"body_excerpt":"Read-only verified content","body_status":"ok"}):
            messages=build_correction(db,request=lambda *args,**kwargs:draft)
        self.assertTrue(any("V4.2 內文補正版" in msg for msg in messages))
        self.assertTrue(any("gaming" in msg for msg in messages))
        self.assertTrue(any("finance" in msg for msg in messages))

    def test_missing_one_category_blocks_publication(self):
        db=self.db()
        db.recent.return_value=db.recent.return_value[:-1]
        with self.assertRaisesRegex(RuntimeError,"Expected exactly 3"):
            build_correction(db)

if __name__=="__main__":
    unittest.main()
