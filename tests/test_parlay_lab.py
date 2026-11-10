import unittest
import pandas as pd
from parlay_lab import _candidates, dual_model_eligible, _join_bankroll_safe_lines, _market_label

class ParlayLabTests(unittest.TestCase):
    def test_dual_model_strict_agreement(self):
        data=pd.DataFrame([
            {"Player":"A","Recent hits":3,"Huie baseline":7,"Safe line":6,"Sam projection":8},
            {"Player":"B","Recent hits":3,"Huie baseline":6,"Safe line":6,"Sam projection":8},
            {"Player":"C","Recent hits":3,"Huie baseline":7,"Safe line":6,"Sam projection":6},
            {"Player":"D","Recent hits":3,"Huie baseline":7,"Safe line":6,"Sam projection":None},
            {"Player":"E","Recent hits":1,"Huie baseline":7,"Safe line":6,"Sam projection":8},
        ])
        self.assertEqual(dual_model_eligible(data)["Player"].tolist(),["A"])

    def test_missing_columns_safe(self):
        data=pd.DataFrame({"Player":["A"]})
        self.assertTrue(dual_model_eligible(data).empty)

    def test_daily_workbook_headers(self):
        df=pd.DataFrame([{"Player":"Sample Player","Market":"Points","Safer line":"15+",
                          "Model projection":19.1,"Last game":18,"2 games":20,"3 games":17,
                          "Game":"BOS at NYK"}])
        picks=_candidates(df)
        self.assertEqual(len(picks),1)
        self.assertEqual(picks.iloc[0]["Recent hits"],3)
        self.assertAlmostEqual(picks.iloc[0]["Huie baseline"],round(55/3,2))

    def test_missing_recent_game_not_imputed(self):
        df=pd.DataFrame([{"Player":"Sample Player","Market":"Points","Safer line":"15+",
                          "Model projection":19.1,"Last game":18,"2 games":20,
                          "Game":"BOS at NYK"}])
        self.assertTrue(_candidates(df).empty)

    def test_join_across_game_label_and_player_abbreviation(self):
        bankroll=pd.DataFrame([{"Player":"S. Curry","Game":"GSW @ LAL",
                                 "Our play":"Over 3 threes","Safer line":"3+ Threes"}])
        props=pd.DataFrame([{"Player":"Stephen Curry","Game":"GSW at LAL","Market":"3PM",
                             "Model projection":4.8,"Last game":5,"2 games ago":4,
                             "3 games ago":4}])
        diagnostics={}
        joined=_join_bankroll_safe_lines(bankroll,props,diagnostics)
        self.assertEqual(diagnostics["matched_rows"],1)
        picks=_candidates(joined)
        self.assertEqual(len(picks),1)
        self.assertEqual(picks.iloc[0]["Market"],"Threes")
        self.assertEqual(picks.iloc[0]["Safe line"],3)
        self.assertEqual(picks.iloc[0]["Sam projection"],4.8)

    def test_unique_market_allows_different_game_labels(self):
        bankroll=pd.DataFrame([{"Player":"Aaron Gordon","Game":"DEN at HOU",
                                 "Our play":"over rebounds","Safer line":"5+"}])
        props=pd.DataFrame([{"Player":"A. Gordon","Game":"Denver Nuggets vs Houston Rockets",
                             "Market":"Rebounds","Model projection":7,
                             "Last game":6,"2 games ago":8,"3 games ago":7}])
        diag={}
        joined=_join_bankroll_safe_lines(bankroll,props,diag)
        self.assertEqual(len(joined),1)
        self.assertEqual(diag["game_label_fallbacks"],1)

    def test_ambiguous_player_market_rejected(self):
        bankroll=pd.DataFrame([{"Player":"A. Thompson","Game":"Unknown",
                                 "Our play":"Points","Safer line":"12+"}])
        props=pd.DataFrame([{"Player":n,"Game":"Unknown","Market":"Points",
                             "Model projection":15,"Last game":12,"2 games ago":13,
                             "3 games ago":14} for n in ("Amen Thompson","Ausar Thompson")])
        self.assertTrue(_join_bankroll_safe_lines(bankroll,props).empty)

    def test_three_point_field_goals_end_to_end(self):
        bankroll=pd.DataFrame([{"Player":"S. Curry","Game":"GSW @ LAL",
                                 "Our play":"Over 3-point field goals","Safer line":"3+"}])
        props=pd.DataFrame([{"Player":"Stephen Curry","Game":"GSW at LAL",
                             "Market":"3-point field goals","Model projection":4.8,
                             "Last game":5,"2 games ago":4,"3 games ago":4}])
        picks=_candidates(_join_bankroll_safe_lines(bankroll,props))
        self.assertEqual(len(picks),1)
        self.assertEqual(picks.iloc[0]["Market"],"Threes")

    def test_market_classifier_does_not_confuse_3point_with_points(self):
        self.assertEqual(_market_label("3-point field goals"),"Threes")
        self.assertEqual(_market_label("over 2.5 3PM"),"Threes")
        self.assertIsNone(_market_label("Points + Rebounds"))

    def test_matched_picks_with_missing_last_games_remain_visible(self):
        bankroll=pd.DataFrame([{"Player":"S. Curry","Game":"GSW @ LAL",
                                 "Our play":"OVER 1.5 threes fg3m","Safer line":"1+ threes fg3m"}])
        props=pd.DataFrame([{"Player":"Stephen Curry","Game":"GSW at LAL",
                             "Market":"3-point field goals","Model projection":4.1,
                             "Last game":"—","2 games ago":"—","3 games ago":"—",
                             "Last 3 avg":3.8}])
        joined=_join_bankroll_safe_lines(bankroll,props)
        self.assertEqual(len(joined),1)
        picks=_candidates(joined)
        self.assertEqual(len(picks),1)
        self.assertAlmostEqual(picks.iloc[0]["Huie baseline"],3.8)
        self.assertEqual(picks.iloc[0]["Baseline source"],"Workbook last-3 average")
        self.assertTrue(pd.isna(picks.iloc[0]["Recent hits"]))
        self.assertTrue(dual_model_eligible(picks).empty)

    def test_no_history_and_no_average_does_not_create_baseline(self):
        df=pd.DataFrame([{"Player":"Sample Player","Market":"Assists","Safer line":"4+",
                         "Model projection":6,"Last game":"—",
                         "2 games ago":"—","3 games ago":"—"}])
        picks=_candidates(df)
        self.assertEqual(len(picks),1)
        self.assertTrue(pd.isna(picks.iloc[0]["Huie baseline"]))
        self.assertTrue(pd.isna(picks.iloc[0]["Recent hits"]))
        self.assertTrue(dual_model_eligible(picks).empty)

    def test_candidate_stat_values(self):
        df=pd.DataFrame([{"Player":"Sample Player","Market":"Rebounds","Safer line":"6+",
                          "Model projection":8.1,"Last game":8,"2 games ago":7,"3 games ago":9,"Game":"A at B"}])
        picks=_candidates(df)
        self.assertEqual(len(picks),1)
        self.assertEqual(float(picks.iloc[0]["Huie baseline"]),8.0)
        self.assertEqual(float(picks.iloc[0]["Safe line"]),6.0)

if __name__=="__main__":
    unittest.main()
