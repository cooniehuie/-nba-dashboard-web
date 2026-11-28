"""Dedicated Bankroll Builder wagers, separate from My Bets settlement ledger."""
import pandas as pd
import html
import streamlit as st

# Original Nov 10 bankroll funding; reinvested winnings do not increase this baseline.
# Start a new cycle only after the bankroll is depleted and new funding is recorded.
BANKROLL_CYCLE_STARTING_BALANCE = 398.85

PARLAYS = [
{"date":"2026-11-27","id":"5-Leg Threes + Assists · Spencer / Shead / Brunson / Collins / Wolf","event_id":"3c8c880a-d060-45b8-a6fa-1c206dc2a03c","contracts":334,"cost":99.89,"fees":4.7,"filled_at":"13:08","my_bets":"Nov 27 · Parlay 5","legs":[["C. Spencer","Threes",1],["J. Shead","Assists",4],["J. Brunson","Assists",4],["J. Collins","Threes",1],["D. Wolf","Threes",1]]},
{"date":"2026-11-27","id":"4-Leg Mixed · Embiid / Jerome / Wembanyama / Johnson","event_id":"ba38ec03-14b8-465c-988b-0a90baffb91b","contracts":225,"cost":99.65,"fees":3.35,"filled_at":"13:06","my_bets":"Nov 27 · Parlay 4","legs":[["J. Embiid","Rebounds",6],["T. Jerome","Points",15],["V. Wembanyama","Points",25],["J. Johnson","Assists",4]]},
{"date":"2026-11-25","id":"7-Leg Threes + Points + Rebounds + Assists · Spencer / Brunson / Jerome / Smith / Coward / Green / Towns","event_id":"a4a5db09-f97b-493d-b4cc-4fe5a14c6998","contracts":346,"cost":99.55,"fees":4.82,"filled_at":"14:53","my_bets":"Nov 25 · Parlay 2","legs":[["C. Spencer","Threes",1],["J. Brunson","Points",20],["T. Jerome","Points",15],["J. Smith","Rebounds",4],["C. Coward","Assists",2],["D. Green","Assists",4],["K. Towns","Assists",2]]},
{"date":"2026-11-25","id":"4-Leg Threes · Buzelis / Thomas / Harden / Wells","event_id":"61b2862b-099f-46d9-aeee-5db159e71f07","contracts":321,"cost":99.89,"fees":4.55,"filled_at":"14:51","my_bets":"Nov 25 · Parlay 1","legs":[["M. Buzelis","Threes",2],["M. Thomas","Threes",1],["J. Harden","Threes",2],["J. Wells","Threes",1]]},
{"date":"2026-11-23","id":"4-Leg Rebounds + Points · Barnes / Queen / Smith / Harden","contracts":333,"cost":99.93,"fees":4.69,"filled_at":"09:59","my_bets":"Nov 23 · Parlay 3","legs":[["S. Barnes","Rebounds",6],["D. Queen","Rebounds",4],["J. Smith","Rebounds",6],["J. Harden","Points",15]]},
{"date":"2026-11-23","id":"4-Leg Threes + Points · Harden / Proctor / Wembanyama / McCain","contracts":297,"cost":99.9,"fees":4.27,"filled_at":"09:53","my_bets":"Nov 23 · Parlay 2","legs":[["J. Harden","Threes",2],["T. Proctor","Threes",1],["V. Wembanyama","Points",25],["J. McCain","Points",10]]},
{"date":"2026-11-23","id":"4-Leg Assists · Mitchell / Giddey / Spencer / Hartenstein","contracts":260,"cost":99.75,"fees":3.81,"filled_at":"09:50","my_bets":"Nov 23 · Parlay 1","legs":[["D. Mitchell","Assists",4],["J. Giddey","Assists",8],["C. Spencer","Assists",4],["I. Hartenstein","Assists",2]]},
{"date":"2026-11-22","id":"5-Leg Assists + Rebounds · Daniels / Thompson / Giddey / Johnson / Reed","contracts":238,"cost":99.77,"fees":3.53,"filled_at":"10:06","my_bets":"Nov 22 · Parlay 3","legs":[["D. Daniels","Assists",4],["A. Thompson","Rebounds",6],["J. Giddey","Assists",6],["J. Johnson","Assists",4],["P. Reed","Rebounds",4]]},
{"date":"2026-11-22","id":"5-Leg Threes + Points + Rebounds · Wiggins / Nembhard / Smith / Gilgeous-Alexander / Johnson","contracts":235,"cost":97.73,"fees":3.48,"filled_at":"10:04","my_bets":"Nov 22 · Parlay 2","legs":[["A. Wiggins","Threes",2],["A. Nembhard","Threes",1],["J. Smith","Threes",1],["S. Gilgeous-Alexander","Points",25],["J. Johnson","Rebounds",6]]},
{"date":"2026-11-22","id":"4-Leg Rebounds · Daniels / Hartenstein / Bailey / Smith","contracts":266,"cost":99.09,"fees":3.88,"filled_at":"10:02","my_bets":"Nov 22 · Parlay 1","legs":[["D. Daniels","Rebounds",6],["I. Hartenstein","Rebounds",8],["A. Bailey","Rebounds",4],["J. Smith","Rebounds",6]]},
{"date":"2026-11-21","id":"5-Leg Threes · Holiday / Castle / Washington / Avdija / Hachimura","event_id":"52871b5c-8c97-460b-b2d3-a00d91b6d248","contracts":222,"cost":99.66,"fees":3.31,"filled_at":"13:45","my_bets":"Nov 21 · Parlay 4","legs":[["J. Holiday","Threes",1],["S. Castle","Threes",1],["P. Washington","Threes",1],["D. Avdija","Threes",1],["R. Hachimura","Threes",1]]},
{"date":"2026-11-21","id":"5-Leg Rebounds + Assists + Points · Wembanyama / Dunn / Williamson","event_id":"4f390282-4ce2-4e4b-8c71-319590ca1e75","contracts":378,"cost":99.86,"fees":4.98,"filled_at":"11:12","my_bets":"Nov 21 · Parlay 1","legs":[["V. Wembanyama","Rebounds",10],["K. Dunn","Assists",2],["V. Wembanyama","Points",25],["Z. Williamson","Points",15],["Z. Williamson","Assists",2]]},
{"date":"2026-11-20","id":"3-Leg Assists + Rebounds · Daniels / Diabate / Bey","contracts":243,"cost":99.82,"fees":3.59,"filled_at":"14:25","my_bets":"Nov 20 · Parlay 4","legs":[["D. Daniels","Assists",4],["M. Diabate","Rebounds",8],["S. Bey","Assists",2]]},
{"date":"2026-11-20","id":"5-Leg Assists + Rebounds · Shead / Thompson / Johnson / Mitchell / Daniels","contracts":290,"cost":99.85,"fees":4.18,"filled_at":"14:20","my_bets":"Nov 20 · Parlay 3","legs":[["J. Shead","Assists",4],["A. Thompson","Assists",2],["J. Johnson","Assists",6],["D. Mitchell","Assists",4],["D. Daniels","Rebounds",4]]},
{"date":"2026-11-20","id":"3-Leg Threes · Doncic / Wiggins / Harden","contracts":244,"cost":99.25,"fees":3.6,"filled_at":"14:16","my_bets":"Nov 20 · Parlay 2","legs":[["L. Doncic","Threes",3],["A. Wiggins","Threes",2],["J. Harden","Threes",2]]},
{"date":"2026-11-20","id":"4-Leg Threes + Points + Assists · Bey / Alexander-Walker / Doncic / Daniels","contracts":338,"cost":99.48,"fees":4.74,"filled_at":"14:15","my_bets":"Nov 20 · Parlay 1","legs":[["S. Bey","Threes",2],["N. Alexander-Walker","Threes",3],["L. Doncic","Points",30],["D. Daniels","Assists",4]]},
{"date":"2026-11-19","id":"3-Leg Threes + Rebounds · Jaquez / Lillard / Edey","contracts":259,"cost":99.63,"fees":3.80,"filled_at":"10:59","my_bets":"Nov 19 · Parlay 3","legs":[["J. Jaquez Jr.","Threes",1],["D. Lillard","Threes",3],["Z. Edey","Rebounds",6]]},
{"date":"2026-11-19","id":"5-Leg Points + Rebounds + Assists · Lillard / Boozer / Coward / Avdija / Holiday","contracts":230,"cost":99.52,"fees":3.42,"filled_at":"10:58","my_bets":"Nov 19 · Parlay 2","legs":[["D. Lillard","Points",15],["C. Boozer","Rebounds",6],["C. Coward","Assists",2],["D. Avdija","Assists",4],["J. Holiday","Points",10]]},
{"date":"2026-11-19","id":"5-Leg Points + Rebounds + Threes + Assists · Avdija / Holiday / Coward / Boozer","contracts":221,"cost":98.88,"fees":3.29,"filled_at":"10:55","my_bets":"Nov 19 · Parlay 1","legs":[["D. Avdija","Points",15],["D. Avdija","Rebounds",4],["J. Holiday","Threes",2],["C. Coward","Rebounds",6],["C. Boozer","Assists",2]]},
{"date":"2026-11-18","id":"4-Leg Threes + Points + Assists + Rebounds · Alexander-Walker / Doncic / Johnson / Okongwu","contracts":291,"cost":99.12,"fees":4.19,"filled_at":"12:13","my_bets":"Nov 18 · Parlay 6","legs":[["N. Alexander-Walker","Threes",3],["L. Doncic","Points",30],["J. Johnson","Assists",6],["O. Okongwu","Rebounds",6]]},
{"date":"2026-11-18","id":"4-Leg Assists + Rebounds · Edgecombe / Daniels / Thompson / Johnson","contracts":290,"cost":99.88,"fees":4.18,"filled_at":"12:12","my_bets":"Nov 18 · Parlay 5","legs":[["V. Edgecombe","Assists",2],["D. Daniels","Rebounds",6],["A. Thompson","Rebounds",6],["J. Johnson","Rebounds",8]]},
{"date":"2026-11-18","id":"3-Leg Threes · Jaquez / Doncic / Maxey","contracts":255,"cost":99.63,"fees":3.75,"filled_at":"12:09","my_bets":"Nov 18 · Parlay 4","legs":[["J. Jaquez Jr.","Threes",1],["L. Doncic","Threes",4],["T. Maxey","Threes",2]]},
{"date":"2026-11-18","id":"5-Leg Assists + Rebounds · James / Green / Embiid / Cunningham / Thompson","contracts":212,"cost":99.10,"fees":3.17,"filled_at":"12:08","my_bets":"Nov 18 · Parlay 3","legs":[["L. James","Assists",4],["D. Green","Assists",4],["J. Embiid","Rebounds",6],["C. Cunningham","Assists",6],["A. Thompson","Assists",2]]},
# Payout-only wins: costs inferred from Robinhood payout less realized profit; no original fill data.
{"date":"2026-11-17","id":"3-Leg Points + Rebounds + Threes · Cunningham / Thompson / Doncic","contracts":256,"cost":99.76,"fees":3.76,"filled_at":"08:25","my_bets":"Nov 17 · Parlay 1","legs":[["C. Cunningham","Points",20],["A. Thompson","Rebounds",6],["L. Doncic","Threes",4]]},
{"date":"2026-11-17","id":"4-Leg Rebounds + Assists · Clingan / Holiday / Bailey / Reed","contracts":234,"cost":99.65,"fees":3.48,"filled_at":"08:26","my_bets":"Nov 17 · Parlay 2","legs":[["D. Clingan","Rebounds",8],["J. Holiday","Assists",2],["A. Bailey","Rebounds",4],["P. Reed","Rebounds",6]]},
{"date":"2026-11-17","id":"3-Leg Threes · Jones Jr. / Thybulle / Allen","contracts":233,"cost":99.69,"fees":3.46,"filled_at":"08:32","my_bets":"Nov 17 · Parlay 3","legs":[["D. Jones Jr.","Threes",1],["M. Thybulle","Threes",1],["G. Allen","Threes",2]]},
{"date":"2026-11-17","id":"3-Leg Points + Assists · Doncic / Miller / Doncic","contracts":210,"cost":99.95,"fees":3.14,"filled_at":"10:57","my_bets":"Nov 17 · Parlay 4","legs":[["L. Doncic","Points",30],["B. Miller","Points",15],["L. Doncic","Assists",6]]},
{"date":"2026-11-16","id":"4-Leg Threes + Assists · Bane / Watson / Queen / Sheppard","contracts":334,"cost":98.54,"fees":4.69,"filled_at":"13:06","my_bets":"Nov 16 · Parlay 3","legs":[["D. Bane","Threes",2],["P. Watson","Assists",2],["D. Queen","Assists",2],["R. Sheppard","Assists",2]]},
{"date":"2026-11-16","id":"3-Leg Rebounds · Lendeborg / Sengun / Coward","contracts":264,"cost":99.69,"fees":3.86,"filled_at":"13:02","my_bets":"Nov 16 · Parlay 2","legs":[["Y. Lendeborg","Rebounds",6],["A. Sengun","Rebounds",8],["C. Coward","Rebounds",6]]},
{"date":"2026-11-16","id":"5-Leg Assists · Murray / Giddey / Suggs / Green / Avdija","contracts":220,"cost":99.20,"fees":3.28,"filled_at":"13:00","my_bets":"Nov 16 · Parlay 1","legs":[["J. Murray","Assists",4],["J. Giddey","Assists",6],["J. Suggs","Assists",2],["D. Green","Assists",4],["D. Avdija","Assists",4]]},
{"date":"2026-11-15","id":"4-Leg Rebounds + Assists · Brown / Maxey / Siakam / Kessler","contracts":253,"cost":99.86,"fees":3.72,"filled_at":"09:54","event_id":"84c62eb5-5955-4075-8010-ff288c30e8d2","my_bets":"Nov 15 · Parlay 3","legs":[["J. Brown","Rebounds",4],["T. Maxey","Assists",4],["P. Siakam","Rebounds",4],["W. Kessler","Rebounds",10]]},
{"date":"2026-11-15","id":"4-Leg Assists · Johnson / Daniels / Marshall / George","contracts":227,"cost":99.63,"fees":3.38,"filled_at":"11:39","my_bets":"Nov 15 · Parlay 7","legs":[["J. Johnson","Assists",6],["D. Daniels","Assists",4],["N. Marshall","Assists",2],["K. George","Assists",4]]},
{"date":"2026-11-15","id":"4-Leg Rebounds + Assists · Eason / Durant / Bailey / Flagg","contracts":256,"cost":99.76,"fees":3.76,"filled_at":"11:38","my_bets":"Nov 15 · Parlay 6","legs":[["T. Eason","Rebounds",4],["K. Durant","Rebounds",4],["A. Bailey","Rebounds",4],["C. Flagg","Assists",4]]},
{"date":"2026-11-15","id":"3-Leg Rebounds · Flagg / Sengun / Okongwu","contracts":229,"cost":99.82,"fees":3.41,"filled_at":"11:35","my_bets":"Nov 15 · Parlay 5","legs":[["C. Flagg","Rebounds",4],["A. Sengun","Rebounds",8],["O. Okongwu","Rebounds",6]]},
{"date":"2026-11-15","id":"3-Leg Points · Doncic / Irving / George","contracts":217,"cost":99.81,"fees":3.25,"filled_at":"11:34","my_bets":"Nov 15 · Parlay 4","legs":[["L. Doncic","Points",30],["K. Irving","Points",15],["K. George","Points",10]]},
{"date":"2026-11-14","id":"5-Leg Assists","contracts":241,"cost":99.12,"fees":3.56,"filled_at":"09:55","my_bets":"Nov 14 · Parlay 4","legs":[["J. Fears","Assists",4],["N. Marshall","Assists",2],["A. Thompson","Assists",2],["J. McDaniels","Assists",2],["J. Kuminga","Assists",2]]},
{"date":"2026-11-14","id":"3-Leg Rebounds","contracts":209,"cost":99.9,"fees":3.13,"filled_at":"09:53","my_bets":"Nov 14 · Parlay 3","legs":[["R. Gobert","Rebounds",8],["J. Kuminga","Rebounds",4],["A. Thompson","Rebounds",6]]},
{"date":"2026-11-14","id":"3-Leg Threes","contracts":242,"cost":99.9,"fees":3.58,"filled_at":"09:52","my_bets":"Nov 14 · Parlay 2","legs":[["T. Shannon Jr.","Threes",1],["A. Dosunmu","Threes",1],["D. Robinson","Threes",3]]},
{"date":"2026-11-14","id":"Points + Grant Threes","contracts":209,"cost":99.69,"fees":3.13,"filled_at":"09:51","my_bets":"Nov 14 · Parlay 1","legs":[["Z. Williamson","Points",15],["A. Dosunmu","Points",10],["D. Robinson","Points",10],["J. Grant","Threes",1]]},
 {"date":"2026-11-13","id":"3-Leg Threes · Spencer / Wiggins / Thomas","contracts":224,"cost":99.88,"fees":3.34,"filled_at":"10:48","event_id":"f9cb124c-3c15-4163-9afe-b415843b6064","my_bets":"Nov 13 · Parlay 2","legs":[("C. Spencer","Threes",1),("A. Wiggins","Threes",2),("M. Thomas","Threes",1)]},
 {"date":"2026-11-13","id":"3-Leg Threes · Thomas / Bane / Holiday","contracts":349,"cost":99.77,"fees":4.84,"filled_at":"10:32","event_id":"4d1c46b3-9287-45c1-85e4-9e6ebd0348b1","my_bets":"Nov 13 · Parlay 1","legs":[("M. Thomas","Threes",2),("D. Bane","Threes",3),("J. Holiday","Threes",2)]},
 {"date":"2026-11-13","id":"4-Leg Assists","contracts":231,"cost":99.99,"fees":3.43,"filled_at":"10:53","event_id":"e9f9a22a-3940-4b6d-b412-e19a4fed50b6","my_bets":"Nov 13 · Parlay 3","legs":[("C. Boozer","Assists",4),("F. Wagner","Assists",6),("A. Black","Assists",2),("J. Johnson","Assists",4)]},
 {"date":"2026-11-13","id":"Rebounds + Assists","contracts":266,"cost":99.56,"fees":3.88,"filled_at":"10:56","event_id":"72d6bdf1-b0a3-4dd4-ae62-8f4fe0cec4b4","my_bets":"Nov 13 · Parlay 4","legs":[("C. Boozer","Rebounds",8),("D. Mitchell","Assists",4),("T. Jerome","Assists",4),("J. Giddey","Assists",6)]},
 {"date":"2026-11-12","id":"Threes + Assists","contracts":226,"cost":99.87,"fees":3.37,"filled_at":"11:35","my_bets":"Nov 12 · Parlay 1","legs":[("G. Allen","Threes",3),("J. Goodwin","Threes",1),("C. Gillespie","Assists",2)]},
 {"date":"2026-11-12","id":"3-Leg Rebounds","contracts":207,"cost":99.77,"fees":3.1,"filled_at":"11:41","my_bets":"Nov 12 · Parlay 2","legs":[("A. Thompson","Rebounds",6),("R. Barrett","Rebounds",4),("R. Gobert","Rebounds",8)]},
 {"date":"2026-11-12","id":"Rebounds + Assists","contracts":225,"cost":98.78,"fees":3.35,"filled_at":"11:46","my_bets":"Nov 12 · Parlay 3","legs":[("M. Diabate","Rebounds",6),("C. Murray-Boyles","Rebounds",4),("P. Reed","Rebounds",4),("I. Quickley","Assists",4)]},
 {"date":"2026-11-12","id":"Points + Assists","contracts":238,"cost":98.67,"fees":3.52,"filled_at":"11:50","my_bets":"Nov 12 · Parlay 4","legs":[("K. George","Points",10),("D. Robinson","Points",10),("I. Quickley","Points",10),("J. Embiid","Assists",2),("J. McDaniels","Assists",2)]},
 {"date":"2026-11-11","id":"5-Leg Threes","contracts":327,"cost":99.09,"fees":4.62,"filled_at":"07:49","my_bets":"Nov 11 · Parlay 1","legs":[("E. Mobley","Threes",1),("M. Thomas","Threes",1),("C. Coward","Threes",1),("L. Doncic","Threes",3),("C. Spencer","Threes",1)]},
 {"date":"2026-11-11","id":"Rebounds + Assists","contracts":221,"cost":98.91,"fees":3.30,"filled_at":"07:54","my_bets":"Nov 11 · Parlay 2","legs":[("A. Drummond","Rebounds",4),("P. Siakam","Rebounds",4),("F. Wagner","Rebounds",4),("D. Mitchell","Assists",4)]},
 {"date":"2026-11-11","id":"4-Leg Assists","contracts":238,"cost":99.68,"fees":3.53,"filled_at":"07:57","my_bets":"Nov 11 · Parlay 3","legs":[("P. Siakam","Assists",2),("A. Nembhard","Assists",6),("C. Boozer","Assists",4),("D. Green","Assists",4)]},
 {"date":"2026-11-10","id":"Assists","contracts":286,"cost":99.26,"fees":4.13,"filled_at":"09:10","my_bets":"Nov 10 · Parlay 3","legs":[("K. Wagler","Assists",2),("C. Gillespie","Assists",2),("F. Wagner","Assists",6),("D. Acuff Jr.","Assists",6)]},
 {"date":"2026-11-10","id":"Three-Pointers","contracts":246,"cost":99.82,"fees":3.63,"filled_at":"09:04","my_bets":"Nov 10 · Parlay 2","legs":[("A. Simons","Threes",1),("D. Jones Jr.","Threes",1),("L. Markkanen","Threes",2),("D. Bane","Threes",2)]},
 {"date":"2026-11-10","id":"Rebounds","contracts":346,"cost":99.98,"fees":4.83,"filled_at":"09:02","my_bets":"Nov 10 · Parlay 1","legs":[("A. Drummond","Rebounds",4),("W. Carter Jr.","Rebounds",8),("A. Black","Rebounds",4),("I. Hartenstein","Rebounds",8)]}
,
 {"date":"2026-11-10","id":"Points + Assists","contracts":270,"cost":99.79,"fees":3.94,"filled_at":"16:38","event_id":"82529a37-8c56-483c-a25c-389dba487cd9","my_bets":"Nov 10 · Parlay 16","legs":[("T. Silva","Points",10),("W. Carter Jr.","Points",10),("A. Caruso","Assists",2)]}
]

