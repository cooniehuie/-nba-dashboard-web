"""Huie NFL projections, independent from NBA/Sam and wager settlement data.

ESPN Site v2 schedules/rosters + Web API v3 completed NFL player game logs.
No invented reference lines, no fabricated injured-player availability.
"""
import json
import math
import re
import statistics
import urllib.request
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from huie_nfl_matchups import apply_context,league_defensive_snapshot,validate_usage_model

SITE="https://site.api.espn.com/apis/site/v2/sports/football/nfl/"
WEB="https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/"
MARKETS=("Anytime TD","Passing yards","Receiving yards","Rushing yards","Receptions")
OFFENSE=("QB","RB","WR","TE")
PT=ZoneInfo("America/Los_Angeles")


def _fetch(url):
    if not (url.startswith(SITE) or url.startswith(WEB)):
        raise ValueError("Unsupported NFL source")
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (HuiesDegenCenter/1.0)",
                                             "Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=12) as response:
        data=json.load(response)
    if not isinstance(data,dict):
        raise ValueError("Unexpected ESPN response")
    return data


@st.cache_data(ttl=300,show_spinner=False)
def _current_week(date_key):
    obj=_fetch(SITE+"scoreboard?dates="+date_key)
    week=obj.get("week",{})
    return int(week.get("number") or 1)


def _schedule_events(data):
    events=[]
    for event in data.get("events") or []:
        comps=(event.get("competitions") or [{}])[0].get("competitors") or []
        teams=[]
        for c in comps:
            team=c.get("team") or {}
            ident=str(team.get("id") or "")
            if ident:
                teams.append({"id":ident,"abbr":str(team.get("abbreviation") or ""),
                              "name":str(team.get("displayName") or ""),
                              "homeAway":c.get("homeAway")})
        if len(teams)!=2 or not str(event.get("id") or "").isdigit():
            continue
        events.append({"id":str(event.get("id") or ""),"game":str(event.get("shortName") or event.get("name") or ""),
                       "date":str(event.get("date") or ""),"state":(event.get("status") or {}).get("type",{}).get("state",""),
                       "week":(event.get("week") or data.get("week") or {}).get("number"),
                       "season":(event.get("season") or data.get("season") or {}).get("year"),
                       "teams":teams})
    events.sort(key=lambda e:e["date"])
    return events



@st.cache_data(ttl=30,show_spinner=False)
def _scoreboard_day(day):
    return _fetch(SITE+f"scoreboard?dates={day:%Y%m%d}")


def _schedule_day(day):
    # ESPN can bucket events differently from the Pacific display date.
    # The week feed is the fallback and the kickoff is the source of truth.
    data=_scoreboard_day(day)
    events=_schedule_events(data)
    if not events or any(_kickoff(g) and _kickoff(g).astimezone(PT).date()!=day for g in events):
        week=(data.get("week") or {}).get("number")
        season=day.year if day.month>=8 else day.year-1
        if week:
            try:
                events.extend(_schedule(season,int(week)))
            except Exception:
                if not events:
                    raise
    by_id={g["id"]:g for g in reversed(events)
           if _kickoff(g) and _kickoff(g).astimezone(PT).date()==day}
    return sorted(by_id.values(),key=lambda game:game["date"])


@st.cache_data(ttl=900,show_spinner=False)
def _schedule(season,week):
    return _schedule_events(_fetch(
        SITE+f"scoreboard?dates={season}&seasontype=2&week={week}&limit=50"))


def _kickoff(game):
    try:
        stamp=datetime.fromisoformat(game["date"].replace("Z","+00:00"))
        return stamp if stamp.tzinfo else None
    except (ValueError, TypeError, KeyError):
        return None


@st.cache_data(ttl=14400,show_spinner=False)
def _roster(team_id,season):
    data=_fetch(SITE+"teams/"+str(team_id)+"/roster?season="+str(season))
    players=[]
    for group in data.get("athletes") or []:
        members=group.get("items",[]) if isinstance(group,dict) and "items" in group else [group]
        for p in members:
            if not isinstance(p,dict):continue
            role=(p.get("position") or {}).get("abbreviation","").upper()
            if role not in OFFENSE:continue
            ident=str(p.get("id") or "")
            name=str(p.get("displayName") or p.get("fullName") or "")
            if not ident.isdigit() or not name:continue
            status=p.get("status") or {}
            status_text=str(status.get("name") or status.get("type") or "") if isinstance(status,dict) else str(status)
            injuries=p.get("injuries") or []
            injury_labels=[str((x.get("status") or x.get("designation") or "")) for x in injuries if isinstance(x,dict)]
            report=(" / ".join(injury_labels) if injury_labels else status_text)
            players.append({"id":ident,"name":name,"position":role,
                            "report":report,"team_id":str(team_id)})
    return players


def _num(value):
    try:
        if isinstance(value,bool):return None
        v=str(value).strip().replace(",","")
        if not re.fullmatch(r"-?\d+(?:\.\d+)?",v):
            return None
        result=float(v)
        return result if math.isfinite(result) else None
    except (TypeError,ValueError):
        return None


def _event_value(root,event,cutoff_iso):
    # Do not include the game currently being projected or later games.
    info=(root.get("events") or {}).get(str(event.get("eventId") or "")) or {}
    when=str(info.get("gameDate") or info.get("date") or "")
    try:
        stamp=datetime.fromisoformat(when.replace("Z","+00:00"))
        cutoff=datetime.fromisoformat(cutoff_iso.replace("Z","+00:00"))
        if stamp>=cutoff:return None
    except (ValueError,TypeError):
        return None
    return info,stamp


