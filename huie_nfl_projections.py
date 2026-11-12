"""Huie NFL projections, independent from NBA/Sam and wager settlement data.

ESPN Site v2 schedules/rosters + Web API v3 completed NFL player game logs.
No invented reference lines, no fabricated injured-player availability.
"""
import json
import math
import re
import statistics
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

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


@st.cache_data(ttl=1800,show_spinner=False)
def _schedule(season,week):
    data=_fetch(SITE+"scoreboard?dates="+str(season)+"&seasontype=2&week="+str(week)+"&limit=50")
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
        if len(teams)!=2:
            continue
        events.append({"id":str(event.get("id") or ""),"game":str(event.get("shortName") or event.get("name") or ""),
                       "date":str(event.get("date") or ""),"state":(event.get("status") or {}).get("type",{}).get("state",""),
                       "teams":teams})
    events.sort(key=lambda e:e["date"])
    return events


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


def _baseline_rows(player,logs,game,team):
    rows=[]
    for market in _available_markets(player["position"]):
        estimate=_forecast(logs,market)
        if estimate is None:continue
        # A clearly OUT player is not presented as a playable projection.
        status=player.get("report","")
        is_out=bool(re.search(r"\b(out|inactive|injured reserve|ir|suspended)\b",status.lower()))
        rows.append({"Game":game,"Team":team,"Player":player["name"],"Position":player["position"],
                     "Market":market,"Huie projection":None if is_out else estimate["projection"],
                     "Reference line":None,"Model side":"—",
                     "Last game":estimate["last_three"][0],"2 games ago":estimate["last_three"][1],
                     "3 games ago":estimate["last_three"][2],
                     "Season avg":estimate["season_avg"],"Games":estimate["games"],
                     "1+ TD games":(f'{estimate["hit_one"]}/{estimate["games"]}' if market=="Anytime TD" else "—"),
                     "Sample":estimate["confidence"],"Status":"OUT (reported)" if is_out else (status or "Not verified"),
                     "Player ID":player["id"],"Method":estimate["method"]})
    return rows


def _default_players(roster):
    grouped={pos:[p for p in roster if p["position"]==pos] for pos in OFFENSE}
    # These are roster entries, NOT claims that selected players are starters.
    return [p["id"] for pos,limit in [("QB",1),("RB",2),("WR",3),("TE",2)]
            for p in grouped[pos][:limit]]


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


