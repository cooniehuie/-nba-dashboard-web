"""Exploratory, read-only parlay builder and independent baseline comparison."""
import itertools
import math
import re
import pandas as pd
import streamlit as st
from parlay_probability import joint_bounds, wilson_interval, yes_break_even, yes_expected_value
from parlay_context import game_day_context, injury_status, parse_game, name_key, team_key, starter_match, team_context, matchup_adjustment
from parlay_calibration import train as train_probabilities, predict as calibrated_predict
from parlay_joint import correlated_joint
from parlay_quotes import fetch_quote_feed, match_quote
from statistics import pstdev

def _col(df, *names):
    for name in names:
        for col in df.columns:
            if str(col).strip().lower() == name.lower():
                return col
    return None

def _num(value):
    try:
        if pd.isna(value): return None
        found = re.search(r"-?\d+(?:\.\d+)?", str(value))
        return float(found.group()) if found else None
    except (ValueError, TypeError):
        return None

def _market_label(value):
    """Recognize a single NBA stat market; reject combined or unclear props."""
    text=str(value or "").casefold().replace("_"," ")
    detected=set()
    if re.search(r"\b(assists?|ast)\b",text):detected.add("Assists")
    if re.search(r"\b(rebounds?|reb)\b",text):detected.add("Rebounds")
    if re.search(r"\b(3pm|3ptm?|fg3m|threes?|three[- ]?pointers?|three[- ]?points?|3[- ]?pointers?|3[- ]?points?|3s)\b",text):
        detected.add("Threes")
    if re.search(r"\b(points?|pts)\b",text):
        if "Threes" not in detected or re.search(r"\b(points?|pts)\s*(?:[+&/]|and)\s*",text):
            detected.add("Points")
    return next(iter(detected)) if len(detected)==1 else None

def _join_bankroll_safe_lines(bankroll, props, diagnostics=None):
    """Join verified safe lines to props; avoid guesses on duplicate players/markets."""
    info=diagnostics if diagnostics is not None else {}
    info.update({"bankroll_rows":len(bankroll) if bankroll is not None else 0,
                 "props_rows":len(props) if props is not None else 0,
                 "numeric_safe_lines":0,"player_matches":0,"market_matches":0,
                 "matched_rows":0,"game_label_fallbacks":0,
                 "ambiguous_rows":0,"unmatched_markets":0})
    if bankroll is None or props is None or bankroll.empty or props.empty:
        return pd.DataFrame()
    bp=_col(bankroll,"Player")
    bg=_col(bankroll,"Game")
    bl=_col(bankroll,"Safer line","Safe line")
    bm=_col(bankroll,"Our play","Market")
    pp=_col(props,"Player")
    pg=_col(props,"Game")
    pm=_col(props,"Market")
    if any(x is None for x in (bp,bl,pp,pm)):
        info["error"]="Missing player, safe-line or market columns"
        return pd.DataFrame()
    def game_key(value):
        pair=parse_game(str(value))
        if pair:return frozenset(pair)
        return re.sub(r"[^a-z0-9]","",str(value).casefold())
    def player_match(a,b):
        aa=name_key(a).split()
        bb=name_key(b).split()
        if len(aa)<2 or len(bb)<2:return False
        return aa==bb or (aa[0][0]==bb[0][0] and aa[1:]==bb[1:])
    ready=[]
    for i,row in props.iterrows():
        market=_market_label(row[pm])
        if market is None:continue
        ready.append({"index":i,"market":market,"player":row[pp],
                      "game":row[pg] if pg is not None else None,"row":row})
    chosen={}
    invalid=set()
    for _,row in bankroll.iterrows():
        safe=_num(row[bl])
        if safe is None:continue
        info["numeric_safe_lines"]+=1
        play=str(row[bm]) if bm is not None else ""
        if re.search(r"\b(under|unders)\b",play.casefold()):
            continue
        candidates=[p for p in ready if player_match(row[bp],p["player"])]
        if not candidates:continue
        info["player_matches"]+=1
        market=_market_label(play+" "+str(row[bl]))
        if market:
            candidates=[p for p in candidates if p["market"]==market]
        if not candidates:
            info["unmatched_markets"]+=1
            continue
        info["market_matches"]+=1
        # Games often use different labels (e.g. BKN @ DAL vs Brooklyn at Dallas).
        # Only relax a game mismatch if player + market is already unique.
        if bg is not None and pg is not None and pd.notna(row[bg]):
            same_game=[p for p in candidates if game_key(row[bg])==game_key(p["game"])]
            if same_game:
                candidates=same_game
            elif len(candidates)==1:
                info["game_label_fallbacks"]+=1
        if len(candidates)!=1:
            info["ambiguous_rows"]+=1
            continue
        match=candidates[0]
        idx=match["index"]
        if idx in chosen and chosen[idx]!=safe:
            invalid.add(idx)
            info["ambiguous_rows"]+=1
        else:
            chosen[idx]=safe
    matched=[]
    for item in ready:
        idx=item["index"]
        if idx not in chosen or idx in invalid:continue
        record=item["row"].to_dict()
        record["Safer line"]=chosen[idx]
        matched.append(record)
    info["matched_rows"]=len(matched)
    return pd.DataFrame(matched)