def parse_gamelog(raw,cutoff_iso):
    """Parse ESPN's full parallel label/stats arrays, keeping stat categories distinct.

    ESPN reports labels like YDS and TD more than once. Their positional category
    offsets distinguish passing from rushing from receiving, so never search
    for the first occurrence of YDS or TD globally.
    """
    labels=[str(x).upper().strip() for x in (raw.get("labels") or [])]
    categories=raw.get("categories") or []
    spans={}
    offset=0
    for cat in categories:
        name=str(cat.get("name") or "").lower()
        count=int(cat.get("count") or 0)
        if count>0:
            spans[name]=(offset,offset+count)
            offset+=count
    seen=set()
    records=[]
    for phase in raw.get("seasonTypes") or []:
        # Exclude playoff/preseason from regular-season model; no guessing
        # when a season phase's name is unavailable.
        if "regular" not in str(phase.get("displayName") or "").lower():
            continue
        for category in phase.get("categories") or []:
            for record in category.get("events") or []:
                eid=str(record.get("eventId") or "")
                if not eid or eid in seen:continue
                resolved=_event_value(raw,record,cutoff_iso)
                if not resolved:continue
                info,stamp=resolved
                values=record.get("stats") or []
                if len(values)!=len(labels) or len(labels)<4:
                    continue  # Do not guess a partial stat-vector layout.
                metrics={}
                for market,catname,label in (
                    ("Passing yards","passing","YDS"),
                    ("Rushing yards","rushing","YDS"),
                    ("Receiving yards","receiving","YDS"),
                    ("Receptions","receiving","REC"),
                    ("Pass attempts","passing","ATT"),
                    ("Rush attempts","rushing","CAR"),
                    ("Targets","receiving","TGTS"),
                ):
                    span=spans.get(catname)
                    if not span:continue
                    found=[i for i in range(*span) if i<len(labels) and labels[i]==label]
                    if len(found)==1:
                        metrics[market]=_num(values[found[0]])
                td_values=[]
                for catname in ("rushing","receiving"):
                    span=spans.get(catname)
                    if not span:continue
                    found=[i for i in range(*span) if i<len(labels) and labels[i]=="TD"]
                    if len(found)==1:
                        td_values.append(_num(values[found[0]]))
                if td_values and all(v is not None for v in td_values):
                    metrics["Anytime TD"]=sum(td_values)
                records.append({"event_id":eid,"date":stamp.isoformat(),
                                "opponent":str((info.get("opponent") or {}).get("abbreviation") or ""),
                                "stats":metrics})
                seen.add(eid)
    return sorted(records,key=lambda x:x["date"])


@st.cache_data(ttl=14400,show_spinner=False)
def _gamelog(athlete_id,season,cutoff_iso):
    if not str(athlete_id).isdigit():
        return []
    obj=_fetch(WEB+"athletes/"+str(athlete_id)+"/gamelog?season="+str(season))
    return parse_gamelog(obj,cutoff_iso)


def _forecast(games,market):
    # Missing stats stay missing, not zero. Require at least three actual games.
    values=[float(g["stats"][market]) for g in games if g.get("stats",{}).get(market) is not None]
    n=len(values)
    if n<3:return None
    rec=values[-3:]
    recency=0.55*rec[-1]+0.30*rec[-2]+0.15*rec[-3]
    season_mean=statistics.mean(values)
    # Shrink recent form to the full season; stronger shrink for small samples.
    weight=0.65 if n>=6 else 0.4
    estimate=weight*recency+(1-weight)*season_mean
    # Rates/counts cannot meaningfully be negative even if an occasional
    # player posts a negative rushing-yard total in a single game.
    estimate=max(0.0,estimate)
    return {"projection":round(estimate,2),"games":n,
            "last_three":list(reversed(rec)),
            "season_avg":round(season_mean,2),
            "hit_one":sum(x>=1 for x in values),
            "confidence":"Higher sample" if n>=8 else "Moderate sample" if n>=5 else "Small sample",
            "method":"65% recency / 35% season" if n>=6 else "40% recency / 60% season"}


def _available_markets(position):
    if position=="QB":return ("Passing yards","Rushing yards","Anytime TD")
    if position=="RB":return ("Rushing yards","Receiving yards","Receptions","Anytime TD")
    return ("Receiving yards","Receptions","Anytime TD")


def _baseline_rows(player,logs,game,team,opponent,opponent_id,defense_snapshot=None,
                   usage_markets=None,markets=None):
    rows=[]
    for market in (markets if markets is not None else _available_markets(player["position"])):
        estimate=_forecast(logs,market)
        if estimate is None:continue
        # Historical games are strictly before matchup kickoff (_gamelog).
        # The season-to-date defensive snapshot is used only for upcoming games.
        context=apply_context(estimate["projection"],logs,market,player["position"],
                              defense_snapshot,opponent_id)
        workload=context["usage"]
        defense=context["defense"]
        usage_active=(market in (usage_markets or set()) and
                      workload.get("notes")=="Verified workload × season efficiency")
        final=context["final"] if usage_active else round(
            estimate["projection"]*defense["factor"],2)
        rows.append({"Game":game,"Team":team,"Opponent":opponent,
                     "Player":player["name"],"Position":player["position"],
                     "Market":market,"Huie projection":final,
                     "Baseline":estimate["projection"],
                     "Workload projection":workload["estimate"],
                     "Expected volume":workload["volume"],
                     "Volume trend %":workload["trend"],
                     "Def. adjustment %":round((defense["factor"]-1)*100,1),
                     "Opp allowed/game":defense["defense_allowed"],
                     "League allowed/game":defense["league_allowed"],
                     "Matchup":defense["label"],"Def. games":defense["sample"],
                     "TD chance %":context["td_probability"],
                     "Reference line":None,"Model side":"—",
                     "Last game":estimate["last_three"][0],"2 games ago":estimate["last_three"][1],
                     "3 games ago":estimate["last_three"][2],
                     "Season avg":estimate["season_avg"],"Games":estimate["games"],
                     "1+ TD games":(f'{estimate["hit_one"]}/{estimate["games"]}' if market=="Anytime TD" else "—"),
                     "Sample":estimate["confidence"],"Status":"Availability not verified",
                     "Player ID":player["id"],
                     "Projection method":(("Verified workload" if usage_active else estimate["method"])+
                                           (" + opponent defense" if defense["label"]!="Unavailable" else "")),
                     "Matchup context":defense["label"],
                     "Method":(("Verified workload + " if usage_active else "Player baseline + ")+
                               ("experimental opponent defense" if defense["label"]!="Unavailable"
                                else "no verified defensive adjustment"))})
    return rows