# Verified against ESPN final NBA boxscores on Nov 21, 2026.
# These are game outcomes, NOT independently verified Robinhood settlements.
# DNP and missing athlete rows remain unverified; never convert them to misses.
FINAL_BOX_AUDIT = [
    {"Date":"2026-11-19","Bet":"Nov 19 · Parlay 1","Final result":"Miss","Verified legs":"Holiday 2 threes: hit; Coward 4 rebounds: miss; Boozer 5 assists: hit","Unverified":"Avdija points/rebounds: ESPN DNP (left foot)","ESPN":"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event=401910020"},
    {"Date":"2026-11-19","Bet":"Nov 19 · Parlay 2","Final result":"Robinhood-confirmed win","Verified legs":"Lillard 33 points; Boozer 6 rebounds; Coward 4 assists; Holiday 22 points","Unverified":"Avdija: ESPN DNP; Robinhood payout overrides box-score uncertainty","ESPN":"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event=401910020"},
    {"Date":"2026-11-19","Bet":"Nov 19 · Parlay 3","Final result":"Unverified","Verified legs":"Jaquez 1 three: hit; Lillard 5 threes: hit","Unverified":"Edey 6+ rebounds: no athlete row in ESPN boxscore","ESPN":"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event=401910019"},
    {"Date":"2026-11-20","Bet":"Nov 20 · Parlay 1","Final result":"Miss","Verified legs":"Bey 4 threes: hit; Alexander-Walker 2 threes: miss; Doncic 25 points: miss; Daniels 10 assists: hit","Unverified":"","ESPN":"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event=401909305"},
    {"Date":"2026-11-20","Bet":"Nov 20 · Parlay 2","Final result":"Miss","Verified legs":"Doncic 2 threes: miss; Wiggins 4 threes: hit; Harden 7 threes: hit","Unverified":"","ESPN":"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event=401909313"},
    {"Date":"2026-11-20","Bet":"Nov 20 · Parlay 3","Final result":"Miss","Verified legs":"Shead 4 assists: hit; Ausar Thompson 3 assists: hit; Johnson 6 assists: hit; Donovan Mitchell 3 assists: miss; Daniels 8 rebounds: hit","Unverified":"","ESPN":"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event=401909307"},
    {"Date":"2026-11-20","Bet":"Nov 20 · Parlay 4","Final result":"All targets reached","Verified legs":"Daniels 10 assists: hit; Diabate 15 rebounds: hit; Bey 3 assists: hit","Unverified":"Robinhood settlement not supplied","ESPN":"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event=401909305"},
]

