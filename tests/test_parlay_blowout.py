import unittest
import pandas as pd
from streamlit.testing.v1 import AppTest

from parlay_blowout import (_audit, _probability, _rotation_blowout, assessment,
                           espn_rotation_game, fit)
from parlay_huie_projections import blowout_adjusted_projections
from huie_individual_games import prepare_projections


def fixture():
    # Boston is a clear favorite. There were reliably fewer minutes for
    # starters and more for deep bench in the verified lopsided sample.
    rows = [{"event_id": str(i), "date": f"2026-11-{i+1:02d}",
             "stats": {"Minutes": 36, "Points": 25, "Threes": 2},
             "starter": True} for i in range(6)]
    bins = {3: (45, 28)}
    return {"ratings": {"BOS": 1650, "DAL": 1400}, "team_games": {"BOS": 12, "DAL": 12},
            "labeled": (100, 20), "bins": bins,
            "game_probs": {str(i): .2 for i in range(6)},
            "effects": {("*", "Starter", True): (100,-500), ("*", "Starter",False): (100,100)},
            "history": {("jayson tatum","BOS"): rows}, "audit": {
                ("Minutes-normalized","Points"): {"enabled": True, "status": "Validated"},
                ("Minutes-normalized","Threes"): {"enabled": False, "status": "Baseline retained"}}}


class BlowoutTests(unittest.TestCase):
    def test_rotation_not_final_margin(self):
        def sub(out):
            return {"type":{"text":"Substitution"},
                    "participants":[{"athlete":{"id":"b"+out}},{"athlete":{"id":out}}]}
        turns = [(440,22,{}),(420,21,sub("1")),(310,22,sub("2")),
                 (240,24,sub("3")),(120,24,{}),(0,23,{})]
        self.assertIs(_rotation_blowout(turns,{"1","2","3"}), True)
        self.assertIsNone(_rotation_blowout([(c,m,{}) for c,m,p in turns],{"1","2","3"}))
        self.assertIs(_rotation_blowout([(c,min(m,12),p) for c,m,p in turns],{"1","2","3"}), False)
        # A comeback that reopens the game is not sustained garbage time.
        self.assertIs(_rotation_blowout(turns[:4]+[(120,5,{}),(0,21,{})],{"1","2","3"}), False)

    def test_bad_feed_and_no_chronological_leak(self):
        model=fit({},[{"id":"1","date":"2026-11-14","home":"BOS","away":"DAL","home_win":True,
                      "blowout":True,"neutral":False,"overtime":False}], "2026-11-14")
        self.assertEqual(model["team_games"],{})
        self.assertEqual(model["labeled"],(0,0))
        self.assertIsNone(_probability(model,"BOS","DAL"))
        event={"id":"1","season":{"type":2},"competitions":[{"competitors":[
            {"homeAway":"home","team":{"abbreviation":"BOS"},"score":130},
            {"homeAway":"away","team":{"abbreviation":"DAL"},"score":105}]}]}
        self.assertIsNone(espn_rotation_game(event,{},"2026-11-14")["blowout"])

    def test_only_improvement_is_enabled(self):
        def examples(new_min,new):
            return [(f"2026-11-{day:02d}",4,new_min,5,new) for day in range(1,8) for _ in range(20)]
        markets={("Adaptive","Points"):examples(3,4.8),("Adaptive","Assists"):examples(4,4.8),
                 ("Adaptive","Threes"):examples(3,4.99),("Adaptive","Rebounds"):examples(3,4.8)[:8]}
        audit=_audit(markets)
        self.assertTrue(audit["Adaptive","Points"]["enabled"])
        for market in ("Assists","Threes","Rebounds"):
            self.assertFalse(audit["Adaptive",market]["enabled"])

    def test_player_adjustment_is_centered_capped_and_gated(self):
        model=fixture()
        args=(model,"DAL @ BOS","Jayson Tatum","BOS")
        method="ESPN historical minutes-normalized fallback"
        pts=assessment(*args,"Points",method,36)
        self.assertGreater(pts["Blowout risk"],.2)
        self.assertLess(pts["Minutes adjustment"],0)
        self.assertGreaterEqual(pts["Minutes adjustment"],-3.5)
        self.assertEqual(assessment(*args,"Threes",method,36)["factor"],1)
        self.assertEqual(assessment(*args,"Points","3 separate games",36)["factor"],1)
        same_risk=pts["Blowout risk"]
        model["game_probs"]={str(i):same_risk for i in range(6)}
        self.assertAlmostEqual(assessment(*args,"Points",method,36)["Minutes adjustment"],0)

    def test_public_projection_updates_edge_and_both_over(self):
        model=fixture()
        hist=model["history"]
        props=pd.DataFrame([{"Player":"Jayson Tatum","Game":"DAL @ BOS","Market":"Points",
                             "Reference line":24.8,"Model projection":26}])
        original=prepare_projections(props,hist,model_audit={},blowout_model=model,apply_blowout=False)
        adjusted=prepare_projections(props,hist,model_audit={},blowout_model=model)
        self.assertEqual(original.iloc[0]["Both models OVER"],"Yes")
        self.assertEqual(adjusted.iloc[0]["Both models OVER"],"No")
        self.assertEqual(adjusted.iloc[0]["Huie side"],"🔴 UNDER")
        self.assertEqual(adjusted.iloc[0]["Sam projection"],26)
        self.assertEqual(adjusted.iloc[0]["Reference line"],24.8)


    def test_public_tab_toggle_and_explanation(self):
        app=AppTest.from_string('''
import pandas as pd
from unittest.mock import patch
from datetime import datetime
import huie_individual_games as page
from test_parlay_blowout import fixture
model=fixture()
class FixedDate(datetime):
    @classmethod
    def now(cls,*args):
        return cls(2026,11,15,12)
props=pd.DataFrame([{"Player":"Jayson Tatum","Game":"DAL @ BOS","Market":"Points",
                    "Reference line":24.8,"Model projection":26}])
with patch.object(page,"datetime",FixedDate), patch.object(page,"_nba_history_bundle",return_value=(model["history"],0,[{}])), patch.object(page,"_blowout_model",return_value={**model,"audit":{k:{**v,"sample":80,"dates":5,"base":6,"adjusted":5.5,"minutes_base":4,"minutes_adjusted":3.8} for k,v in model["audit"].items()}}), patch.object(page,"_validated_audit",return_value={}):
    page.render(props)
''')
        app.run()
        self.assertFalse(app.exception)
        grids=[el.value for el in app.dataframe if "Blowout risk" in el.value]
        self.assertTrue(grids)
        self.assertLess(grids[0].iloc[0]["Minutes adjustment"],0)
        app.checkbox(key="huie_nba_blowout").set_value(False).run()
        self.assertFalse(app.exception)
        grids=[el.value for el in app.dataframe if "Blowout risk" in el.value]
        self.assertEqual(grids[0].iloc[0]["Minutes adjustment"],0)
        self.assertEqual(grids[0].iloc[0]["Huie projection"],25)


if __name__ == "__main__":
    unittest.main()