def _default_players(roster,qb1_id=None):
    grouped={pos:[p for p in roster if p["position"]==pos] for pos in OFFENSE}
    # Roster list still includes all QBs for manual selection. Prefer ESPN QB1.
    qbs=grouped["QB"]
    preferred=[p for p in qbs if p["id"]==qb1_id]
    if preferred:
        qb_defaults=preferred[:1]
    else:
        # Include two QBs on a missing depth chart; avoid alphabetically
        # selecting only an unrelated QB3 over the real starter.
        qb_defaults=qbs[:2]
    other=[p["id"] for pos,limit in [("RB",2),("WR",3),("TE",2)]
           for p in grouped[pos][:limit]]
    return [p["id"] for p in qb_defaults]+other


def _parse_stored_lines(data):
    if data is None:return {}
    try:
        rows=json.loads(data.decode("utf-8") if isinstance(data,bytes) else data)
        if not isinstance(rows,list):return {}
        return {(str(r["player_id"]),str(r["market"])):float(r["line"])
                for r in rows if isinstance(r,dict) and
                r.get("market") in MARKETS and _num(r.get("line")) is not None}
    except (ValueError,TypeError,KeyError,AttributeError):
        return {}


ALIASES={"WAS":"WSH","JAC":"JAX","LA":"LAR","STL":"LAR","SD":"LAC","OAK":"LV",
         "TAM":"TB","KAN":"KC","NWE":"NE","GNB":"GB","NOR":"NO","SFO":"SF"}
SUFFIXES={"jr","sr","ii","iii","iv"}
ARCHIVE="nfl_models/sam_nfl_archive.json"


def _team(code):
    code=str(code or "").strip().upper()
    return ALIASES.get(code,code)


def _name_parts(value):
    value=unicodedata.normalize("NFKD",str(value or "").lower())
    value="".join(c for c in value if not unicodedata.combining(c))
    value=re.sub(r"\b([a-z])\.\s*([a-z])\.",r"\1\2",value)
    return tuple(re.findall(r"[a-z0-9]+",value.replace("'","").replace("’","")))


def _player_match(name,players,allow_initial=True):
    """Accept only a unique name match within one matchup and known team."""
    parts=_name_parts(name)
    if len(parts)<2:
        return None
    exact=[p for p in players if _name_parts(p["name"])==parts]
    if exact:
        return exact[0] if len(exact)==1 else None
    def core(parts):
        return parts[:-1] if parts and parts[-1] in SUFFIXES else parts
    query=core(parts)
    matches=[]
    for p in players:
        full=_name_parts(p["name"])
        base=core(full)
        if parts[-1] in SUFFIXES and full[-1:]!=parts[-1:]:
            continue
        if base==query or (allow_initial and len(query)>1 and len(base)>1 and
                           len(query[0])==1 and base[0].startswith(query[0]) and
                           query[1:]==base[1:]):
            matches.append(p)
    return matches[0] if len(matches)==1 else None


def _read_archive(storage_read):
    if storage_read is None:
        return {}
    raw=storage_read(ARCHIVE)
    if not raw:
        return {}
    archive=json.loads(raw)
    games=archive.get("games")
    if not isinstance(games,dict):
        raise ValueError("Invalid Sam NFL archive")
    return games


def _sam_for_game(archive,game):
    when=_kickoff(game)
    if not when:
        return None
    day=when.astimezone(PT).date().isoformat()
    sides={_team(t["abbr"]) for t in game["teams"]}
    matches=[]
    for key,record in archive.items():
        if not isinstance(record,dict):
            continue
        recorded=record.get("date") or key.split("|",1)[0]
        match=re.fullmatch(r"([A-Z]{2,3})\s*@\s*([A-Z]{2,3})",str(record.get("matchup","")).strip().upper())
        if not match or {_team(t) for t in match.groups()}!=sides:
            continue
        # Compatibility with the original Nov 12 WAS-NYG save.
        legacy=(day=="2026-11-12" and recorded=="2026-11-13" and sides=={"WSH","NYG"})
        if recorded==day or legacy:
            matches.append((recorded==day,str(record.get("uploaded_at","")),record))
    return max(matches,key=lambda item:item[:2])[2] if matches else None