def render_bankroll_parlays(espn_nba_boxscores,match_espn_player,confirmed_settlements=None):
    from parlay_live_tracking import render_live_parlays
    bets=[]
    # Stable purchase snapshots: one record per actual Robinhood order.
    # The same bets may appear in My Bets; do not add these totals again.
    # Number display labels independently for each date, in purchase-time order.
    # Preserve original IDs and My Bets keys for settlement matching.
    daily_numbers={}
    for p in sorted(PARLAYS,key=lambda x:(x["date"],x["filled_at"])):
        day=p["date"]
        day_numbers=daily_numbers.setdefault(day,{})
        day_numbers[id(p)]=len(day_numbers)+1
    for p in PARLAYS:
        date_label=pd.to_datetime(p["date"]).strftime("%m-%d-%y")
        number=daily_numbers[p["date"]][id(p)]
        bets.append({"date":p["date"],"id":p.get("event_id",p["id"]),
                     "label":f"({date_label}) Parlay {number} · {p['id']}",
                     "quantity":p["contracts"],"cost":p["cost"],"fees":p["fees"],
                     "time":p["filled_at"],"legs":p["legs"],
                     "my_bets":p.get("my_bets","")})
    outcomes=bankroll_outcomes(confirmed_settlements,espn_nba_boxscores,match_espn_player)
    render_live_parlays(bets,espn_nba_boxscores,match_espn_player,
                        outcomes,prefix="bankroll_parlays",
                        title="Bankroll Builder Parlays · Live Tracking")
    st.caption("Performance P/L includes verified final-game full-hold estimates where Robinhood settlements are unavailable; confirmed Robinhood payouts override estimates. Nov 19 Parlay 3 remains unverified.")
    with st.expander("Nov 19–20 · verified final box-score audit", expanded=True):
        st.caption("ESPN final NBA box scores checked Nov 21. A box-score hit or miss is not a Robinhood settlement; DNP and missing stats stay unverified.")
        st.dataframe(pd.DataFrame(FINAL_BOX_AUDIT),hide_index=True,use_container_width=True)


