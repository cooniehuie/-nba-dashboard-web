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
                   usage_markets=None):
    rows=[]
    for market in _available_markets(player["position"]):
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
                     "Method":(("Verified workload + " if usage_active else "Player baseline + ")+
                               ("experimental opponent defense" if defense["label"]!="Unavailable"
                                else "no verified defensive adjustment"))})
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
    if st.button("↻ Refresh NFL schedule and player stats",key="huie_nfl_force_refresh"):
        _current_week.clear()
        _schedule.clear()
        _roster.clear()
        _gamelog.clear()
        league_defensive_snapshot.clear()
        st.rerun()
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
    # ESPN's team statistics endpoint exposes current season-to-date totals,
    # not a historical "as of" snapshot. Never use its current totals when
    # grading an already started or completed NFL game.
    matchup_upcoming=False
    try:
        kickoff=datetime.fromisoformat(selected["date"].replace("Z","+00:00"))
        from datetime import timezone
        matchup_upcoming=selected.get("state")=="pre" and kickoff>datetime.now(timezone.utc)
    except (TypeError,ValueError):
        pass
    use_defense=st.checkbox("Adjust projections for verified opponent defense",
                            value=True,key="huie_nfl_defense_"+selected["id"],
                            help="Uses current season-to-date opponent allowances, normalized to league rates. "
                                 "Disabled for games that have started, to avoid look-ahead bias.")
    snapshot=None
    if use_defense and matchup_upcoming:
        with st.spinner("Checking opponent defensive allowance against the NFL average..."):
            try:
                snapshot=league_defensive_snapshot(season)
                if snapshot.get("coverage",0)<24:
                    st.warning("NFL defensive coverage is too incomplete to adjust projections. "
                               "Baseline/verified usage only.")
            except Exception as exc:
                st.warning("NFL defensive stats unavailable ("+type(exc).__name__+"). "
                           "Baseline/verified usage only.")
    elif use_defense and not matchup_upcoming:
        st.caption("Opponent defense adjustment is disabled for started or historical games: "
                   "ESPN's season totals would include later results.")
    if snapshot and snapshot.get("coverage",0)>=24:
        st.caption(f"Opponent defense: verified team season stats for {snapshot['coverage']} / "
                   f"{snapshot['total']} NFL teams. Neutral = league average; adjustment capped at ±12%.")
    lookup={p["team"]:next((other for other in teams if other["abbr"]!=p["team"]),None)
            for p in identities.values()}
    # Use only earlier games to compare model errors; only activate
    # workload adjustment when its held-out MAE beats the baseline.
    permitted={pid:_available_markets(identities[pid]["position"]) for pid in chosen}
    validation=validate_usage_model(player_results,_forecast,permitted)
    usage_markets={market for market,v in validation.items()
                   if v.get("validated") and v.get("use_usage")}
    if validation:
        details=[]
        for market in MARKETS:
            v=validation.get(market)
            if not v:continue
            details.append({"Market":market,"Held-out games":v["examples"],
                            "Distinct players":v["players"],
                            "Baseline MAE":v["base_mae"],
                            "Usage MAE":v["usage_mae"],
                            "MAE improvement %":v["delta_pct"],
                            "Workload active":bool(market in usage_markets),
                            "Validated sample":v["validated"]})
        if details:
            with st.expander("NFL workload model · chronological validation",expanded=False):
                st.dataframe(pd.DataFrame(details),hide_index=True,use_container_width=True)
                st.caption("Workload adjustments are enabled only when >=12 held-out observations "
                           "from >=3 players show at least a 1% reduction in mean absolute error. "
                           "All training games precede each evaluated game.")
    rows=[]
    for pid in chosen:
        player=identities[pid]
        other=lookup.get(player["team"]) or {}
        rows.extend(_baseline_rows(player,player_results.get(pid,[]),
                                   selected["game"],player["team"],
                                   other.get("abbr","—"),other.get("id"),
                                   snapshot,usage_markets))
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
    frame["Reference line"]=pd.to_numeric(
        [stored.get((str(row["Player ID"]),row["Market"]))
         for _,row in frame.iterrows()],errors="coerce")
    st.caption("Huie NFL v2: player-history baseline plus verified opponent defense (upcoming games only). Attempts/carries/targets adjust the final model only when held-out validation improves accuracy; all effects are disclosed below. Anytime TD means rushing + receiving TDs, **not passing TDs**. Reference lines require administrator input.")
    a,b,c,d=st.columns(4)
    a.metric("Players with projections",frame["Player"].nunique())
    b.metric("NFL stat projections",int(frame["Huie projection"].notna().sum()))
    c.metric("Context-adjusted",int(((frame["Huie projection"]-frame["Baseline"]).abs()>0.01).sum()))
    d.metric("Reference lines",int(frame["Reference line"].notna().sum()))
    choices=list(MARKETS)
    selected_markets=st.multiselect("Markets",choices,default=choices,key="huie_nfl_markets")
    visible=frame[frame["Market"].isin(selected_markets)].copy()
    if visible.empty:
        st.info("Choose at least one market.")
        return
    if is_admin:
        st.caption("Admin: enter actual Robinhood/reference thresholds in the Reference line column. No odds are inferred.")
        edit_cols=["Player","Market","Huie projection","Baseline","Reference line","Model side"]
        edited=st.data_editor(visible[edit_cols].copy(),hide_index=True,use_container_width=True,
                              key="huie_nfl_line_editor_"+selected["id"],
                              disabled=[col for col in edit_cols if col!="Reference line"],
                              column_config={"Reference line":st.column_config.NumberColumn("Reference line",min_value=0.0,step=0.5,format="%.1f")})
        visible["Reference line"]=pd.to_numeric(edited["Reference line"],errors="coerce")
        if st.button("💾 Save NFL reference lines",key="huie_nfl_save_lines",type="primary"):
            if storage_write is None:
                st.error("Private storage isn't configured.")
            else:
                lines=dict(stored)
                for _,row in visible.iterrows():
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
    columns=["Player","Team","Opponent","Market","Huie projection","Reference line",
             "Model side","Baseline","Def. adjustment %","Matchup",
             "Expected volume","TD chance %","Status"]
    st.dataframe(visible[columns],hide_index=True,use_container_width=True,
                 column_config={"Huie projection":st.column_config.NumberColumn("Huie projection",format="%.1f"),
                                "Reference line":st.column_config.NumberColumn("Reference line",format="%.1f")})
    with st.expander("Download / detailed projections",expanded=False):
        st.download_button("Download Huie NFL projections CSV",visible.to_csv(index=False),
                           file_name=f"huie_nfl_{season}_espnweek_{week}.csv",
                           mime="text/csv",key="huie_nfl_download")
        st.dataframe(visible[["Player","Market","Games","Method","Workload projection",
                                   "Last game","2 games ago","3 games ago","Season avg","1+ TD games",
                                   "Expected volume","Volume trend %","Def. adjustment %","Matchup",
                                   "Def. games","Opp allowed/game","League allowed/game",
                                   "TD chance %","Sample","Status"]],
                     hide_index=True,use_container_width=True)
    st.caption("NFL v2 limitations: matchup effects are capped experimental heuristics, not calibrated betting probabilities. Workload updates activate only after a positive chronological MAE check. Opponent defense is season-normalized and never used in retrospective projections. Weather, snap counts, market prices and game-day injury verification are not yet modeled; missing feeds fall back to player history. Three observed games per stat are required.")