def _source_candidates(bankroll, all_props=None, diagnostics=None):
    """Always combine the two saved workbook sheets when both are available.

    Bankroll's descriptive 'Our play' field can be parsed as a market, so
    checking whether _candidates(bankroll) is empty is NOT a valid trigger
    for joining. Using it silently drops all Sam projections.
    """
    if all_props is not None and not all_props.empty:
        joined=_join_bankroll_safe_lines(bankroll, all_props, diagnostics)
        return _candidates(joined), joined
    return _candidates(bankroll), pd.DataFrame()

def _candidate_diagnostics(df):
    """Aggregate input coverage only; never expose private player data in logs."""
    if df is None or df.empty:
        return {"Matched input rows": 0}
    stats=("Last game","2 games ago","3 games ago")
    columns=[_col(df,name) for name in stats]
    report={"Matched input rows":len(df),
            "Recognized markets":sum(_market_label(v) is not None for v in df[_col(df,"Market")])
                                  if _col(df,"Market") is not None else 0}
    for label,col in zip(stats,columns):
        report["Numeric "+label]=sum(_num(v) is not None for v in df[col]) if col is not None else 0
    report["Three recorded games"]=sum(
        all(col is not None and _num(row[col]) is not None for col in columns)
        for _,row in df.iterrows())
    avgcol=_col(df,"Last 3 avg","Last 3 average")
    report["Numeric last-3 average"]=sum(_num(v) is not None for v in df[avgcol]) if avgcol is not None else 0
    projcol=_col(df,"Model projection")
    report["Numeric Sam projections"]=sum(_num(v) is not None for v in df[projcol]) if projcol is not None else 0
    return report

def _candidates(df, *, reference_only=False):
    """Parse independent projections; production uses only All Player Props Reference line."""
    if df is None or df.empty:return pd.DataFrame()
    p=_col(df,"Player","Player name")
    m=_col(df,"Market","Stat","Stat type","Prop type","Prop","Category")
    line=_col(df,"Reference line") if reference_only else _col(df,"Safer line","Safe line","Safe alternate line")
    game=_col(df,"Game","Matchup")
    projection=_col(df,"Model projection","Sam projection","Projection")
    avg_col=_col(df,"Last 3 avg","Last 3 average")
    history=[
        _col(df,"Last game","1 game","1 game ago","Last","Game 1"),
        _col(df,"2 games ago","2 games","2 games back","Game 2"),
        _col(df,"3 games ago","3 games","3 games back","Game 3"),
    ]
    if p is None or line is None:return pd.DataFrame()
    rows=[]
    for _,r in df.iterrows():
        name=str(r[p]).strip()
        target=_num(r[line])
        if not name or name.lower()=="nan" or target is None:continue
        market=_market_label(r[m]) if m is not None and pd.notna(r[m]) else None
        if market is None:
            market=_market_label(r[line]) if pd.notna(r[line]) else None
        if market not in ("Points","Rebounds","Assists","Threes"):continue
        values=[_num(r[c]) if c is not None else None for c in history]
        valid=[v for v in values if v is not None]
        # An average is a projection baseline, not proof of three separate hits.
        recent_complete=len(valid)==3
        observed_avg=sum(valid)/3 if recent_complete else (_num(r[avg_col]) if avg_col is not None else None)
        baseline=round(observed_avg,2) if observed_avg is not None else None
        recent_hits=sum(v>=target for v in valid) if recent_complete else None
        sam=_num(r[projection]) if projection else None
        rows.append({"Player":name,"Market":market,"Safe line":target,
                     "Line source":"All Player Props · Reference line" if reference_only else "Safe line",
                     "Game":str(r[game]) if game else "Unknown",
                     "Sam projection":sam,"Huie baseline":baseline,
                     "Recent hits":recent_hits,"Games":len(valid),
                     "Recent hit rate":recent_hits/3 if recent_hits is not None else None,
                     "Baseline source":"3 separate games" if recent_complete else
                                       ("Workbook last-3 average" if baseline is not None else "Unavailable"),
                     "Baseline margin":round(baseline-target,2) if baseline is not None else None,
                     "Sam margin":round(sam-target,2) if sam is not None else None})
    result=pd.DataFrame(rows)
    if result.empty:return result
    return result.drop_duplicates(subset=["Player","Market","Safe line","Game"])