def automatic_game_results(espn_nba_boxscores, match_espn_player):
    """Compute box-score outcomes without treating them as Robinhood settlements."""
    feeds={}
    outcomes={}
    for p in PARLAYS:
        day=p["date"]
        if day not in feeds:
            try:
                feeds[day]=espn_nba_boxscores(day.replace("-",""))[1]
            except Exception:
                feeds[day]=[]
        statuses=[]
        for name,market,target in p["legs"]:
            athlete=match_espn_player(name,feeds[day],market)
            game=athlete.get("game",{}) if athlete else {}
            stat=athlete.get("stats",{}).get(market) if athlete else None
            if stat is None or athlete.get("dnp"):
                statuses.append("Unverified")
            elif stat>=target:
                statuses.append("Hit" if game.get("state")=="post" else "Live hit")
            elif game.get("state")=="post":
                statuses.append("Miss")
            else:
                statuses.append("Pending")
        if "Miss" in statuses:
            result="Game result: lost"
        elif all(s=="Hit" for s in statuses):
            result="Game result: won"
        else:
            result="Unverified / in progress"
        outcomes[(day,p["id"])]=result
    return outcomes

def inferred_settlements(espn_nba_boxscores, match_espn_player):
    """Full-hold contract outcomes. A final-game miss loses; all reached wins."""
    results={}
    feeds={}
    for p in PARLAYS:
        date=p["date"]
        if date not in feeds:
            try:
                feeds[date]=espn_nba_boxscores(date.replace("-",""))[1]
            except Exception:
                feeds[date]=[]
        hits=0
        misses=0
        for name,market,target in p["legs"]:
            athlete=match_espn_player(name,feeds[date],market)
            game=athlete.get("game",{}) if athlete else {}
            actual=athlete.get("stats",{}).get(market) if athlete else None
            if actual is not None and actual>=target:
                hits+=1
            elif actual is not None and game.get("state")=="post":
                misses+=1
        if misses:
            results[p["my_bets"]]={"status":"Loss","realized_profit":-p["cost"],"source":"Final box score"}
        elif hits==len(p["legs"]):
            results[p["my_bets"]]={"status":"Won","realized_profit":p["contracts"]-p["cost"],"source":"All targets reached"}
    return results