def _sam_rows(record,roster,game):
    """Keep all dated Sam reference lines, even for unmatched players."""
    sides={_team(t["abbr"]) for t in game["teams"]}
    rows={}
    conflicts=set()
    for r in (record or {}).get("rows",[]):
        if not isinstance(r,dict):
            continue
        market=r.get("Market")
        line=_num(r.get("Reference line"))
        name=str(r.get("Player") or "").strip()
        if market not in MARKETS or not name:
            continue
        team=_team(r.get("Team"))
        eligible=[p for p in roster if _team(p["team"])==team] if team in sides else (
                 roster if not team else [])
        athlete=_player_match(name,eligible)
        key=(athlete["id"] if athlete else (_name_parts(name),team),market)
        candidate={"Player":athlete["name"] if athlete else name,"Market":market,
                   "Team":athlete["team"] if athlete else team,
                   "Player ID":athlete["id"] if athlete else "",
                   "Reference line":line,"Sam projection":_num(r.get("Sam projection"))}
        if key in rows and (rows[key]["Reference line"],rows[key]["Sam projection"])!=(line,candidate["Sam projection"]):
            conflicts.add(key)
        rows[key]=candidate
    for key in conflicts:
        # Conflicting snapshots within one file are not gradeable.
        rows[key].update({"Reference line":None,"Sam projection":None})
    return list(rows.values())


@st.cache_data(ttl=14400,show_spinner=False)
def _depth_players(team_id):
    raw=_fetch(SITE+f"teams/{team_id}/depthcharts")
    charts=raw.get("depthchart") or raw.get("depthCharts") or []
    positions=(charts[0].get("positions") or {}) if charts else {}
    ids=[]
    for key,position in positions.items():
        if str(key).lower() not in ("qb","rb","fb","wr","lwr","rwr","swr","wr1","wr2","wr3","te"):
            continue
        limit=1 if str(key).lower()=="qb" else 2
        for item in (position.get("athletes") or [])[:limit]:
            info=item.get("athlete") or item
            pid=str(info.get("id") or "")
            if pid.isdigit():
                ids.append(pid)
    return list(dict.fromkeys(ids))


def _season_for(game):
    kickoff=_kickoff(game).astimezone(PT)
    return int(game.get("season") or (kickoff.year if kickoff.month>=8 else kickoff.year-1))


def _reference_week(game):
    try:
        week=int(game.get("week") or 0)
        return week if 1<=week<=18 else None
    except (TypeError,ValueError):
        return None


def _game_rosters(game):
    errors=0
    players=[]
    picks=[]
    for team in game["teams"]:
        try:
            roster=[{**p,"team":team["abbr"]} for p in _roster(team["id"],_season_for(game))]
        except Exception:
            roster=[]
            errors+=1
        players.extend(roster)
        if roster:
            try:
                depth=set(_depth_players(team["id"]))
            except Exception:
                depth=set()
            ordered=[p for p in roster if p["id"] in depth]+[p for p in roster if p["id"] not in depth]
            qb1=next((p["id"] for p in ordered if p["position"]=="QB" and p["id"] in depth),None)
            picks.extend(_default_players(ordered,qb1))
    return players,picks,errors


def _is_upcoming(game):
    stamp=_kickoff(game)
    return bool(stamp and game.get("state")=="pre" and stamp>datetime.now(timezone.utc))


def _build_projections(games,archive,lines,include_unlined=False,use_defense=False):
    """Build NBA-style dated prop rows without changing how Huie forecasts are generated."""
    snapshots={g["id"]:_sam_for_game(archive,g) for g in games}
    rosters={}
    issues=0
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs={pool.submit(_game_rosters,g):g["id"] for g in games}
        for future in as_completed(jobs):
            gid=jobs[future]
            players,defaults,errors=future.result()
            rosters[gid]=(players,defaults)
            issues+=errors
    props={}
    jobs={}
    coverage=0
    for game in games:
        gid=game["id"]
        roster,defaults=rosters[gid]
        refs=_sam_rows(snapshots[gid],roster,game)
        saved=lines.get((_season_for(game),_reference_week(game)),{})
        eligible={p["id"]:p for p in roster}
        keyed={(r["Player ID"],r["Market"]):r for r in refs if r["Player ID"]}
        for (pid,market),line in saved.items():
            if pid not in eligible:
                continue
            player=eligible[pid]
            if (pid,market) not in keyed:
                row={"Player":player["name"],"Team":player["team"],"Player ID":pid,
                     "Market":market,"Sam projection":None}
                refs.append(row)
                keyed[pid,market]=row
            keyed[pid,market]["Reference line"]=line
        if any(_num(r.get("Reference line")) is not None for r in refs):
            coverage+=1
        if include_unlined or not refs:
            for pid in defaults:
                for market in _available_markets(eligible[pid]["position"]):
                    if (pid,market) not in keyed:
                        row={"Player":eligible[pid]["name"],"Team":eligible[pid]["team"],
                             "Player ID":pid,"Market":market,"Reference line":None,"Sam projection":None}
                        refs.append(row)
                        keyed[pid,market]=row
        props[gid]=refs
        for pid in dict.fromkeys(defaults+[r["Player ID"] for r in refs if r["Player ID"]]):
            jobs[(gid,pid)]=(game,eligible[pid])
    logs={}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures={pool.submit(_gamelog,p["id"],_season_for(g),g["date"]):key
                 for key,(g,p) in jobs.items()}
        for future in as_completed(futures):
            try:
                logs[futures[future]]=future.result()
            except Exception:
                issues+=1
    snapshot={}
    if use_defense:
        for season in {_season_for(g) for g in games if _is_upcoming(g)}:
            try:
                context=league_defensive_snapshot(season)
                if context.get("coverage",0)>=24:
                    snapshot[season]=context
                else:
                    issues+=1
            except Exception:
                issues+=1
    # Fixed per-matchup validation population means switching All games vs a
    # single matchup does not change projections for that matchup.
    audits={}
    forecasts={}
    for game in games:
        gid=game["id"]
        game_logs={pid:records for (event,pid),records in logs.items() if event==gid}
        permitted={pid:tuple(dict.fromkeys(r["Market"] for r in props[gid] if r["Player ID"]==pid))
                   for pid in game_logs}
        # Neither Sam's player selection nor Sam's lines determine the model.
        # Use a fixed ESPN cohort and standard positional markets for validation.
        cohort={pid:game_logs[pid] for pid in rosters[gid][1] if pid in game_logs}
        standard={pid:_available_markets(jobs[gid,pid][1]["position"]) for pid in cohort}
        validation=validate_usage_model(cohort,_forecast,standard)
        audits[gid]=validation
        active={market for market,v in validation.items() if v.get("validated") and v.get("use_usage")}
        defense=snapshot.get(_season_for(game)) if _is_upcoming(game) else None
        for pid,records in game_logs.items():
            if not permitted[pid]:
                continue
            player=jobs[gid,pid][1]
            other=next(t for t in game["teams"] if t["abbr"]!=player["team"])
            for row in _baseline_rows(player,records,game["game"],player["team"],other["abbr"],other["id"],
                                      defense,active,markets=permitted[pid]):
                row["Predictive validation"]=("Workload validated" if row["Projection method"].startswith("Verified workload")
                                              else "Historical fallback")
                forecasts[gid,pid,row["Market"]]=row
    assembled=[]
    for game in games:
        for prop in props[game["id"]]:
            identified=bool(prop["Player ID"])
            model=forecasts.get((game["id"],prop["Player ID"],prop["Market"]),{})
            assembled.append({**model,**prop,"Game":game["game"],"Game ID":game["id"],
                              "Huie projection":model.get("Huie projection"),
                              "Projection method":model.get("Projection method","Insufficient verified player history"
                                                           if identified else "Player identity unverified")})
    frame=pd.DataFrame(assembled)
    if not frame.empty:
        frame=_side_metrics(frame)
    return frame,audits,issues,coverage


