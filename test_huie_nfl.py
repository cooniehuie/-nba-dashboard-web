"""Regression tests for dated NFL forecasts and conservative result grading."""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest
import huie_nfl_projections as nfl
from huie_daily_performance import _stat_summary

GAME={"id":"123","game":"WSH @ NYG","date":"2026-11-13T01:15Z","week":10,"season":2026,"state":"post",
      "teams":[{"id":"28","abbr":"WSH"},{"id":"19","abbr":"NYG"}]}
PLAYER={"id":"1","name":"Jayden Daniels","position":"QB","team_id":"28"}
LOGS=[{"date":f"2026-10-{10+i:02d}","stats":{"Passing yards":200+i*5,"Pass attempts":30}}
      for i in range(8)]

def archive(line=210.5):
    return {"2026-11-12|WAS @ NYG":{"date":"2026-11-12","matchup":"WAS @ NYG","rows":[
        {"Player":"J. Daniels","Team":"WAS","Market":"Passing yards","Reference line":line,"Sam projection":230},
        {"Player":"Unknown Player","Team":"NYG","Market":"Receptions","Reference line":2.5,"Sam projection":3}
    ]}}

def fake_roster(tid,season):
    return [PLAYER] if tid=="28" else []

def fake_logs(pid,season,cutoff):
    assert season==2026 and cutoff==GAME["date"]
    return LOGS

def fake_box(gid):
    return {"state":"post","available":True,"players":[
        {"id":"1","name":"Jayden Daniels","team":"WSH","stats":{"Passing yards":215}}],"absences":[]}

class TestNFL(unittest.TestCase):
    def test_exact_date_and_team(self):
        actual=nfl._sam_for_game(archive(),GAME)
        self.assertEqual(actual["date"],"2026-11-12")
        wrong={k:{**v,"date":"2026-11-14"} for k,v in archive().items()}
        self.assertIsNone(nfl._sam_for_game(wrong,GAME))
        self.assertIsNone(nfl._player_match("J. Smith",[{"name":"James Smith"},{"name":"Joe Smith"}]))

    def test_both_models_and_independent_forecast(self):
        with patch.object(nfl,"_roster",fake_roster),patch.object(nfl,"_depth_players",return_value=["1"]),patch.object(nfl,"_gamelog",fake_logs),patch.object(nfl,"league_defensive_snapshot") as defense:
            rows,_,_,covered=nfl._build_projections([GAME],archive(),{},use_defense=True)
            comparison,_,_,_=nfl._build_projections([GAME],archive(245),{},include_unlined=True)
            unlined,_,_,_=nfl._build_projections([GAME],{},{})
        defense.assert_not_called()
        self.assertEqual(covered,1)
        self.assertEqual(len(rows),2)
        value=rows.iloc[0]
        self.assertEqual(value["Player ID"],"1")
        self.assertEqual(value["Both models OVER"],"Yes")
        self.assertEqual(comparison.iloc[0]["Huie projection"],value["Huie projection"])
        self.assertEqual(unlined.iloc[0]["Huie projection"],value["Huie projection"])
        self.assertEqual(comparison.iloc[0]["Huie side"],"🔴 UNDER")
        self.assertEqual(rows.iloc[1]["Huie side"],"⚪ UNVERIFIED")

    def test_grade_results(self):
        original={"Player":"Jayden Daniels","Team":"WSH","Player ID":"1","Game":"WSH @ NYG",
                  "Game ID":"123","Market":"Passing yards","Reference line":210.5,
                  "Huie projection":220.5,"Huie side":"🟢 OVER"}
        rows=pd.DataFrame([original,{**original,"Reference line":215},{**original,"Huie side":"🔴 UNDER"},
                           {**original,"Market":"Rushing yards"},{**original,"Player":"Joe Other","Player ID":"3"},
                           {**original,"Game ID":"999"},{**original,"Huie side":"⚪ UNVERIFIED"}])
        box=fake_box("123")
        box["absences"]=[{"name":"Joe Other","team":"WSH"}]
        graded=nfl._grade_projections(rows,{"123":box})
        self.assertEqual(graded["Result"].tolist(),["Hit","Push","Miss","Unverified stat","DNP","Pending game","Unverified projection"])
        summary=_stat_summary(graded,nfl.MARKETS).set_index("Stat")
        self.assertEqual(summary.loc["Passing yards","Hit rate"],"50.0%")

    def test_nfl_route_without_nba_workbook(self):
        app=AppTest.from_file("app.py")
        app.secrets["ADMIN_PASSWORD"]="test-only"
        with patch.object(nfl,"_schedule_day",return_value=[GAME]),patch.object(nfl,"_game_rosters",
                               return_value=([{**PLAYER,"team":"WSH"}],["1"],0)),patch.object(nfl,"_gamelog",fake_logs):
            app.run()
            app.radio(key="site_nav").set_value("🏈 Huie NFL Projections").run()
        self.assertFalse(list(app.exception))
        self.assertTrue(any("Huie NFL Projections" in title.value for title in app.title))
        self.assertTrue(any(button.label=="Home" for button in app.button))
        self.assertFalse(any("Upload your NBA projections" in info.value for info in app.info))

    def test_streamlit_date_week_and_filters(self):
        fixture=AppTest.from_string('''
import json
from unittest.mock import patch
import huie_nfl_projections as n
from test_huie_nfl import GAME, archive, fake_roster, fake_logs, fake_box
def storage(path):
    return json.dumps({"games":archive()}) if path == n.ARCHIVE else None
with patch.object(n,"_schedule_day",return_value=[GAME]),patch.object(n,"_schedule",return_value=[GAME]),patch.object(n,"_current_week",return_value=10),patch.object(n,"_roster",fake_roster),patch.object(n,"_depth_players",return_value=["1"]),patch.object(n,"_gamelog",fake_logs),patch.object(n,"_event_box",fake_box):
    n.render(storage_read=storage)
''')
        fixture.run()
        self.assertFalse(list(fixture.exception))
        self.assertTrue(any(m.label=="Displayed props" and m.value=="2" for m in fixture.metric))
        self.assertTrue(any(m.label=="Total hits" and m.value=="1" for m in fixture.metric))
        fixture.checkbox(key="huie_nfl_games_both_only").set_value(True).run()
        self.assertFalse(list(fixture.exception))
        self.assertTrue(any(m.label=="Displayed props" and m.value=="1" for m in fixture.metric))
        self.assertTrue(any(m.label=="Unverified" and m.value=="1" for m in fixture.metric))
        fixture.button(key="huie_nfl_week10").click().run()
        self.assertFalse(list(fixture.exception))
        self.assertEqual(fixture.radio(key="huie_nfl_scope").value,"Full NFL week")
        fixture.selectbox(key="huie_nfl_matchup_v2").select("123").run()
        self.assertFalse(list(fixture.exception))
        self.assertTrue(any("Individual Games" in title.value for title in fixture.title))

if __name__=="__main__":
    unittest.main()
