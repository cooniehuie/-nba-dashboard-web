"""Read-only verified NBA context. Unknown reports never imply availability."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.request import Request, urlopen
from collections import defaultdict
import json
import re
import unicodedata

BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
PACIFIC = ZoneInfo("America/Los_Angeles")
ALIASES = {"GS":"GSW","SA":"SAS","NY":"NYK","PHO":"PHX","NO":"NOP","BRK":"BKN"}
def team_key(s):
    v = str(s or "").strip().upper()
    return ALIASES.get(v, v)
def name_key(s):
    s = unicodedata.normalize("NFKD", str(s or "").casefold())
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())
def fetch_json(url):
    if not url.startswith(BASE + "/"):
        raise ValueError("Unapproved data host")
    with urlopen(Request(url, headers={"User-Agent":"Mozilla/5.0"}), timeout=10) as response:
        raw = response.read(4_000_001)
    if len(raw)>4_000_000: raise ValueError("Oversize ESPN payload")
    obj = json.loads(raw)
    if not isinstance(obj, dict): raise ValueError("Invalid API response")
    return obj
def parse_injuries(data):
    items=[]
    for group in data.get("injuries", []):
        if not isinstance(group, dict): continue
        team=team_key((group.get("team") or {}).get("abbreviation"))
        for item in group.get("injuries", []):
            if not isinstance(item,dict): continue
            person=item.get("athlete") or {}
            name=person.get("displayName") or person.get("fullName")
            if not name: continue
            status=item.get("status") or item.get("designation") or "Unspecified"
            if isinstance(status,dict): status=status.get("name") or status.get("description") or "Unspecified"
            items.append({"player":str(name),"key":name_key(name),"team":team,"status":str(status),"reported":item.get("date")})
    return items
def injury_status(player, team, report):
    """Output block, review, or unlisted; no injury entry is not clearance."""
    tokens=name_key(player).split()
    if not tokens: return ("review","Missing player")
    matches=[r for r in report if r["key"]==" ".join(tokens)]
    if not matches and len(tokens)>1:
        matches=[r for r in report if len(r["key"].split())>1
                 and r["key"].split()[0].startswith(tokens[0])
                 and r["key"].split()[1:]==tokens[1:]]
    if team:
        matches=[r for r in matches if not r["team"] or team_key(r["team"])==team_key(team)]
    if not matches: return ("unlisted","No ESPN injury entry (not medical clearance)")
    if len({(r["key"],r["team"]) for r in matches})>1:
        return ("review","Ambiguous player match")
    text=", ".join(sorted(set(r["status"] for r in matches)))
    value=text.casefold()
    if any(w in value for w in ("out","doubtful","inactive","suspended")): return ("block",text)
    return ("review",text)
def starter_match(player, team, named_starters):
    """Return True/False/None for uniquely matched confirmed lineup membership."""
    team=team_key(team)
    tokens=name_key(player).split()
    if len(tokens)<2 or not named_starters:return None
    known=[key.split() for abbr,key in named_starters if not team or team_key(abbr)==team]
    if not known:return None
    matches=[p for p in known if p==tokens or (p[0].startswith(tokens[0]) and p[1:]==tokens[1:])]
    if len(matches)==1:return True
    if len(matches)>1:return None
    # Without a known team, the absence of a matching starter proves nothing.
    if not team or len(known)<5:return None
    return False

def parse_game(label):
    m=re.search(r"\b([A-Za-z]{2,4})\s+(?:at|@|vs\.?|v)\s+([A-Za-z]{2,4})\b",str(label),re.I)
    return (team_key(m[1]),team_key(m[2])) if m else None
def scoreboard(data):
    games=[]
    for event in data.get("events",[]):
        comp=(event.get("competitions") or [{}])[0]
        sides={c.get("homeAway"):team_key((c.get("team") or {}).get("abbreviation")) for c in comp.get("competitors",[])}
        if sides.get("away") and sides.get("home"):
            games.append({"id":str(event.get("id","")),"away":sides["away"],"home":sides["home"],
                          "state":(event.get("status") or {}).get("type",{}).get("state","")})
    return games
def starters_from_summary(summary):
    result=set()
    for entry in (summary.get("boxscore") or {}).get("players",[]):
        team=team_key((entry.get("team") or {}).get("abbreviation"))
        for group in entry.get("statistics",[]):
            for p in group.get("athletes",[]):
                if p.get("starter") is True:
                    name=(p.get("athlete") or {}).get("displayName")
                    if name: result.add((team,name_key(name)))
    return result
def nba_live_json(url):
    """Fetch official NBA CDN live JSON; never treat failed requests as confirmations."""
    import re
    host="https://cdn.nba.com/static/json/liveData/"
    if not url.startswith(host) or not re.match(
            r"^https://cdn\.nba\.com/static/json/liveData/(scoreboard/todaysScoreboard_00\.json|boxscore/boxscore_\d{10}\.json)$",url):
        raise ValueError("Unapproved NBA live-data URL")
    with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=8) as response:
        raw=response.read(3_000_001)
    if len(raw)>3_000_000:raise ValueError("Oversize NBA response")
    obj=json.loads(raw)
    if not isinstance(obj,dict):raise ValueError("Invalid NBA live-data response")
    return obj

def nba_confirmed_starters(scoreboard_payload,game_date,fetch=None):
    """Only accept complete five-per-team named starter lists from official NBA boxscores."""
    fetch=fetch or nba_live_json
    confirmed={}
    for game in (scoreboard_payload.get("scoreboard") or {}).get("games",[]):
        game_id=str(game.get("gameId",""))
        if not (game_id.isdigit() and len(game_id)==10):continue
        try:
            instant=datetime.fromisoformat(str(game["gameTimeUTC"]).replace("Z","+00:00"))
            if instant.astimezone(PACIFIC).date()!=game_date:continue
        except (KeyError,ValueError,TypeError):continue
        away=team_key((game.get("awayTeam") or {}).get("teamTricode"))
        home=team_key((game.get("homeTeam") or {}).get("teamTricode"))
        if not away or not home:continue
        try:
            payload=fetch("https://cdn.nba.com/static/json/liveData/boxscore/boxscore_"+game_id+".json")
        except Exception:continue
        event=payload.get("game") or {}
        starters={}
        for side in ("awayTeam","homeTeam"):
            team=event.get(side) or {}
            abbr=team_key(team.get("teamTricode"))
            listed=[]
            for player in team.get("players",[]):
                marker=player.get("starter")
                if marker is True or str(marker).strip().lower() in ("1","true"):
                    name=player.get("name") or (str(player.get("firstName",""))+" "+str(player.get("familyName",""))).strip()
                    if name:listed.append((abbr,name_key(name)))
            if len(set(listed))==5:starters[abbr]=set(listed)
        # Partial provider output cannot be called a confirmed full lineup.
        if len(starters)==2 and all(len(v)==5 for v in starters.values()):
            confirmed[frozenset((away,home))]={
                "players":starters[away]|starters[home],
                "source":"NBA official live boxscore","game_id":game_id}
    return confirmed

def game_day_context(day=None, fetch=None):
    fetch=fetch or fetch_json
    day=day or datetime.now(PACIFIC).date()
    info={"checked_at":datetime.now(PACIFIC).isoformat(),"injuries":None,
          "injury_error":None,"games":[],"schedule_error":None,"starters":{},
          "official_starters":{}}
    try: info["injuries"]=parse_injuries(fetch(BASE+"/injuries"))
    except Exception as exc: info["injury_error"]=type(exc).__name__
    try: info["games"]=scoreboard(fetch(BASE+"/scoreboard?dates="+day.strftime("%Y%m%d")))
    except Exception as exc: info["schedule_error"]=type(exc).__name__
    try:
        source=nba_live_json("https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json")
        info["official_starters"]=nba_confirmed_starters(source,day)
    except Exception:
        # NBA official feed may be blocked or unavailable; keep statuses unconfirmed.
        pass
    for game in info["games"]:
        # A pregame roster is not a verified starting lineup.
        if game["state"] not in ("in","post") or not game["id"].isdigit(): continue
        try: info["starters"][game["id"]]=starters_from_summary(fetch(BASE+"/summary?event="+game["id"]))
        except Exception: continue
    return info
def _value(stat, *names, attempts=False):
    mapping={re.sub("[^a-z]","",str(s.get("name","")).lower()):str(s.get("displayValue",s.get("value",""))) for s in stat}
    for name in names:
        item=mapping.get(re.sub("[^a-z]","",name.lower()))
        if item:
            if attempts and "-" in item: item=item.split("-",1)[1]
            try: return float(item.replace(",",""))
            except (ValueError,TypeError): pass
    return None
def game_metrics(summary):
    rows=[]
    for item in (summary.get("boxscore") or {}).get("teams",[]):
        team=team_key((item.get("team") or {}).get("abbreviation"))
        stats=item.get("statistics") or []
        fga=_value(stats,"fieldGoalsMade-fieldGoalsAttempted",attempts=True)
        fta=_value(stats,"freeThrowsMade-freeThrowsAttempted",attempts=True)
        oreb=_value(stats,"offensiveRebounds")
        tov=_value(stats,"turnovers","totalTurnovers")
        pts=_value(stats,"points","totalPoints")
        if pts is None:
            try: pts=float(item.get("score"))
            except (ValueError,TypeError): pass
        if team and all(x is not None for x in (fga,fta,oreb,tov,pts)):
            poss=fga+.44*fta-oreb+tov
            if 60<=poss<=150: rows.append((team,poss,pts))
    if len(rows)!=2: return []
    pace=(rows[0][1]+rows[1][1])/2
    return [{"team":r[0],"pace":pace,"points_allowed_100":100*rows[1-i][2]/pace} for i,r in enumerate(rows)]
def team_context(opponents, day=None, fetch=None, days=21, max_per_team=7):
    """Request completed boxscores for relevant teams; returns observed subset, not league averages."""
    targets={team_key(t) for t in opponents if t}
    if not targets: return {"rows":[],"failures":0}
    fetch=fetch or fetch_json
    day=day or datetime.now(PACIFIC).date()
    games=[]; failures=0
    for offset in range(1,days+1):
        try: games+=scoreboard(fetch(BASE+"/scoreboard?dates="+(day-timedelta(days=offset)).strftime("%Y%m%d")))
        except Exception: failures+=1
    count=defaultdict(int); selected=[]
    for game in reversed(games):
        relevant=targets.intersection({game["home"],game["away"]})
        if game["state"]!="post" or not game["id"].isdigit(): continue
        if relevant and any(count[t]<max_per_team for t in relevant):
            selected.append(game)
            for t in relevant: count[t]+=1
    rows=[]
    for game in selected:
        try: rows+=game_metrics(fetch(BASE+"/summary?event="+game["id"]))
        except Exception: failures+=1
    return {"rows":rows,"failures":failures,"date":day.isoformat()}
def matchup_adjustment(rows, opponent, market, min_games=5):
    all_rows=[r for r in rows if r.get("pace") and r.get("points_allowed_100")]
    theirs=[r for r in all_rows if team_key(r.get("team"))==team_key(opponent)]
    if len(theirs)<min_games or len(all_rows)<2*min_games: return None
    avg=lambda arr,k:sum(r[k] for r in arr)/len(arr)
    rp=avg(all_rows,"pace"); rd=avg(all_rows,"points_allowed_100")
    if rp<=0 or rd<=0: return None
    p=avg(theirs,"pace"); d=avg(theirs,"points_allowed_100")
    p_factor=max(.96,min(1.04,1+.25*(p/rp-1)))
    d_factor=max(.96,min(1.04,1+.25*(d/rd-1)))
    # Defensive point suppression is not justified for rebound/assist/three markets.
    factor=p_factor*d_factor if market=="Points" else p_factor
    return {"factor":factor,"pace":round(p,1),"allowed_100":round(d,1),
            "games":len(theirs),"source":"ESPN final team boxscores, observed opponent subset"}