def _side_metrics(frame):
    ref=pd.to_numeric(frame["Reference line"],errors="coerce")
    huie=pd.to_numeric(frame["Huie projection"],errors="coerce")
    sam=pd.to_numeric(frame["Sam projection"],errors="coerce")
    frame["Huie edge"]=(huie-ref).round(2)
    frame["Sam edge"]=(sam-ref).round(2)
    frame["Huie side"]=["⚪ UNVERIFIED" if pd.isna(h) or pd.isna(r) else
                        "🟢 OVER" if h>r else "🔴 UNDER" if h<r else "⚪ AT LINE"
                        for h,r in zip(huie,ref)]
    frame["Both models OVER"]=["Unverified" if pd.isna(h) or pd.isna(s) or pd.isna(r) else
                               "Yes" if h>r and s>r else "No" for h,s,r in zip(huie,sam,ref)]
    def recent_hits(row):
        line=_num(row.get("Reference line"))
        values=[_num(row.get(k)) for k in ("Last game","2 games ago","3 games ago")]
        values=[v for v in values if v is not None]
        side=row["Huie side"]
        if line is None or not values or side not in ("🟢 OVER","🔴 UNDER"):
            return "—"
        hits=sum(v>line for v in values) if side=="🟢 OVER" else sum(v<line for v in values)
        return f"{hits}/{len(values)}"
    frame["Recent hits"]=frame.apply(recent_hits,axis=1)
    return frame


@st.cache_data(ttl=30,show_spinner=False)
def _event_box(game_id):
    """Get exact game participation and stats with ESPN athlete/team IDs."""
    from my_bets_absences import game_reported_absences

    summary=_fetch(SITE+f"summary?event={game_id}")
    header=summary.get("header") or {}
    competition=(header.get("competitions") or [{}])[0]
    confirmed=str(header.get("id") or competition.get("id") or "")
    if confirmed!=str(game_id):
        raise ValueError("Wrong ESPN game in box score")
    status=(competition.get("status") or {}).get("type") or {}
    result={"id":game_id,"state":status.get("state"),"players":[],"absences":[],
            "available":False}
    if status.get("state")!="post" or not status.get("completed"):
        return result
    players={}
    box=(summary.get("boxscore") or {}).get("players") or []
    offense_teams=set()
    for group in box:
        info=group.get("team") or {}
        team=_team(info.get("abbreviation"))
        tid=str(info.get("id") or "")
        if not team or not tid:
            continue
        for category in group.get("statistics") or []:
            kind=str(category.get("name","")).lower()
            labels=[str(label).upper() for label in category.get("labels") or []]
            observed={"passing":(("Passing yards","YDS"),),
                      "rushing":(("Rushing yards","YDS"),("_rush_td","TD")),
                      "receiving":(("Receiving yards","YDS"),("Receptions","REC"),("_rec_td","TD"))}
            if kind in observed and category.get("athletes"):
                offense_teams.add(tid)
            for row in category.get("athletes") or []:
                person=row.get("athlete") or {}
                pid=str(person.get("id") or "")
                name=person.get("displayName") or person.get("fullName")
                if not pid.isdigit() or not name:
                    continue
                pos=person.get("position") or {}
                position=pos.get("abbreviation") if isinstance(pos,dict) else ""
                athlete=players.setdefault(pid,{"id":pid,"name":name,"team":team,"team_id":tid,
                                                "position":position or "","stats":{}})
                values=row.get("stats") or []
                for stat,label in observed.get(kind,()):
                    if labels.count(label)==1 and labels.index(label)<len(values):
                        num=_num(values[labels.index(label)])
                        if num is not None:
                            athlete["stats"][stat]=num
    for p in players.values():
        td=[p["stats"].get(key) for key in ("_rush_td","_rec_td")]
        if any(v is not None for v in td):
            p["stats"]["Anytime TD"]=sum(v for v in td if v is not None)
    result["available"]=len(offense_teams)==2
    result["players"]=list(players.values())
    result["absences"]=game_reported_absences(summary,{"id":game_id,"state":"post"},"NFL")
    return result