def render(storage_read=None,storage_write=None,is_admin=False):
    st.title("🏈 Huie NFL Projections")
    st.caption("Independent NFL prop model · ESPN regular-season game logs · No Sam/NBA projections used.")
    today=datetime.now(PT).date()
    season=today.year if today.month>=8 else today.year-1
    try:
        default_week=_current_week(today.strftime("%Y%m%d"))
    except Exception:
        default_week=1
        st.warning("Could not detect the NFL's current schedule week from ESPN. Choose the schedule index below.")
    a,b=st.columns([1,2])
    season=int(a.selectbox("NFL season",[season,season-1],key="huie_nfl_season"))
    week=int(b.selectbox("ESPN schedule week",list(range(1,19)),
                         index=max(0,min(17,default_week-1)),key="huie_nfl_week"))
    try:
        schedule=_schedule(season,week)
    except Exception as exc:
        st.error("NFL schedule unavailable from ESPN ("+type(exc).__name__+"). No games were fabricated.")
        return
    if not schedule:
        st.info("No regular-season games returned for this schedule window.")
        return
    def pretty(game):
        try:
            when=datetime.fromisoformat(game["date"].replace("Z","+00:00")).astimezone(PT)
            return when.strftime("%a, %b %-d · %-I:%M %p PT")+" · "+game["game"]
        except (ValueError,TypeError):
            return game["game"]
    selected=st.selectbox("Choose matchup",schedule,format_func=pretty,
                          key="huie_nfl_matchup")
    if selected.get("state")=="post":
        st.warning("This matchup is already final. Projections use games before its kickoff and should not be treated as a documented pregame snapshot.")
    teams=selected["teams"]
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            future={pool.submit(_roster,t["id"],season):t for t in teams}
            rosters=[]
            for f in as_completed(future):
                team=future[f]
                for player in f.result():
                    player={**player,"team":team["abbr"]}
                    rosters.append(player)
    except Exception as exc:
        st.error("Could not retrieve ESPN's NFL rosters ("+type(exc).__name__+").")
        return
    if not rosters:
        st.info("No QB, RB, WR or TE players were found on these team rosters.")
        return
    rosters=sorted(rosters,key=lambda p:(p["team"],OFFENSE.index(p["position"]),p["name"]))
    identities={p["id"]:p for p in rosters}
    defaults=[pid for team in teams for pid in _default_players([p for p in rosters if p["team"]==team["abbr"]])]
    chosen=st.multiselect("Players to project (ESPN rosters; starter status not guaranteed)",
                          list(identities),default=defaults,
                          format_func=lambda pid:f'{identities[pid]["name"]} · {identities[pid]["team"]} {identities[pid]["position"]}',
                          key="huie_nfl_players_"+selected["id"])
    if len(chosen)>40:
        st.warning("Select 40 players or fewer to keep the box-score requests manageable.")
        return
    if not chosen:
        st.info("Select at least one NFL player to calculate projections.")
        return
    with st.spinner("Calculating Huie NFL projections from completed regular-season game logs..."):
        player_results={}
        failures=[]
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures={pool.submit(_gamelog,pid,season,selected["date"]):pid for pid in chosen}
            for future in as_completed(futures):
                pid=futures[future]
                try:player_results[pid]=future.result()
                except Exception as exc:failures.append((pid,type(exc).__name__))
    rows=[]
    for pid in chosen:
        player=identities[pid]
        rows.extend(_baseline_rows(player,player_results.get(pid,[]),
                                   selected["game"],player["team"]))
    if failures:
        st.warning(f'{len(failures)} player game logs could not be retrieved. Missing projections were not imputed.')
        with st.expander("Unavailable player feeds"):
            st.write(", ".join(identities[pid]["name"]+" ("+reason+")" for pid,reason in failures))
    if not rows:
        st.info("Not enough verified NFL games for these players. Three observed games per stat are required.")
        return
    frame=pd.DataFrame(rows)
    path=f"nfl_reference_lines_{season}_week_{week}.json"
    stored={}
    if storage_read:
        try:stored=_parse_stored_lines(storage_read(path))
        except Exception:st.caption("Saved reference lines are unavailable; no values were guessed.")
    frame["Reference line"]=[stored.get((str(row["Player ID"]),row["Market"]))
                             for _,row in frame.iterrows()]
    st.caption("Huie uses a recency-weighted, season-shrunk baseline. Anytime TD counts rushing + receiving touchdowns, **not passing TDs**. Reference lines must be entered by the administrator; no sportsbook prices are assumed.")
    a,b,c=st.columns(3)
    a.metric("Players with projections",frame["Player"].nunique())
    b.metric("NFL stat projections",int(frame["Huie projection"].notna().sum()))
    c.metric("Reference lines available",int(frame["Reference line"].notna().sum()))
    choices=list(MARKETS)
    selected_markets=st.multiselect("Markets",choices,default=choices,key="huie_nfl_markets")
    visible=frame[frame["Market"].isin(selected_markets)].copy()
    if visible.empty:
        st.info("Choose at least one market.")
        return
    if is_admin:
        st.caption("Admin: enter actual Robinhood/reference thresholds in the Reference line column. No odds are inferred.")
        edited=st.data_editor(visible,hide_index=True,use_container_width=True,key="huie_nfl_line_editor_"+selected["id"],
                              disabled=[col for col in visible.columns if col!="Reference line"],
                              column_config={"Reference line":st.column_config.NumberColumn("Reference line",min_value=0.0,step=0.5,format="%.1f"),
                                             "Player ID":None,"Method":None})
        visible=edited.copy()
        if st.button("💾 Save NFL reference lines",key="huie_nfl_save_lines",type="primary"):
            if storage_write is None:
                st.error("Private storage isn't configured.")
            else:
                lines=dict(stored)
                for _,row in edited.iterrows():
                    key=(str(row["Player ID"]),row["Market"])
                    newval=_num(row["Reference line"])
                    if newval is None:lines.pop(key,None)
                    else:lines[key]=newval
                payload=[{"player_id":pid,"market":market,"line":val}
                         for (pid,market),val in sorted(lines.items())]
                try:
                    storage_write(path,json.dumps(payload,indent=2).encode("utf-8"))
                    st.success("NFL reference lines saved for this schedule window.")
                except Exception as exc:
                    st.error("Couldn't save NFL reference lines ("+type(exc).__name__+").")
    for idx,row in visible.iterrows():
        baseline=_num(row["Huie projection"])
        line=_num(row["Reference line"])
        visible.at[idx,"Model side"]=(
            "🟢 OVER" if baseline is not None and line is not None and baseline>line else
            "🔴 UNDER" if baseline is not None and line is not None and baseline<line else
            "⚪ AT LINE" if baseline is not None and line is not None and baseline==line else
            "—"
        )
    columns=["Player","Team","Position","Market","Huie projection","Reference line",
             "Model side","Last game","2 games ago","3 games ago","Season avg",
             "Games","1+ TD games","Sample","Status"]
    st.dataframe(visible[columns],hide_index=True,use_container_width=True,
                 column_config={"Huie projection":st.column_config.NumberColumn("Huie projection",format="%.1f"),
                                "Reference line":st.column_config.NumberColumn("Reference line",format="%.1f")})
    with st.expander("Download / detailed projections",expanded=False):
        st.download_button("Download Huie NFL projections CSV",visible.to_csv(index=False),
                           file_name=f"huie_nfl_{season}_espnweek_{week}.csv",
                           mime="text/csv",key="huie_nfl_download")
        st.dataframe(visible[["Player","Market","Games","Method","Status"]],hide_index=True,use_container_width=True)
    st.caption("Limitations: This baseline does not yet adjust for opponent defense, injuries, changes in workload, or implied odds. A higher projection alone is not a validated betting edge. Players with fewer than 3 recorded games per stat are omitted.")
