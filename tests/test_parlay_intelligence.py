import unittest
from datetime import datetime, timezone, timedelta, date
from parlay_context import (parse_injuries, injury_status, parse_game,
                            starters_from_summary, nba_confirmed_starters, starter_match, game_metrics, matchup_adjustment)
from parlay_quotes import validate_quotes, match_quote
from parlay_calibration import train, predict, examples
from parlay_joint import correlated_joint

class ContextTests(unittest.TestCase):
    def test_injury_filter_and_unknown(self):
        report=parse_injuries({"injuries":[{"team":{"abbreviation":"GSW"},"injuries":[
            {"athlete":{"displayName":"Stephen Curry"},"status":"Out"},
            {"athlete":{"displayName":"Draymond Green"},"status":"Questionable"}]}]})
        self.assertEqual(injury_status("S. Curry","GSW",report)[0],"block")
        self.assertEqual(injury_status("D. Green","GSW",report)[0],"review")
        self.assertEqual(injury_status("K. Thompson","",report)[0],"unlisted")
        self.assertEqual(parse_game("GSW at BOS"),("GSW","BOS"))

    def test_confirmed_starter_not_projected(self):
        data={"boxscore":{"players":[{"team":{"abbreviation":"BOS"},
            "statistics":[{"athletes":[
                {"starter":True,"athlete":{"displayName":"Jayson Tatum"}},
                {"starter":False,"athlete":{"displayName":"Bench Guy"}}]}]}]}}
        self.assertIn(("BOS","jayson tatum"),starters_from_summary(data))
        self.assertNotIn(("BOS","bench guy"),starters_from_summary(data))

    def test_nba_official_five_starters(self):
        schedule={"scoreboard":{"games":[{"gameId":"0022600190",
            "gameTimeUTC":"2026-11-10T03:00:00Z",
            "awayTeam":{"teamTricode":"LAL"},"homeTeam":{"teamTricode":"GSW"}}]}}
        def fake(url):
            def team(abbr,prefix):
                return {"teamTricode":abbr,"players":[{"starter":"1",
                    "firstName":prefix,"familyName":str(i)} for i in range(5)]}
            return {"game":{"awayTeam":team("LAL","Away"),"homeTeam":team("GSW","Home")}}
        found=nba_confirmed_starters(schedule,date(2026,11,9),fetch=fake)
        self.assertEqual(len(found),1)
        self.assertEqual(len(next(iter(found.values()))["players"]),10)
        names=next(iter(found.values()))["players"]
        self.assertTrue(starter_match("A. 0","LAL",names))
        self.assertIsNone(starter_match("B. Bench","",names))
        self.assertEqual(nba_confirmed_starters(schedule,date(2026,11,8),fetch=fake),{})

    def test_final_boxscore_pace(self):
        def team(abbrev,pts):
            return {"team":{"abbreviation":abbrev},"score":str(pts),
                "statistics":[{"name":"fieldGoalsMade-fieldGoalsAttempted","displayValue":"40-90"},
                              {"name":"freeThrowsMade-freeThrowsAttempted","displayValue":"20-25"},
                              {"name":"offensiveRebounds","displayValue":"12"},
                              {"name":"turnovers","displayValue":"15"}]}
        rows=game_metrics({"boxscore":{"teams":[team("GSW",106),team("BOS",109)]}})
        self.assertEqual(len(rows),2)
        self.assertGreater(rows[0]["pace"],90)
        five=rows*5
        adjustment=matchup_adjustment(five,"BOS","Points")
        self.assertIsNotNone(adjustment)
        self.assertLessEqual(adjustment["factor"],1.0816)
        self.assertIsNone(matchup_adjustment(rows,"BOS","Points"))

class QuoteTests(unittest.TestCase):
    def quote(self,minutes=0):
        now=datetime.now(timezone.utc)
        return {"contracts":[{"player":"Stephen Curry","market":"Threes","line":3,
            "side":"yes","contract_id":"123","price":.47,"fee":.02,
            "timestamp":(now-timedelta(minutes=minutes)).isoformat(),"payout":1}]}
    def test_fresh_only(self):
        quotes=validate_quotes(self.quote())
        self.assertEqual(len(quotes),1)
        self.assertEqual(match_quote("S. Curry","Threes",3,quotes)["price"],.47)
        self.assertIsNone(match_quote("S. Curry","Threes",4,quotes))
        self.assertEqual(validate_quotes(self.quote(minutes=30)),[])
    def test_missing_fee_or_id_never_accepted(self):
        item=self.quote()
        del item["contracts"][0]["fee"]
        self.assertEqual(validate_quotes(item),[])

class CalibratedModelTests(unittest.TestCase):
    def history(self):
        history={}
        for i in range(35):
            games=[]
            for d in range(22):
                games.append({"date":f"2026-10-{d+1:02d}","stats":{
                    "Points":10+(i%12)+(d%7)+(d*i%3),
                    "Rebounds":3+(i%8)+(d%3),
                    "Assists":2+(i%5)+(d%4),
                    "Threes":1+(i%4)+(d%3)}})
            history[(f"Player {i}","NBA")]=games
        return history
    def test_walkforward_and_holdout(self):
        h=self.history()
        x=examples(h)
        self.assertTrue(x["Points"])
        self.assertGreaterEqual(min(r["date"] for r in x["Points"]),"2026-10-06")
        result=train(h)
        self.assertIn("Points",result)
        self.assertGreater(result["Points"]["holdout_n"],100)
        self.assertIsNone(predict(11,10,3,{"calibrated":False}))
    def test_unavailable_history_withholds_probability(self):
        self.assertEqual(train({}),{})

class JointTests(unittest.TestCase):
    def test_correlated_scenario_requires_real_overlap(self):
        history={}
        for p in ("Player One","Player Two"):
            history[(p,"TEAM")]=[{"date":f"2026-10-{d+1:02d}",
                "stats":{"Points":10+(d%5)+(d*d%7)+(1 if p.endswith("One") else d%3)}} for d in range(29)]
        group=[{"Player":"P. One","Market":"Points","Calibrated probability":.7},
               {"Player":"P. Two","Market":"Points","Calibrated probability":.6}]
        result=correlated_joint(group,history)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result["scenario_probability"],.3)
        self.assertLessEqual(result["scenario_probability"],.6)
        self.assertIsNone(correlated_joint(group,{},minimum_overlap=10))

if __name__=="__main__":unittest.main()