# Persist verified final-box-score outcomes in the performance statistics even
# when ESPN is temporarily unavailable. These are full-hold MODEL estimates,
# not Robinhood-confirmed settlements. Confirmed payouts always take priority.
VERIFIED_FINAL_BOX_OUTCOMES = {
    "Nov 19 · Parlay 1":{"status":"Loss","realized_profit":-98.88,"source":"Verified final box score · inferred full-hold P/L"},
    "Nov 20 · Parlay 1":{"status":"Loss","realized_profit":-99.48,"source":"Verified final box score · inferred full-hold P/L"},
    "Nov 20 · Parlay 2":{"status":"Loss","realized_profit":-99.25,"source":"Verified final box score · inferred full-hold P/L"},
    "Nov 20 · Parlay 3":{"status":"Loss","realized_profit":-99.85,"source":"Verified final box score · inferred full-hold P/L"},
    "Nov 20 · Parlay 4":{"status":"Won","realized_profit":143.18,"source":"Verified final box score · inferred full-hold P/L"},
}

def bankroll_outcomes(settlements, espn_nba_boxscores=None, match_espn_player=None):
    """Preserve confirmed transactions; otherwise use full-hold outcome rules."""
    results=dict(settlements or {})
    # A confirmed Robinhood settlement takes precedence over box-score estimates.
    for key,value in VERIFIED_FINAL_BOX_OUTCOMES.items():
        current=results.get(key,{})
        if current.get("realized_profit") is None or current.get("status") not in ("Won","Loss","Lost","Closed"):
            results[key]=dict(value)
    if espn_nba_boxscores is not None and match_espn_player is not None:
        inferred=inferred_settlements(espn_nba_boxscores,match_espn_player)
        for key,value in inferred.items():
            current=results.get(key,{})
            if current.get("realized_profit") is None or current.get("status") not in ("Won","Loss","Lost","Closed"):
                results[key]=value
    return results