def _grade_projections(frame,boxes):
    outcomes=[]
    for row in frame.to_dict("records"):
        side={"🟢 OVER":"OVER","🔴 UNDER":"UNDER","⚪ AT LINE":"At line"}.get(row["Huie side"],"Unverified")
        box=boxes.get(row["Game ID"],{})
        actual=None
        reference=_num(row["Reference line"])
        if side=="At line":
            outcome="No side"
        elif side=="Unverified":
            outcome="No reference line" if reference is None else "Unverified projection"
        elif box.get("error"):
            outcome="Box score unavailable"
        elif box.get("state")!="post":
            outcome="Pending game"
        elif not box.get("available"):
            outcome="Box score unavailable"
        else:
            team=_team(row.get("Team"))
            players=[p for p in box["players"] if not team or p["team"]==team]
            player=next((p for p in players if p["id"]==row["Player ID"]),None)
            if player is None and not row["Player ID"]:
                player=_player_match(row["Player"],players,allow_initial=False)
            if player is None:
                # Missing players do not become a zero or DNP. Require a
                # specifically reported absence for this same game and team.
                absences=[r for r in box["absences"] if not team or _team(r.get("team"))==team]
                outcome=("DNP" if _player_match(row["Player"],absences,allow_initial=False)
                         else "Unmatched")
            else:
                actual=_num(player["stats"].get(row["Market"]))
                if actual is None:
                    outcome="Unverified stat"
                elif actual==reference:
                    outcome="Push"
                elif (side=="OVER" and actual>reference) or (side=="UNDER" and actual<reference):
                    outcome="Hit"
                else:
                    outcome="Miss"
        outcomes.append({"Player":row["Player"],"Game":row["Game"],"Market":row["Market"],
                         "Side":side,"Reference line":reference,
                         "Huie projection":row["Huie projection"],"Actual":actual,"Result":outcome})
    return pd.DataFrame(outcomes)


def _render_results(frame,games,period,date_label,coverage):
    from huie_daily_performance import render_graded_summary

    graded_frame=frame[frame["Reference line"].notna()].copy()

    @st.fragment(run_every="30s" if any(g["state"]!="post" for g in games) else None)
    def summary():
        st.subheader(f"📊 Huie Projections {period} Hit Summary")
        live_note=" · Auto-refreshes every 30 seconds while open" if any(g["state"]!="post" for g in games) else ""
        st.caption(f"{date_label} · Final NFL box scores only{live_note} · Scope follows the selected matchup, not the filters below.")
        if graded_frame.empty:
            st.info("No verified reference lines to grade for this selection.")
            return
        if st.button("↻ Refresh box scores",key="huie_nfl_grade_refresh"):
            _event_box.clear()
            st.rerun(scope="fragment")

        # Do not request a preview box score for a matchup before kickoff.
        # After kickoff, ESPN's event status is rechecked for live-to-final grading.
        targets=set(graded_frame["Game ID"])
        relevant=[g for g in games if g["id"] in targets and not _is_upcoming(g)]
        boxes={}
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures={pool.submit(_event_box,g["id"]):g["id"] for g in relevant}
            for future in as_completed(futures):
                try:
                    boxes[futures[future]]=future.result()
                except Exception:
                    boxes[futures[future]]={"error":True}
        graded=_grade_projections(graded_frame,boxes)
        render_graded_summary(graded,MARKETS,f"Games with verified reference lines: {coverage}/{len(games)}",
                              "huie_nfl_grade",f"huie_nfl_results_{date_label.replace(' ','_')}.csv",
                              breakdown_label=f"{period} breakdown by stat")
    summary()


def _table(frame,key):
    wanted=["Player","Market","Reference line","Huie projection","Huie edge","Huie side",
            "Both models OVER","Sam projection","Sam edge","Last game","2 games ago","3 games ago",
            "Recent hits","Expected volume","Volume trend %","Projection method",
            "Predictive validation","Matchup context","Games","TD chance %","Team"]
    values=frame.sort_values("Huie edge",ascending=False,na_position="last")[
        [col for col in wanted if col in frame]].copy()
    numbers=("Reference line","Huie projection","Huie edge","Sam projection","Sam edge",
             "Last game","2 games ago","3 games ago","Expected volume","Volume trend %","TD chance %")
    for col in numbers:
        if col in values:
            values[col]=pd.to_numeric(values[col],errors="coerce").round(1)
    st.dataframe(values,hide_index=True,use_container_width=True,key=key,
                 column_config={"Player":st.column_config.TextColumn("Player",width="medium"),
                                "Market":st.column_config.TextColumn("Market",width="small"),
                                **{col:st.column_config.NumberColumn(col,format="%+.1f" if col.endswith("edge") else "%.1f")
                                   for col in numbers}})


