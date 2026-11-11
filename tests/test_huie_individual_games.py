"""Regression tests for Huie's separate read-only Individual Games tab."""
import unittest
import pandas as pd
from streamlit.testing.v1 import AppTest
from huie_individual_games import prepare_projections

def props():
    return pd.DataFrame([
        {"Player":"Evan Mobley","Market":"Threes","Reference line":1.5,
         "Model projection":2.5,"Game":"Cleveland Cavaliers @ Charlotte Hornets",
         "Last game":None,"2 games ago":None,"3 games ago":None},
        {"Player":"J. Fears","Market":"Assists","Reference line":4.5,
         "Model projection":5.1,"Game":"New Orleans Pelicans @ Golden State Warriors",
         "Last game":None,"2 games ago":None,"3 games ago":None},
        {"Player":"Missing Player","Market":"Points","Reference line":8.5,
         "Model projection":13.5,"Game":"Cleveland Cavaliers @ Charlotte Hornets",
         "Last game":None,"2 games ago":None,"3 games ago":None},
        {"Player":"Even Line","Market":"Assists","Reference line":5,
         "Model projection":6.0,"Game":"New Orleans Pelicans @ Golden State Warriors",
         "Last game":5,"2 games ago":5,"3 games ago":5},
    ])

def history():
    return {
        ("Evan Mobley","CLE"):[
            {"date":f"2026-11-{d:02d}",
             "stats":{"Threes":float(1+d%4),"Minutes":30.0}} for d in range(1,13)
        ],
        ("Jeremiah Fears","NOP"):[
            {"date":f"2026-11-{d:02d}",
             "stats":{"Assists":float(3+d%4),"Minutes":32.0}} for d in range(1,13)
        ]
    }

class IndividualGamesLogicTests(unittest.TestCase):
    def test_all_games_matchup_labels_and_reference_line(self):
        result=prepare_projections(props(),history(),model_audit={})
        self.assertEqual(len(result),4)
        self.assertSetEqual(set(result["Game"]),{
            "Cleveland Cavaliers @ Charlotte Hornets",
            "New Orleans Pelicans @ Golden State Warriors"})
        evan=result.loc[result["Player"]=="Evan Mobley"].iloc[0]
        self.assertEqual(evan["Reference line"],1.5)
        self.assertEqual(evan["Sam projection"],2.5)
        self.assertTrue(pd.notna(evan["Huie projection"]))
        self.assertTrue(evan["Projection method"].startswith("ESPN"))
        self.assertAlmostEqual(evan["Huie edge"],round(evan["Huie projection"]-1.5,2))

    def test_missing_verified_history_stays_unknown(self):
        result=prepare_projections(props(),history(),model_audit={})
        missing=result.loc[result["Player"]=="Missing Player"].iloc[0]
        self.assertTrue(pd.isna(missing["Huie projection"]))
        self.assertEqual(missing["Huie side"],"⚪ UNVERIFIED")
        self.assertEqual(missing["Both models OVER"],"Unverified")

    def test_strict_reference_line_equality_not_over(self):
        result=prepare_projections(props(),history(),model_audit={})
        even=result.loc[result["Player"]=="Even Line"].iloc[0]
        self.assertEqual(even["Huie projection"],5)
        self.assertEqual(even["Huie side"],"⚪ AT LINE")
        self.assertEqual(even["Both models OVER"],"No")

    def test_independent_from_sam_projection(self):
        raw=props()
        low=prepare_projections(raw,history(),model_audit={})
        raw.loc[raw["Player"]=="Evan Mobley","Model projection"]=99.0
        high=prepare_projections(raw,history(),model_audit={})
        a=low.loc[low["Player"]=="Evan Mobley"].iloc[0]
        b=high.loc[high["Player"]=="Evan Mobley"].iloc[0]
        self.assertEqual(a["Huie projection"],b["Huie projection"])
        self.assertNotEqual(a["Sam projection"],b["Sam projection"])

    def test_no_history_never_fabricates_huie(self):
        result=prepare_projections(props(),{},model_audit={})
        self.assertTrue(result.loc[result["Player"]=="Evan Mobley","Huie projection"].isna().all())
        self.assertTrue(pd.notna(result.loc[result["Player"]=="Even Line","Huie projection"].iloc[0]))


APP=r'''
import pandas as pd
import huie_individual_games as huie
huie._historical_boxscores=lambda: ({
    ("Evan Mobley","CLE"):[
        {"date":f"2026-11-{d:02d}",
         "stats":{"Threes":2.0,"Minutes":30}} for d in range(1,12)
    ]},0)
huie._validated_audit=lambda history:{}
frame=pd.DataFrame([
    {"Player":"Evan Mobley","Market":"Threes","Reference line":1.5,
     "Model projection":2.5,"Game":"Cleveland Cavaliers @ Charlotte Hornets"},
    {"Player":"J. Fears","Market":"Assists","Reference line":4.5,
     "Model projection":5.1,"Game":"New Orleans Pelicans @ Golden State Warriors"}
])
huie.render(frame)
'''

class HuieIndividualGamesUITests(unittest.TestCase):
    def test_public_tab_renders_without_errors(self):
        app=AppTest.from_string(APP,default_timeout=90).run()
        self.assertFalse([str(e.message) for e in app.exception])
        titles=" ".join(str(v.value) for v in app.title)
        self.assertIn("Huie Projections",titles)
        self.assertTrue(any("Choose matchup" in str(x.label) for x in app.selectbox))
        self.assertGreater(len(app.dataframe),0, f"info={[x.message for x in app.info]} | warning={[x.message for x in app.warning]} | multiselect={[x.value for x in app.multiselect]} | expander={[x.label for x in app.expander]} | subheader={[x.value for x in app.subheader]} | checkbox={[x.value for x in app.checkbox]}")

    def test_single_game_selection(self):
        app=AppTest.from_string(APP,default_timeout=90).run()
        choices=app.selectbox[0].options
        self.assertIn("All games",choices)
        self.assertIn("Cleveland Cavaliers @ Charlotte Hornets",choices)
        app.selectbox[0].set_value("Cleveland Cavaliers @ Charlotte Hornets").run()
        self.assertFalse([str(e.message) for e in app.exception])
        self.assertTrue(any("Cleveland Cavaliers @ Charlotte Hornets" in str(e.value) for e in app.subheader), f"subheader={[x.value for x in app.subheader]}, info={[x.message for x in app.info]}, multiselect={[x.value for x in app.multiselect]}")

if __name__=="__main__":
    unittest.main()