def render_overview_parlay_pl(settlements, bankroll_history=None, espn_nba_boxscores=None, match_espn_player=None):
    """Match the existing Safe Line History hero with daily P/L bars."""
    outcomes=bankroll_outcomes(settlements,espn_nba_boxscores,match_espn_player)
    records=[]
    for p in PARLAYS:
        settlement=outcomes.get(p.get("my_bets",""),{})
        settled=(settlement.get("status") in ("Won","Loss","Lost","Closed")
                 and settlement.get("realized_profit") is not None)
        records.append({"Date":p["date"],"Parlay":p["id"],"Invested":float(p["cost"]),
                        "Realized P/L":float(settlement["realized_profit"]) if settled else None,
                        "Status":settlement.get("status") if settled else "Pending"})
    frame=pd.DataFrame(records)
    confirmed=frame.dropna(subset=["Realized P/L"])
    total=float(confirmed["Realized P/L"].sum())
    invested=float(frame["Invested"].sum())
    won=int((confirmed["Realized P/L"]>0).sum())
    lost=int((confirmed["Realized P/L"]<0).sum())
    pending=len(frame)-len(confirmed)
    daily=confirmed.groupby("Date")["Realized P/L"].sum().to_dict() if len(confirmed) else {}
    dates=sorted(frame["Date"].unique(),reverse=True)
    magnitude=max([abs(v) for v in daily.values()] or [1.0])
    bars=[]
    for date in dates:
        value=daily.get(date)
        label=pd.to_datetime(date).strftime("%b %-d")
        if value is None:
            height=4
            color="#94a3b8"
            amount="Pending"
        else:
            height=max(5,100*abs(value)/magnitude)
            color="#34d399" if value>=0 else "#fb7185"
            amount="${:+,.2f}".format(value)
        day_rows=frame[frame["Date"]==date]
        day_wins=int((day_rows["Realized P/L"]>0).sum())
        day_total=len(day_rows)
        bars.append('<div class="bkpl-bar-wrap"><div class="bkpl-bar-track"><div class="bkpl-bar" style="height:{:.1f}%;background:{}"></div></div><span>{}</span><b>{}</b><span class="bkpl-record">{} / {} won</span></div>'.format(height,color,label,amount,day_wins,day_total))
    total_label="${:+,.2f}".format(total) if len(confirmed) else "Pending"
    st.markdown("""<style>
    .bkpl-hero{border-radius:22px;padding:26px 30px;background:linear-gradient(125deg,#0f172a,#172554 62%,#0e7490);color:#fff;box-shadow:0 16px 35px #0f172a20;margin:14px 0 22px}
    .bkpl-kicker{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#93c5fd;font-weight:700}
    .bkpl-grid{display:grid;grid-template-columns:1.2fr 1fr;gap:24px;align-items:center}
    .bkpl-headline{display:flex;align-items:center;gap:22px;flex-wrap:wrap}
    .bkpl-growth{display:flex;flex-direction:column;gap:3px}
    .bkpl-growth strong{font-size:clamp(22px,2.6vw,36px);color:#a7f3d0;line-height:1.1}
    .bkpl-growth span{font-size:10px;letter-spacing:.09em;color:#cbd5e1}
    .bkpl-big{font-size:clamp(48px,6vw,82px);font-weight:850;line-height:1.12;letter-spacing:-.05em}
    .bkpl-muted{color:#cbd5e1;font-size:13px}
    .bkpl-stats{display:flex;gap:20px;flex-wrap:wrap;margin-top:18px}
    .bkpl-stat strong{display:block;font-size:25px;color:#fff}
    .bkpl-stat span{font-size:12px;color:#cbd5e1}
    .bkpl-track{height:12px;border-radius:30px;background:#ffffff30;overflow:hidden;margin:16px 0 7px}
    .bkpl-fill{height:100%;background:linear-gradient(90deg,#34d399,#a7f3d0);border-radius:30px}
    .bkpl-chart{display:flex;align-items:end;gap:7px;height:188px;padding-top:12px}
    .bkpl-bar-wrap{flex:1;min-width:0;text-align:center;display:flex;flex-direction:column;align-items:center;gap:5px;height:100%}
    .bkpl-bar-track{width:100%;height:118px;display:flex;align-items:end;border-radius:7px;background:#ffffff14;overflow:hidden}
    .bkpl-bar{width:100%;border-radius:6px 6px 0 0}
    .bkpl-bar-wrap span{font-size:10px;color:#cbd5e1;white-space:nowrap}
    .bkpl-bar-wrap b{font-size:10px;color:white;white-space:nowrap}
    .bkpl-record{font-size:10px;color:#cbd5e1;white-space:nowrap}
    @media(max-width:750px){
      .bkpl-hero{width:100%;max-width:100%;min-width:0;box-sizing:border-box;padding:16px;overflow:hidden}
      .bkpl-grid{grid-template-columns:minmax(0,1fr);gap:12px;min-width:0;max-width:100%}
      .bkpl-grid>div{min-width:0;max-width:100%;overflow:hidden}
      .bkpl-chart{width:100%;max-width:100%;min-width:0;box-sizing:border-box;height:160px;gap:6px;overflow-x:auto;overflow-y:hidden;padding-bottom:8px}
      .bkpl-bar-wrap{flex:0 0 70px;min-width:70px}
      .bkpl-big{font-size:46px}
    }
    /* Matches the compact Safe Line History sizing on phones for one-screen screenshots. */
    @media(max-width:750px){
      .bkpl-hero{padding:11px 13px!important;margin:4px 0 8px!important;border-radius:15px!important}
      .bkpl-kicker{font-size:9px!important;letter-spacing:.09em!important;line-height:1.2!important;white-space:nowrap}
      .bkpl-grid{gap:5px!important}
      .bkpl-big{font-size:36px!important;line-height:1.04!important}
      .bkpl-muted{font-size:10px!important;line-height:1.2!important}
      .bkpl-track{height:7px!important;margin:8px 0 4px!important}
      .bkpl-stats{gap:11px!important;flex-wrap:nowrap!important;margin-top:5px!important;align-items:start!important}
      .bkpl-stat{min-width:0}
      .bkpl-stat strong{font-size:16px!important;line-height:1.1!important;white-space:nowrap}
      .bkpl-stat span{font-size:8px!important;line-height:1.15!important}
      .bkpl-chart{height:108px!important;padding:4px 0 0!important;gap:5px!important}
      .bkpl-bar-track{height:57px!important;flex:0 0 57px!important;border-radius:5px!important}
      .bkpl-bar-wrap{flex:0 0 66px!important;min-width:66px!important;max-width:66px!important;gap:2px!important}
      .bkpl-bar-wrap span,.bkpl-bar-wrap b{font-size:9px!important;line-height:1.15!important}
    }
    </style>""",unsafe_allow_html=True)
    markup='''<div class="bkpl-hero"><div class="bkpl-kicker">🏀 BANKROLL BUILDER · PARLAY P/L HISTORY</div>
      <div class="bkpl-grid"><div><div class="bkpl-headline"><div class="bkpl-big">{}</div><div class="bkpl-growth"><strong>{:+.1f}%</strong><span>BANKROLL GROWTH</span></div></div>
      <div class="bkpl-muted">Realized P/L · {} graded parlays</div>
      <div class="bkpl-track"><div class="bkpl-fill" style="width:{:.1f}%"></div></div>
      <div class="bkpl-stats">
      <div class="bkpl-stat"><strong>${:,.2f}</strong><span>STARTING BALANCE</span></div>
      <div class="bkpl-stat"><strong>${:,.2f}</strong><span>CURRENT BALANCE</span></div>
      <div class="bkpl-stat"><strong>{}</strong><span>PARLAYS</span></div>
      <div class="bkpl-stat"><strong>{}</strong><span>WINS</span></div>
      <div class="bkpl-stat"><strong>{}</strong><span>LOSSES</span></div>
      <div class="bkpl-stat"><strong>{}</strong><span>PENDING</span></div></div></div>
      <div><div class="bkpl-muted">DAILY REALIZED P/L</div>
      <div class="bkpl-chart">{}</div></div></div></div>'''.format(
        total_label,(total/BANKROLL_CYCLE_STARTING_BALANCE*100) if BANKROLL_CYCLE_STARTING_BALANCE else 0,len(confirmed),100*len(confirmed)/len(frame) if len(frame) else 0,
        BANKROLL_CYCLE_STARTING_BALANCE,BANKROLL_CYCLE_STARTING_BALANCE+total,len(frame),won,lost,pending,"".join(bars))
    st.markdown(markup,unsafe_allow_html=True)
    with st.expander("Individual parlay results",expanded=False):
        st.dataframe(frame,hide_index=True,use_container_width=True)
    st.caption("Daily P/L follows the original Bankroll Builder list date. Green = profit; red = loss; gray = pending.")