def _edit_lines(frame,game,storage_read,storage_write):
    week=_reference_week(game)
    if week is None or storage_write is None or storage_read is None:
        return
    path=f"nfl_reference_lines_{_season_for(game)}_week_{week}.json"
    with st.expander("Admin · NFL reference lines"):
        st.caption("Enter actual reference thresholds only. Leave an override blank to use the archived Sam line.")
        try:
            previous=_parse_stored_lines(storage_read(path))
        except Exception:
            st.error("Saved reference lines could not be read. No edits were made.")
            return
        edited_rows=frame[frame["Player ID"].ne("")].drop_duplicates(["Player ID","Market"]).copy()
        if edited_rows.empty:
            st.info("No verified player identities available to edit.")
            return
        keys=list(zip(edited_rows["Player ID"],edited_rows["Market"]))
        edited_rows["Manual override"]=pd.to_numeric([previous.get(k) for k in keys],errors="coerce")
        cols=["Player","Market","Reference line","Manual override"]
        with st.form("huie_nfl_edit_lines_"+game["id"]):
            edited=st.data_editor(edited_rows[cols].reset_index(drop=True),hide_index=True,
                                  use_container_width=True,disabled=cols[:-1],
                                  column_config={"Manual override":st.column_config.NumberColumn(
                                      "Manual override",min_value=0.0,step=0.5,format="%.1f")})
            submitted=st.form_submit_button("💾 Save NFL reference lines")
        if submitted:
            try:
                # Re-read and only update keys the editor owns.
                lines=_parse_stored_lines(storage_read(path))
                for key,original,val in zip(keys,[previous.get(k) for k in keys],edited["Manual override"]):
                    val=_num(val)
                    if val==original:
                        continue
                    if val is None:
                        lines.pop(key,None)
                    else:
                        lines[key]=val
                payload=[{"player_id":pid,"market":market,"line":val}
                         for (pid,market),val in sorted(lines.items())]
                storage_write(path,json.dumps(payload,indent=2).encode("utf-8"))
            except Exception as exc:
                st.error(f"Could not save reference lines ({type(exc).__name__}).")
                return
            st.session_state["huie_nfl_lines_saved"]=True
            st.rerun()


