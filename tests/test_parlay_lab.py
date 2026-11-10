import unittest
import pandas as pd
from parlay_lab import _candidates, dual_model_eligible

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
        self.assertAlmostEqual(picks.iloc[0]["Huie baseline"],55/3)

    def test_missing_recent_game_not_imputed(self):
        df=pd.DataFrame([{"Player":"Sample Player","Market":"Points","Safer line":"15+",
                          "Model projection":19.1,"Last game":18,"2 games":20,
                          "Game":"BOS at NYK"}])
        self.assertTrue(_candidates(df).empty)

    def test_candidate_stat_values(self):
        df=pd.DataFrame([{"Player":"Sample Player","Market":"Rebounds","Safer line":"6+",
                          "Model projection":8.1,"Last game":8,"2 games ago":7,"3 games ago":9,"Game":"A at B"}])
        picks=_candidates(df)
        self.assertEqual(len(picks),1)
        self.assertEqual(float(picks.iloc[0]["Huie baseline"]),8.0)
        self.assertEqual(float(picks.iloc[0]["Safe line"]),6.0)

if __name__=="__main__":
    unittest.main()