@st.cache_data(ttl=21600, show_spinner=False)
def _historical_boxscores(days_back=30):
    """Fetch completed ESPN boxscores for recent calendar days; no synthetic games."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    from collections import defaultdict
    from urllib.request import Request, urlopen
    import json
    def fetch(url):
        with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=8) as response:
            return json.load(response)
    today=datetime.now(ZoneInfo("America/Los_Angeles")).date()
    result=defaultdict(list)
    failures=0
    for offset in range(1, days_back+1):
        day=today-timedelta(days=offset)
        try:
            board=fetch("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates="+day.strftime("%Y%m%d"))
            games=[]
            players=[]
            for event in board.get("events",[]):
                if event.get("status",{}).get("type",{}).get("state")!="post":continue
                summary=fetch("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event="+str(event["id"]))
                for team in summary.get("boxscore",{}).get("players",[]):
                    for group in team.get("statistics",[]):
                        keys=[str(k).lower() for k in group.get("keys",[])]
                        labels=[str(k).lower() for k in group.get("labels",[])]
                        for athlete in group.get("athletes",[]):
                            if athlete.get("didNotPlay") or athlete.get("inactive"):continue
                            stats=athlete.get("stats",[])
                            def stat(*options):
                                for key in options:
                                    idx=keys.index(key) if key in keys else (labels.index(key) if key in labels else -1)
                                    if 0<=idx<len(stats):return stats[idx]
                                return None
                            def numeric(value):
                                try:
                                    raw=str(value).strip()
                                    if ":" in raw:
                                        parts=raw.split(":")
                                        if len(parts)==2:
                                            return float(parts[0])+float(parts[1])/60
                                    return float(raw.split("-")[0])
                                except (ValueError,TypeError):return None
                            info=athlete.get("athlete",{})
                            players.append({"name":info.get("displayName",info.get("fullName","")),
                                            "team":team.get("team",{}).get("abbreviation",""),
                                            "game":{"state":"post"},
                                            "stats":{"Points":numeric(stat("pts","points")),
                                                     "Rebounds":numeric(stat("reb","rebs","rebounds")),
                                                     "Assists":numeric(stat("ast","assists")),
                                                     "Threes":numeric(stat("3pt","3pm","3-pt")),
                                                     "Minutes":numeric(stat("min","minutes"))}})
        except Exception:
            failures+=1
            continue
        for athlete in players:
            game=athlete.get("game",{})
            if game.get("state")!="post" or athlete.get("dnp"):
                continue
            key=(str(athlete.get("name","")).casefold(),str(athlete.get("team","")).upper())
            result[key].append({"date":day.isoformat(),"stats":athlete.get("stats",{})})
    return dict(result),failures

def _history_view(data):
    st.subheader("External results · ESPN completed NBA games")
    st.caption("Huie's independent projections automatically use verified completed ESPN games when the workbook lacks recent stats. ESPN history is cached for six hours; no results are fabricated.")
    auto=st.checkbox("Automatically load verified ESPN history for Huie's model",
                     value=True,key="lab_auto_history")
    if st.button("Refresh verified ESPN history",key="lab_fetch_history"):
        _historical_boxscores.clear()
    st.session_state["lab_history_enabled"]=auto
    if not auto:
        for key in ("lab_history_results","lab_history_raw","lab_calibration"):
            st.session_state.pop(key,None)
        st.info("ESPN history loading is off. Huie projections require three actual games or a recorded workbook average.")
        return
    with st.spinner("Checking recent completed NBA box scores..."):
        try:
            history,failures=_historical_boxscores()
        except Exception as exc:
            st.warning("Historical results could not be retrieved: "+str(exc))
            return
    st.session_state["lab_history_raw"]=history
    st.session_state["lab_calibration"]=train_probabilities(history)
    calibration=st.session_state["lab_calibration"]
    if calibration:
        with st.expander("Walk-forward probability calibration · held-out results"):
            calibration_rows=[{"Market":market,"Training examples":row["train_n"],
                               "Holdout examples":row["holdout_n"],
                               "Brier score":row["brier"],"Naive baseline Brier":row["naive_brier"],
                               "Passed held-out check":row["calibrated"]}
                              for market,row in calibration.items()]
            st.dataframe(pd.DataFrame(calibration_rows),hide_index=True,use_container_width=True)
            st.caption("Calibration uses synthetic historical alternate lines (not archived Robinhood prices). Markets that fail the holdout check produce no forecast probability.")
    else:
        st.caption("Not enough ESPN completed games to validate hit-probability calibration.")
    # Match by unambiguous normalized player names; abbreviated names that
    # map to multiple athletes are deliberately left unresolved.
    import unicodedata
    def norm(value):
        value=unicodedata.normalize("NFKD",str(value).lower())
        return " ".join("".join(ch if ch.isalnum() else " " for ch in value).split())
    output=[]
    for _,pick in data.iterrows():
        short=norm(pick["Player"]).split()
        if len(short)<2:continue
        matches=[]
        for (name,team),games in history.items():
            full=norm(name).split()
            if len(full)>1 and full[0].startswith(short[0]) and full[1:]==short[1:]:
                matches.append((name,team,games))
        if len(matches)!=1:continue
        name,team,games=matches[0]
        samples=[(float(g["stats"][pick["Market"]]),g["stats"].get("Minutes"))
                 for g in games if g["stats"].get(pick["Market"]) is not None]
        if not samples:continue
        values=[x[0] for x in samples]
        minute_values=[float(m) for _,m in samples if m is not None and float(m)>0]
        # A minutes-normalized estimate only uses observed minutes; it is
        # withheld if there is insufficient minutes data.
        per_min=[v/float(m) for v,m in samples if m is not None and float(m)>=5]
        projected_minutes=(sum(minute_values[:5])/len(minute_values[:5])) if len(minute_values)>=5 else None
        minutes_estimate=(sum(per_min)/len(per_min)*projected_minutes) if projected_minutes and len(per_min)>=5 else None
        output.append({"Player":name,"Market":pick["Market"],"Safe line":pick["Safe line"],
                       "Recent three games":min(3,len(values)),
                       "Recent three hits":sum(v>=pick["Safe line"] for v in values[:3]) if len(values)>=3 else None,
                       "Recent three average":round(sum(values[:3])/3,2) if len(values)>=3 else None,
                       "Completed games":len(values),"Hits":sum(v>=pick["Safe line"] for v in values),
                       "Historical average":round(sum(values)/len(values),2),
                       "Historical SD":round(max(.75,pstdev(values[:5])),3) if len(values)>=5 else None,
                       "ESPN team":team,
                       "Minutes projection":round(minutes_estimate,2) if minutes_estimate is not None else None,
                       "Recent minutes":round(projected_minutes,1) if projected_minutes is not None else None,
                       "Sam projection":pick["Sam projection"],
                       "Huie baseline":pick["Huie baseline"]})
    if output:
        st.session_state["lab_history_results"]=pd.DataFrame(output)
        st.dataframe(pd.DataFrame(output),use_container_width=True,hide_index=True)
    else:
        st.session_state.pop("lab_history_results",None)
        st.info("No unambiguous completed-game records were found for the current candidates.")
    # Walk-forward evaluation: predict each game only from the five games
    # before it. This avoids training on the result being predicted.
    backtest=[]
    for (name,team),games in history.items():
        chronological=sorted(games,key=lambda x:x["date"])
        for market in ("Points","Rebounds","Assists","Threes"):
            valid=[(g["date"],g["stats"].get(market)) for g in chronological
                   if g["stats"].get(market) is not None]
            for i in range(5,len(valid)):
                prior=[float(x[1]) for x in valid[i-5:i]]
                predicted=sum(prior)/5
                actual=float(valid[i][1])
                backtest.append({"Player":name,"Market":market,
                                 "Date":valid[i][0],"Predicted":predicted,
                                 "Actual":actual,"Absolute error":abs(predicted-actual)})
    with st.expander("Historical backtest · 5-game rolling baseline"):
        st.caption("Walk-forward mean absolute error from previous-five-game forecasts. This measures Huie's simple baseline only, not Sam's historical performance or betting returns.")
        if backtest:
            back=pd.DataFrame(backtest)
            summary=back.groupby("Market",as_index=False).agg(
                Predictions=("Actual","size"),MAE=("Absolute error","mean"))
            summary["MAE"]=summary["MAE"].round(2)
            st.dataframe(summary,use_container_width=True,hide_index=True)
            st.caption("A lower MAE means a more accurate stat projection. Do not compare MAE across different stat types as though they share the same scale.")
        else:st.info("Not enough verified games for a walk-forward backtest.")
    if failures:st.warning(str(failures)+" dates could not be fetched; historical samples are incomplete.")

def dual_model_eligible(data, minimum_recent_hits=2):
    """Strict dual-projection OVER agreement; optional descriptive form filter.

    The calling site supplies Reference line as the internal Safe line field.
    Missing estimates NEVER qualify; equality does not qualify.
    """
    if data is None or data.empty:return data
    required=["Huie baseline","Safe line","Sam projection"]
    if minimum_recent_hits is not None:required.append("Recent hits")
    if any(col not in data.columns for col in required):
        return data.iloc[0:0].copy()
    recent_ok=(pd.Series(True,index=data.index) if minimum_recent_hits is None
               else pd.to_numeric(data["Recent hits"],errors="coerce").ge(minimum_recent_hits))
    line=pd.to_numeric(data["Safe line"],errors="coerce")
    huie=pd.to_numeric(data["Huie baseline"],errors="coerce")
    sam=pd.to_numeric(data["Sam projection"],errors="coerce")
    return data[recent_ok & line.notna() & huie.gt(line) & sam.gt(line)].copy()

@st.cache_data(ttl=900,show_spinner=False)
def _live_nba_context():
    return game_day_context()

@st.cache_data(ttl=21600,show_spinner=False)
def _recent_opponent_context(opponents):
    return team_context(opponents,days=21,max_per_team=6)

@st.cache_data(ttl=180,show_spinner=False)
def _configured_contract_quotes(url,token):
    return fetch_quote_feed(url,token)

def render(all_props):
    st.title("🧪 Smart Parlay Builder & Huie's Model Lab")
    st.caption("All Player Props only · Sam's model versus Huie's independent model · both must exceed the same Reference line. No bets are placed.")
    if all_props is None or all_props.empty:
        st.info("Today's All Player Props sheet is missing. Upload a workbook containing Player, Market, Reference line and Model projection.")
        return
    data=_candidates(all_props,reference_only=True)
    if data.empty:
        st.warning("No usable All Player Props rows contain a player, recognized stat market and numeric Reference line. Bankroll Builder safe lines are not used.")
        st.caption("Available All Player Props columns: "+", ".join(map(str,all_props.columns)))
        st.dataframe(pd.DataFrame([{"Check":k,"Rows":v} for k,v in _candidate_diagnostics(all_props).items()]),use_container_width=True,hide_index=True)
        return
    st.subheader("Huie's Model Lab · independent recent-games baseline")
    st.write("Huie's baseline uses three recorded player results, or the workbook's recorded last-three average when individual games are incomplete. Missing values remain unavailable and never count as hits.")
    st.caption("Recent 3-game hit rates are descriptive. External injury, lineup and matchup data are shown only when verified. Calibrated probabilities require a held-out historical check.")
    missing_sam=data["Sam projection"].notna().sum()==0
    missing_history=data["Games"].lt(3).any()
    with st.expander("All Player Props · data coverage",expanded=bool(missing_sam)):
        st.dataframe(pd.DataFrame([{"Check":k,"Rows":v} for k,v in _candidate_diagnostics(all_props).items()]),use_container_width=True,hide_index=True)
        st.caption("Reference lines come exclusively from All Player Props. Historical n/a entries are not game results, and reference lines are not Sam projections.")
    if missing_sam:
        st.warning("All Player Props has no numeric Sam model projections for these rows. No player can qualify until the Model projection column contains real numbers.")
    if missing_history:
        st.info("The saved workbook has missing recent-game statistics. Huie's model will automatically check verified ESPN completed games below; players with insufficient data remain unverified.")
    _history_view(data)
    historical=st.session_state.get("lab_history_results")
    if st.session_state.get("lab_history_enabled") and isinstance(historical,pd.DataFrame) and not historical.empty:
        # Join on unique player initial + surname and stat, never silently
        # assign ambiguous names (e.g. Amen versus Ausar Thompson).
        import unicodedata
        def initials(value):
            v=unicodedata.normalize("NFKD",str(value).lower())
            words=" ".join("".join(ch if ch.isalnum() else " " for ch in v).split()).split()
            return (words[0][:1]+" "+" ".join(words[1:])) if len(words)>1 else ""
        counts=historical.assign(_key=historical["Player"].map(initials)).groupby(["_key","Market"]).size()
        safe=historical.assign(_key=historical["Player"].map(initials))
        safe=safe[safe.apply(lambda x:counts.loc[(x["_key"],x["Market"])]==1,axis=1)]
        lookup_history={(x["_key"],x["Market"]):x for _,x in safe.iterrows()}
        for idx,pick in data.iterrows():
            rec=lookup_history.get((initials(pick["Player"]),pick["Market"]))
            if rec is None or rec["Completed games"]<3:continue
            # Fill missing individual-game evidence only from verified ESPN games.
            if rec["Recent three games"]==3:
                data.at[idx,"Recent hits"]=int(rec["Recent three hits"])
                data.at[idx,"Games"]=3
                data.at[idx,"Recent hit rate"]=int(rec["Recent three hits"])/3
            minutes_based=rec.get("Minutes projection")
            if rec["Completed games"]>=5 and pd.notna(minutes_based):
                baseline=float(minutes_based)
                source="ESPN minutes-adjusted projection"
            else:
                baseline=float(rec["Recent three average"])
                source="ESPN latest 3 completed games"
            data.at[idx,"Huie baseline"]=round(baseline,2)
            data.at[idx,"Baseline source"]=source
            data.at[idx,"Baseline margin"]=round(baseline-pick["Safe line"],2)
            data.at[idx,"External games"]=int(rec["Completed games"])
            data.at[idx,"External hits"]=int(rec["Hits"])
            data.at[idx,"Historical SD"]=rec.get("Historical SD")
            data.at[idx,"ESPN team"]=rec.get("ESPN team")
    st.subheader("Model comparison · available verified information")
    show=data.sort_values(["Recent hits","Baseline margin"],ascending=False,na_position="last").copy()
    show["Recent hit rate"]=show["Recent hit rate"].map(
        lambda x:f"{x:.0%}" if pd.notna(x) else "Unverified")
    st.dataframe(show.rename(columns={"Safe line":"Reference line","Huie baseline":"Huie projection"}),use_container_width=True,hide_index=True)
    st.caption("The model comparison refreshes after external historical results load. Entries missing either model's estimate do not qualify for the dual-model parlay list.")

    st.subheader("Game-day availability and risk checks")
    st.caption("Manual injury/role review is required: this is not a live injury feed. Excluded players are never used in generated parlays.")
    excluded_text=st.text_area("Exclude players (one per line; injury, minutes limit, or uncertain role)",
                               value="",key="lab_excluded_players",height=80)
    exclusions={x.strip().casefold() for x in excluded_text.splitlines() if x.strip()}
    st.subheader("ESPN injury reports and verified starters")
    st.caption("ESPN injury listings are not a medical clearance. Starter confirmations use complete NBA official starting fives when published, or ESPN in-progress/final boxscores. Pregame listings are otherwise unknown.")
    use_live=st.checkbox("Load ESPN game-day injury and confirmed-starter checks",value=True,key="lab_live_context")
    live=None
    if use_live:
        with st.spinner("Checking injury report and game-day information..."):
            live=_live_nba_context()
        if live["injury_error"]:
            st.warning("ESPN injury report unavailable ("+live["injury_error"]+"). Player availability remains unverified.")
        else:
            st.caption("ESPN injury list retrieved at "+live["checked_at"]+" · Players not listed are not automatically cleared.")
        if live["schedule_error"]:
            st.caption("ESPN game schedule unavailable; starters cannot be verified.")
    for idx,pick in data.iterrows():
        status="Feed not checked";flag="unknown";starting="Unconfirmed"
        side=parse_game(pick.get("Game",""))
        team=str(pick.get("ESPN team","")) if pd.notna(pick.get("ESPN team")) else ""
        if live is not None:
            if live["injuries"] is not None:
                flag,status=injury_status(pick["Player"],team,live["injuries"])
            if side:
                game=next((g for g in live["games"] if {g["away"],g["home"]}==set(side)),None)
                if game:
                    if game["state"]=="pre":
                        starting="Unconfirmed (pregame)"
                    elif game["state"] in ("in","post"):
                        known=live["starters"].get(game["id"],set())
                        matched=starter_match(pick["Player"],team,known)
                        if matched is True:
                            starting="Confirmed ESPN starter"
                        elif matched is False:
                            starting="Not an ESPN-confirmed starter"
                        else:
                            starting="Unverified (boxscore or player match incomplete)"
                official=live.get("official_starters",{}).get(frozenset(side))
                if official:
                    verified=starter_match(pick["Player"],team,official["players"])
                    if verified is True:
                        starting="Confirmed NBA official starter"
                    elif verified is False:
                        starting="Not listed in confirmed NBA starting five"
        data.at[idx,"ESPN injury flag"]=flag
        data.at[idx,"ESPN injury status"]=status
        data.at[idx,"Starter verification"]=starting
    st.dataframe(data[["Player","Market","ESPN injury status","Starter verification"]],
                 hide_index=True,use_container_width=True)
    exclude_uncertain=st.checkbox("Exclude ESPN-listed questionable/probable/uncertain players",value=True)
    st.subheader("Opponent defense and pace")
    st.caption("Optional exploratory adjustments from completed ESPN team boxscores. Uses at least five verified opponent games and compares with the observed game subset, not a full-league average.")
    use_matchup=st.checkbox("Apply verified recent pace/defense adjustments where available",value=True,key="lab_matchup_context")
    opponent_for={}
    for idx,pick in data.iterrows():
        teams=parse_game(pick.get("Game",""))
        team=team_key(pick.get("ESPN team","")) if pd.notna(pick.get("ESPN team")) else ""
        if teams and team in teams:
            opponent_for[idx]=teams[0] if teams[1]==team else teams[1]
    if use_matchup and opponent_for:
        with st.spinner("Checking recent completed opponent boxscores..."):
            context=_recent_opponent_context(tuple(sorted(set(opponent_for.values()))))
        for idx,opponent in opponent_for.items():
            row=data.loc[idx]
            adjustment=matchup_adjustment(context["rows"],opponent,row["Market"])
            if adjustment is None or pd.isna(row.get("External games")):
                continue
            data.at[idx,"Huie baseline"]=round(float(row["Huie baseline"])*adjustment["factor"],2)
            data.at[idx,"Baseline margin"]=round(float(data.at[idx,"Huie baseline"])-float(row["Safe line"]),2)
            data.at[idx,"Matchup context"]=f'{opponent} · {adjustment["games"]} games · x{adjustment["factor"]:.3f}'
        if "Matchup context" in data:
            st.dataframe(data[["Player","Market","Matchup context"]].dropna(subset=["Matchup context"]),
                         hide_index=True,use_container_width=True)
        if context["failures"]:
            st.caption(f'{context["failures"]} ESPN game requests were unavailable; incomplete samples were not imputed.')
    elif use_matchup:
        st.caption("Opponent matchup adjustments require unambiguous ESPN player-team matches from External Historical Results; no unidentified team is guessed.")
    st.subheader("Smart Parlay Builder")
    st.info("OVER agreement only: Sam projection > Reference line AND Huie projection > Reference line. Equal-to-line, under-line and missing projections are excluded.")
    leg_count=st.select_slider("Number of legs",options=[2,3,4],value=2)
    recent_filter=st.selectbox("Optional recent-game filter",["Model agreement only (no recent-hit minimum)","At least 2 of 3 recent hits","All 3 recent hits"],index=0)
    require_history=st.checkbox("Require at least 5 verified external games",value=False)
    different_games=st.checkbox("Prefer different matchups",value=True)
    max_parlays=st.slider("Combinations to show",1,15,5)
    st.caption("These filters avoid repeating the same player within one parlay; they do not estimate correlation or odds.")
    overlap_limit=st.slider("Maximum appearances of a player across displayed parlays",1,5,2)
    # The All Player Props Reference line is the ONLY qualifying threshold.
    # Recent form is optional; never override the strict two-model agreement.
    recent_min=[None,2,3][["Model agreement only (no recent-hit minimum)","At least 2 of 3 recent hits","All 3 recent hits"].index(recent_filter)]
    eligible=dual_model_eligible(data,recent_min)
    if exclusions:
        eligible=eligible[~eligible["Player"].astype(str).str.casefold().isin(exclusions)]
    if require_history:
        eligible=eligible[eligible.get("External games",pd.Series(0,index=eligible.index)).fillna(0)>=5]
    if "ESPN injury flag" in eligible:
        eligible=eligible[eligible["ESPN injury flag"]!="block"]
        if exclude_uncertain:
            eligible=eligible[eligible["ESPN injury flag"]!="review"]
    calibration=st.session_state.get("lab_calibration",{})
    eligible["Calibrated probability"]=eligible.apply(
        lambda r:calibrated_predict(r["Huie baseline"],r["Safe line"],
                                    r.get("Historical SD"),calibration.get(r["Market"])),axis=1)
    eligible["Consensus margin"] = eligible[["Baseline margin","Sam margin"]].min(axis=1)
    if eligible["Calibrated probability"].notna().any():
        st.subheader("Validated single-leg probability forecasts")
        probability_view=eligible[["Player","Market","Safe line","Calibrated probability"]].copy()
        probability_view["Calibrated probability"]=probability_view["Calibrated probability"].map(
            lambda p:f"{p:.1%}" if pd.notna(p) else "Not validated")
        st.dataframe(probability_view.rename(columns={"Safe line":"Reference line"}),hide_index=True,use_container_width=True)
    else:
        st.caption("No eligible market has passed the held-out calibration check. Numerical win probabilities and EV are withheld.")
    st.caption(f"{len(eligible)} All Player Props candidates pass both-model-above-Reference-line agreement and the optional filters.")
    # Laplace-smoothed historical hit frequency is descriptive, not a
    # calibrated future probability; use only as a ranking tie-breaker.
    eligible["Observed hit rate"] = eligible.apply(
        lambda x:(x["External hits"]+1)/(x["External games"]+2)
        if pd.notna(x.get("External games")) and x.get("External games",0)>=5
        else ((x["Recent hits"]+1)/(x["Games"]+2)
              if pd.notna(x.get("Recent hits")) and x.get("Games",0)>=3 else float("nan")),axis=1)
    # Consensus edge is normalized so threes and points can be compared.
    eligible["Relative consensus edge"]=(eligible["Consensus margin"]/
                                        eligible["Safe line"].clip(lower=1))
    eligible=eligible.sort_values(["Relative consensus edge","Observed hit rate"],ascending=False,na_position="last").head(24)
    # Cap candidate pool for predictable compute, avoid duplicate players in one parlay.
    combos=[]
    for group in itertools.combinations(eligible.to_dict("records"),leg_count):
        if len({x["Player"] for x in group})!=leg_count:continue
        if different_games and len({x["Game"] for x in group})!=leg_count:continue
        score=sum(float(x["Relative consensus edge"]) for x in group)+sum(float(x["Observed hit rate"]) if pd.notna(x["Observed hit rate"]) else 0.0 for x in group)*0.1
        combos.append((score,group))
    combos.sort(key=lambda item:item[0],reverse=True)
    if not combos:
        st.info("No parlay combinations satisfy the current filters. Try a smaller leg count, turn off the optional recent-hit requirement, or allow shared matchups. Both model projections must still exceed the Reference line.")
        return
    selected=[]
    player_exposure={}
    for _,group in combos:
        if any(player_exposure.get(x["Player"],0)>=overlap_limit for x in group):continue
        selected.append(group)
        for x in group:player_exposure[x["Player"]]=player_exposure.get(x["Player"],0)+1
        if len(selected)>=max_parlays:break
    if not selected:
        st.warning("No combinations meet the cross-parlay player exposure limit.")
        return
    st.subheader("Contract-price comparison")
    st.caption("Automatic quotes can come from an administrator-configured HTTPS source; Robinhood prediction-market quotes are not available through the connected Robinhood integration. A manual YES price and fee may also be entered.")
    quote_url=st.secrets.get("PREDICTION_QUOTES_URL","")
    quote_token=st.secrets.get("PREDICTION_QUOTES_BEARER","")
    external_quotes=[]
    if quote_url:
        try:
            external_quotes=_configured_contract_quotes(str(quote_url),str(quote_token))
            st.caption(f"{len(external_quotes)} fresh, structurally validated YES quotes from configured feed (20-minute maximum age). This does not independently verify the feed provider.")
        except Exception as exc:
            st.warning("Configured quote source unavailable: "+type(exc).__name__+". No quote is assumed.")
    else:
        st.caption("No trusted quotes feed configured in Streamlit Secrets. Prices and actual fees must be entered manually.")
    unique_legs={}
    for group in selected:
        for leg in group:
            key=(leg["Player"],leg["Market"],leg["Safe line"])
            unique_legs[key]=leg
    price_rows=[]
    feed_matches={}
    for key,v in unique_legs.items():
        quote=match_quote(v["Player"],v["Market"],v["Safe line"],external_quotes)
        if quote:feed_matches[key]=quote
        price_rows.append({"Player":v["Player"],"Market":v["Market"],"Reference line":v["Safe line"],
                           "YES price ($)":quote["price"] if quote else None,
                           "Fee / contract ($)":quote["fee"] if quote else None,
                           "Observed hit frequency":round(v["Observed hit rate"],3)})
    price_input=st.data_editor(pd.DataFrame(price_rows),hide_index=True,
                               disabled=["Player","Market","Reference line","Observed hit frequency"],
                               column_config={"YES price ($)":st.column_config.NumberColumn(
                                   "YES price ($)",min_value=0.01,max_value=0.99,step=0.01),
                                   "Fee / contract ($)":st.column_config.NumberColumn(
                                   "Fee / contract ($)",min_value=0.0,max_value=0.99,step=0.01)},
                               use_container_width=True,key="lab_contract_prices")
    entered={}
    for _,row in price_input.iterrows():
        value=row["YES price ($)"]
        if pd.notna(value) and 0<float(value)<1:
            raw_fee=row["Fee / contract ($)"]
            fee=float(raw_fee) if pd.notna(raw_fee) and 0<=float(raw_fee)<1 else None
            entered[(row["Player"],row["Market"],row["Reference line"])]=(float(value),fee)
    if entered:
        comparison=[]
        for key,leg in unique_legs.items():
            if key not in entered:continue
            observed=float(leg["Observed hit rate"])
            price,fee=entered[key]
            p=leg.get("Calibrated probability")
            p=float(p) if pd.notna(p) else None
            threshold=yes_break_even(price,fee) if fee is not None else None
            ev=yes_expected_value(p,price,fee) if p is not None and fee is not None else None
            quote=feed_matches.get(key)
            from_feed=bool(quote and abs(price-quote["price"])<1e-8 and fee is not None
                           and abs(fee-quote["fee"])<1e-8)
            comparison.append({"Player":leg["Player"],"Market":leg["Market"],
                               "Price source":"Configured fresh feed" if from_feed else "Manual entry",
                               "Reference line":leg["Safe line"],"Manual YES price":round(price,3),
                               "Manual fee":round(fee,3) if fee is not None else None,
                               "Price-only break-even":round(price,3),
                               "Break-even incl fee":round(threshold,3) if threshold is not None else None,
                               "Observed frequency":round(observed,3),
                               "Validated single-leg probability":round(p,3) if p is not None else None,
                               "Illustrative EV / $1 contract":round(ev,3) if ev is not None else None})
        st.dataframe(pd.DataFrame(comparison),use_container_width=True,hide_index=True)
        st.warning("Feed quotes are NOT verified live Robinhood prices. Manual overrides are marked. EV is withheld unless BOTH the actual fee and a held-out-validated single-leg probability are available. This is per-contract math, NOT a combo-parlay profit forecast.")
    for idx,group in enumerate(selected,1):
        with st.expander(f"Candidate parlay {idx} · {leg_count} legs",expanded=idx==1):
            for leg in group:
                prob=leg.get("Calibrated probability")
                prob_text=f"{prob:.1%} held-out-calibrated scenario" if pd.notna(prob) else "probability not validated"
                form=f"{int(leg['Recent hits'])}/3" if pd.notna(leg.get("Recent hits")) else "unverified"
                st.write(f"**{leg['Player']} — {leg['Market']} OVER {leg['Safe line']:g}** · Sam {leg['Sam projection']:g} · Huie {leg['Huie baseline']:g} · recent form {form} · {prob_text} · {leg['Game']}")
    st.subheader("Joint parlay probability and uncertainty")
    st.caption("Dependence-aware Fréchet bounds require validated marginal probabilities. Where sufficient overlapping historical game dates exist, an additional shrinkage-correlation simulation is shown as a SCENARIO, not a verified chance to win.")
    historical_raw=st.session_state.get("lab_history_raw",{})
    joint_rows=[]
    for idx,group in enumerate(selected,1):
        probabilities=[x.get("Calibrated probability") for x in group]
        valid=all(pd.notna(p) and 0<float(p)<1 for p in probabilities)
        if valid:
            low,high=joint_bounds([float(p) for p in probabilities])
            scenario=correlated_joint(group,historical_raw) if historical_raw else None
            joint_rows.append({"Parlay":idx,"Legs":len(group),
                               "Joint lower bound":round(low,3),"Joint upper bound":round(high,3),
                               "Correlation scenario":scenario.get("scenario_probability") if scenario else None,
                               "Common historical dates":scenario.get("minimum_common_game_dates") if scenario else None,
                               "Source":"Held-out marginal calibration; paired ESPN history" if scenario else "Held-out marginal calibration; dependence unavailable"})
        else:
            joint_rows.append({"Parlay":idx,"Legs":len(group),
                               "Joint lower bound":None,"Joint upper bound":None,
                               "Correlation scenario":None,"Common historical dates":None,
                               "Source":"Not enough validated historical data"})
    st.dataframe(pd.DataFrame(joint_rows),hide_index=True,use_container_width=True)
    st.warning("A correlation scenario is not a calibrated joint win probability. Where paired history is insufficient, the app does NOT assume independence. Do not interpret these as confirmed positive-EV parlays.")
    st.caption("All Player Props Reference lines only, not Bankroll Builder safe lines. Ranked by normalized two-model consensus and verified form where available, NOT expected value. Injury reports do not guarantee participation and no parlay is labeled profitable.")