def render(storage_read=None,storage_write=None,is_admin=False):
    st.title("🏈 Huie NFL Projections · Individual Games")
    st.caption("All player props · Huie's independently calculated NFL projections vs the Reference line. Public read-only. Sam's projections are displayed for comparison only, not used to calculate Huie's.")
    today=datetime.now(PT).date()
    season=today.year if today.month>=8 else today.year-1
    c1,c2=st.columns(2)
    if c1.button("📅 View yesterday's completed games",key="huie_nfl_yesterday"):
        st.session_state["huie_nfl_scope"]="Game date"
        st.session_state["huie_nfl_game_date"]=today-timedelta(days=1)
    if c2.button("🏈 View 2026 Week 10 projections",key="huie_nfl_week10"):
        st.session_state["huie_nfl_scope"]="Full NFL week"
        st.session_state["huie_nfl_slate_season"]=2026
        st.session_state["huie_nfl_slate_week"]=10
    scope=st.radio("Projection scope",["Game date","Full NFL week"],horizontal=True,key="huie_nfl_scope")
    try:
        if scope=="Game date":
            # Football has multiple off-days each week. If today has no
            # games, open on the next game day in the current week.
            start_date=today
            current=None
            if "huie_nfl_game_date" not in st.session_state:
                current=_schedule_day(today)
            if current==[]:
                try:
                    current_week=_current_week(today.strftime("%Y%m%d"))
                    upcoming=[_kickoff(g).astimezone(PT).date() for g in _schedule(season,current_week)
                              if _kickoff(g) and _kickoff(g).astimezone(PT).date()>today]
                    if upcoming:
                        start_date=min(upcoming)
                except Exception:
                    pass
            selected_date=st.date_input("Game date for Huie projections and results",value=start_date,
                                        key="huie_nfl_game_date",
                                        help="Pacific kickoff date. Historical days load matching archived Sam NFL HTML, when available.")
            games=current if selected_date==today and current is not None else _schedule_day(selected_date)
            period="Daily"
            date_label=selected_date.isoformat()
        else:
            ca,cb=st.columns(2)
            options=list(dict.fromkeys([season,season-1,2026]))
            year=ca.selectbox("NFL season",options,key="huie_nfl_slate_season")
            try:
                default=_current_week(today.strftime("%Y%m%d"))
            except Exception:
                default=1
            week=cb.selectbox("ESPN schedule week",list(range(1,19)),index=max(0,min(17,default-1)),
                              key="huie_nfl_slate_week")
            games=_schedule(year,week)
            period="Weekly"
            date_label=f"{year} Week {week}"
    except Exception as exc:
        st.error(f"ESPN NFL schedule unavailable ({type(exc).__name__}).")
        return
    games=[g for g in games if _kickoff(g)]
    if not games:
        st.info("No NFL games for this selection. Choose a different game date or select Full NFL week.")
        return

    by_id={g["id"]:g for g in games}
    labels={g["id"]:g["game"] for g in games}
    if scope=="Full NFL week":
        labels={g["id"]:f'{_kickoff(g).astimezone(PT):%a, %b %-d · %-I:%M %p PT} · {g["game"]}'
                for g in games}
    choice=st.selectbox("Choose matchup",["All games"]+list(by_id),
                        format_func=lambda gid:labels.get(gid,gid),key="huie_nfl_matchup_v2")
    if choice!="All games":
        games=[by_id[choice]]

    use_defense=st.checkbox("Include verified opponent defense adjustment where available",
                            key="huie_nfl_defense_v2",
                            help="Optional. Uses verified ESPN season-to-date defensive allowances, for upcoming games only.")
    if use_defense and any(not _is_upcoming(g) for g in games):
        st.caption("Opponent defense adjustment is disabled once a game starts to prevent later results from affecting its forecast.")
    if any(g["state"]=="post" for g in games):
        st.caption("Past projections are reconstructed using player stats from before kickoff. These are not saved pregame forecasts.")

    lines={}
    archive={}
    if storage_read:
        try:
            archive=_read_archive(storage_read)
        except Exception:
            st.warning("Sam NFL archive unavailable. Independent Huie forecasts are still available.")
        try:
            for year,week in {(_season_for(g),_reference_week(g)) for g in games}:
                if week is not None:
                    path=f"nfl_reference_lines_{year}_week_{week}.json"
                    lines[year,week]=_parse_stored_lines(storage_read(path))
        except Exception:
            st.caption("Some saved reference lines could not be loaded.")
    if st.session_state.pop("huie_nfl_lines_saved",False):
        st.success("NFL reference lines saved.")

    include_unlined=False
    if is_admin:
        include_unlined=st.checkbox("Include unlined players from ESPN depth charts",key="huie_nfl_include_unlined",
                                   help="Useful for adding a missing manual reference line or inspecting baseline forecasts.")
    with st.spinner("Preparing independently verified Huie projections..."):
        data,audits,failures,coverage=_build_projections(games,archive,lines,include_unlined,use_defense)
    if data.empty:
        st.info("No usable NFL projection rows for this matchup. Check ESPN availability or upload the matching Sam HTML in 🏈 NFL Model.")
        return
    if coverage<len(games):
        st.caption(f"{coverage}/{len(games)} matchups have reference lines. For missing Sam lines, upload the date-matched game HTML in 🏈 NFL Model. No NFL Excel workbook is required.")
    _render_results(data,games,period,date_label,coverage)
    st.divider()

    market_choices=sorted(data["Market"].unique())
    a,b=st.columns(2)
    markets=a.multiselect("Markets",market_choices,default=market_choices,key="huie_nfl_games_markets")
    keyword=b.text_input("Search player",key="huie_nfl_games_search").strip()
    over_only=st.checkbox("Only Huie OVER projections",key="huie_nfl_games_over_only")
    both_only=st.checkbox("Only props where BOTH Huie and Sam project OVER",key="huie_nfl_games_both_only")
    filtered=data[data["Market"].isin(markets)].copy()
    if keyword:
        filtered=filtered[filtered["Player"].str.contains(keyword,case=False,regex=False,na=False)]
    if over_only:
        filtered=filtered[filtered["Huie side"]=="🟢 OVER"]
    if both_only:
        filtered=filtered[filtered["Both models OVER"]=="Yes"]

    a,b,c,d=st.columns(4)
    a.metric("Displayed props",len(filtered))
    b.metric("Huie OVER",int(filtered["Huie side"].eq("🟢 OVER").sum()))
    c.metric("Both models OVER",int(filtered["Both models OVER"].eq("Yes").sum()))
    d.metric("Unverified Huie",int(filtered["Huie projection"].isna().sum()))
    if failures:
        st.caption(f"{failures} ESPN requests or feeds were unavailable or incomplete. Missing values were not imputed.")
    st.caption("🟢 OVER means Huie's projection is strictly above the reference line. 🔴 UNDER means strictly below. Missing data stays unverified.")
    if filtered.empty:
        st.info("No player props match these filters. Try clearing one of the OVER-only filters.")
    elif choice!="All games":
        st.subheader(labels[choice])
        _table(filtered,"huie_nfl_individual_selected")
    else:
        st.subheader("All games · matchup breakdown")
        shown=False
        for game in games:
            gid=game["id"]
            subset=filtered[filtered["Game ID"]==gid]
            if subset.empty:
                continue
            overs=int(subset["Huie side"].eq("🟢 OVER").sum())
            with st.expander(f"{labels[gid]} · {len(subset)} props · {overs} Huie OVER",expanded=not shown):
                _table(subset,"huie_nfl_individual_"+gid)
            shown=True

    with st.expander("How Huie's independent projection is calculated"):
        st.write("Huie uses verified ESPN regular-season game logs before kickoff. When a chronological test supports it, observed attempts, carries or targets adjust the historical baseline. Opponent defense is optional and uses season-to-date data only for games that have not started. Anytime TD excludes passing touchdowns. Sam projections and reference lines are not model inputs.")
        details=[{"Game":labels[gid],"Market":market,"Held-out observations":v["examples"],
                  "Distinct players":v["players"],"Baseline MAE":v["base_mae"],"Workload MAE":v["usage_mae"],
                  "MAE improvement %":v["delta_pct"],"Workload active":v["use_usage"]}
                 for gid,audit in audits.items() for market,v in audit.items()]
        if details:
            st.dataframe(pd.DataFrame(details),hide_index=True,use_container_width=True)
        else:
            st.caption("No workload validation samples for this selection. Verified historical baselines still display where available.")
        if is_admin and st.button("↻ Refresh NFL schedule and player stats",key="huie_nfl_force_refresh"):
            for cached in (_current_week,_scoreboard_day,_schedule,_roster,_depth_players,
                           _gamelog,_event_box,league_defensive_snapshot):
                cached.clear()
            st.rerun()
        if not filtered.empty:
            st.download_button("Download Huie NFL projections CSV",filtered.to_csv(index=False),
                               file_name=f"huie_nfl_{date_label.replace(' ','_')}.csv",mime="text/csv",
                               key="huie_nfl_download_v2")
    if is_admin and choice!="All games":
        _edit_lines(data,by_id[choice],storage_read,storage_write)
