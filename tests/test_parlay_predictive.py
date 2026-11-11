import unittest
from parlay_predictive import clean_history, forecast, audit

def games_for_player(minutes, rate=.5, start_day=1):
    return [{"date":f"2026-10-{start_day+i:02d}",
             "stats":{"Points":round(m*rate,1),"Minutes":m}}
            for i,m in enumerate(minutes)]

class IndependentPredictiveModelTests(unittest.TestCase):
    def test_recency_minutes_affect_projection(self):
        # Increasing minutes at unchanged per-minute scoring should raise
        # the forward estimate over a longer-period static role.
        stable=games_for_player([24]*12)
        growth=games_for_player([24]*8+[34]*4)
        stable_pred=forecast(stable,"Points")
        growth_pred=forecast(growth,"Points")
        self.assertIsNotNone(growth_pred)
        self.assertGreater(growth_pred["projection"],stable_pred["projection"])
        self.assertEqual(growth_pred["minutes_signal"],"Rising minutes")
        self.assertEqual(growth_pred["games"],12)
        self.assertLessEqual(growth_pred["expected_minutes"],42.0)

    def test_recency_stat_rate_changes_without_minutes_change(self):
        games=games_for_player([30]*12,rate=.5)
        for game in games[-4:]:
            game["stats"]["Points"]=23
        new=forecast(games,"Points")
        base=forecast(games_for_player([30]*12,rate=.5),"Points")
        self.assertGreater(new["projection"],base["projection"])
        self.assertEqual(new["minutes_signal"],"Stable minutes")

    def test_order_independent_and_missing_skipped(self):
        games=games_for_player([30]*8)
        first=forecast(games,"Points")["projection"]
        self.assertEqual(first,forecast(list(reversed(games)),"Points")["projection"])
        games.append({"date":"2026-10-30","stats":{"Points":None,"Minutes":30}})
        self.assertEqual(first,forecast(games,"Points")["projection"])

    def test_no_synthetic_stats_or_book_lines(self):
        raw=[{"date":f"2026-10-{i:02d}",
              "stats":{"Points":10+i,"Minutes":30},
              "Model projection":999,"Reference line":0}
             for i in range(1,10)]
        pred=forecast(raw,"Points")
        self.assertGreater(pred["projection"],0)
        self.assertLess(pred["projection"],40)
        self.assertIsNone(forecast(raw[:2],"Points"))
        self.assertIsNone(forecast(raw,"Steals"))

    def test_graceful_fallback_without_minutes(self):
        raw=[{"date":f"2026-10-{i:02d}",
              "stats":{"Assists":float(i),"Minutes":None}} for i in range(1,10)]
        result=forecast(raw,"Assists")
        self.assertIn("minutes unavailable",result["method"])
        self.assertIsNone(result["expected_minutes"])
        self.assertIsNone(forecast(raw[:2],"Assists"))

    def test_rate_capped_under_extreme_recent_spike(self):
        g=games_for_player([30]*10,rate=.4)
        g[-1]["stats"]["Points"]=90
        p=forecast(g,"Points")
        simple=sum(x["stats"]["Points"] for x in g[-5:])/5
        self.assertLessEqual(p["projection"],round(1.28*simple,2))

    def test_rolling_audit_has_valid_observation_counts(self):
        history={}
        for player in range(25):
            rows=[]
            for d in range(1,30):
                minutes=24+(d%7)
                rows.append({"date":f"2026-10-{d:02d}",
                            "stats":{"Points":round(minutes*(.4+.02*(player%5)),1),
                                     "Minutes":minutes}})
            history[(f"Player {player}","NBA")]=rows
        scores=audit(history)
        self.assertIn("Points",scores)
        self.assertGreaterEqual(scores["Points"]["evaluated_games"],45)
        self.assertGreaterEqual(scores["Points"]["evaluation_dates"],4)
        self.assertLessEqual(scores["Points"]["adaptive_mae"],100)
        self.assertIn("enabled",scores["Points"])

    def test_insufficient_history_does_not_enable_model(self):
        history={("Sample Person","NBA"):games_for_player([28]*9)}
        self.assertFalse(audit(history).get("Points",{}).get("enabled",False))

if __name__=="__main__":
    unittest.main()
