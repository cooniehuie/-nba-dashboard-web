"""Exploratory, read-only parlay builder and independent baseline comparison."""
import itertools
import math
import re
import pandas as pd
import streamlit as st
from parlay_probability import joint_bounds, wilson_interval, yes_break_even, yes_expected_value
from parlay_context import game_day_context, injury_status, parse_game, name_key, team_key, team_context, matchup_adjustment
from parlay_calibration import train as train_probabilities, predict as calibrated_predict
from parlay_joint import correlated_joint
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

def _candidates(df):
    p=_col(df,"Player")
    m=_col(df,"Market","Stat")
    line=_col(df,"Safer line","Safe line")
    game=_col(df,"Game")
    projection=_col(df,"Model projection")
    history=[_col(df,x) for x in ("Last game","2 games ago","3 games ago")]
    history=[x for x in history if x is not None]
    if p is None or line is None: return pd.DataFrame()
    rows=[]
    for _,r in df.iterrows():
        name=str(r[p]).strip()
        target=_num(r[line])
        if not name or name.lower()=="nan" or target is None:continue
        market=str(r[m]).strip().title() if m else ""
        if not market:
            text=str(r[line]).lower()
            market=next((value for token,value in (("assist","Assists"),("rebound","Rebounds"),("three","Threes"),("point","Points")) if token in text),"")
        if market not in ("Points","Rebounds","Assists","Threes"):continue
        values=[_num(r[c]) for c in history]
        values=[v for v in values if v is not None]
        if len(values)<3:continue
        # This is an empirical recent-games baseline, NOT a calibrated win probability.
        hit=sum(v>=target for v in values)
        avg=sum(values)/len(values)
        gap=avg-target
        sam=_num(r[projection]) if projection else None
        rows.append({"Player":name,"Market":market,"Safe line":target,
                     "Game":str(r[game]) if game else "Unknown",
                     "Sam projection":sam,"Huie baseline":round(avg,2),
                     "Recent hits":hit,"Games":len(values),"Recent hit rate":hit/len(values),
                     "Baseline margin":round(gap,2),
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
    st.caption("Optional research fetch of the previous 30 calendar days. Only completed games with recorded player statistics count; unavailable records are not treated as misses.")
    if st.button("Load external historical results",key="lab_fetch_history"):
        st.session_state["lab_history_enabled"]=True
    if not st.session_state.get("lab_history_enabled",False):
        st.session_state.pop("lab_history_results",None)
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
    """Only include over legs when both independent projections exceed line."""
    if data is None or data.empty:return data
    required=["Recent hits","Huie baseline","Safe line","Sam projection"]
    if any(col not in data.columns for col in required):
        return data.iloc[0:0].copy()
    return data[
        (data["Recent hits"]>=minimum_recent_hits)
        & data["Huie baseline"].notna()
        & (data["Huie baseline"]>data["Safe line"])
        & data["Sam projection"].notna()
        & (data["Sam projection"]>data["Safe line"])
    ].copy()

@st.cache_data(ttl=900,show_spinner=False)
def _live_nba_context():
    return game_day_context()

@st.cache_data(ttl=21600,show_spinner=False)
def _recent_opponent_context(opponents):
    return team_context(opponents,days=21,max_per_team=6)

def render(df):
    st.title("🧪 Smart Parlay Builder & Huie's Model Lab")
    st.caption("Research-only combinations using today's saved workbook. No bets are placed, and model accuracy or profitability is not guaranteed.")
    if df is None or df.empty:
        st.info("Upload today's workbook with safe lines and recent game stats to use this feature.")
        return
    data=_candidates(df)
    if data.empty:
        st.warning("No eligible picks. This prototype requires Player, Safer line, Market (or stat named in line), and all three recent game columns.")
        return
    st.subheader("Huie's Model Lab · independent recent-games baseline")
    st.write("Huie's baseline is the average of the last three recorded games, compared with Sam's projection. It does not use Sam's projected value to calculate its own baseline.")
    st.caption("Recent 3-game hit rates are descriptive. External injury, lineup and matchup data are shown only when verified. Calibrated probabilities require a held-out historical check.")
    show=data.sort_values(["Recent hits","Baseline margin"],ascending=False).copy()
    show["Recent hit rate"]=show["Recent hit rate"].map(lambda x:f"{x:.0%}")
    st.dataframe(show,use_container_width=True,hide_index=True)
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
            if rec is None or rec["Completed games"]<5:continue
            # Use an independently calculated minutes-normalized projection
            # when available; otherwise use the historical stat average.
            minutes_based=rec.get("Minutes projection")
            baseline=float(minutes_based) if pd.notna(minutes_based) else float(rec["Historical average"])
            data.at[idx,"Huie baseline"]=baseline
            data.at[idx,"Baseline margin"]=round(baseline-pick["Safe line"],2)
            data.at[idx,"External games"]=int(rec["Completed games"])
            data.at[idx,"External hits"]=int(rec["Hits"])
            data.at[idx,"Historical SD"]=rec.get("Historical SD")
            data.at[idx,"ESPN team"]=rec.get("ESPN team")
    st.subheader("Game-day availability and risk checks")
    st.caption("Manual injury/role review is required: this is not a live injury feed. Excluded players are never used in generated parlays.")
    excluded_text=st.text_area("Exclude players (one per line; injury, minutes limit, or uncertain role)",
                               value="",key="lab_excluded_players",height=80)
    exclusions={x.strip().casefold() for x in excluded_text.splitlines() if x.strip()}
    st.subheader("ESPN injury reports and verified starters")
    st.caption("ESPN injury listings are not a medical clearance. Lineups are labeled confirmed only when an in-progress or completed boxscore explicitly marks the player as a starter.")
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
                        if known and team and team_key(team) in side:
                            if (team_key(team),name_key(pick["Player"])) in known:
                                starting="Confirmed ESPN starter"
                            else:
                                starting="Not confirmed as starter"
                        else:
                            starting="Unverified (boxscore unavailable or team unmatched)"
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
    st.info("Only OVER legs where BOTH Sam's projection and Huie's independent baseline are strictly above the safe line can qualify. Missing projections are excluded.")
    leg_count=st.select_slider("Number of legs",options=[2,3,4],value=2)
    require_three=st.checkbox("Require 3 of last 3 games to hit",value=True)
    require_history=st.checkbox("Require at least 5 verified external games",value=False)
    different_games=st.checkbox("Prefer different matchups",value=True)
    max_parlays=st.slider("Combinations to show",1,15,5)
    st.caption("These filters avoid repeating the same player within one parlay; they do not estimate correlation or odds.")
    overlap_limit=st.slider("Maximum appearances of a player across displayed parlays",1,5,2)
    # Both models MUST project strictly above the safe line. Missing Sam
    # projections are ineligible, rather than silently treated as agreement.
    eligible=dual_model_eligible(data,3 if require_three else 2)
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
        st.dataframe(probability_view,hide_index=True,use_container_width=True)
    else:
        st.caption("No eligible market has passed the held-out calibration check. Numerical win probabilities and EV are withheld.")
    st.caption(f"{len(eligible)} candidates pass the dual-model rule and current availability/history filters.")
    # Laplace-smoothed historical hit frequency is descriptive, not a
    # calibrated future probability; use only as a ranking tie-breaker.
    eligible["Observed hit rate"] = eligible.apply(
        lambda x:(x["External hits"]+1)/(x["External games"]+2)
        if pd.notna(x.get("External games")) and x.get("External games",0)>=5
        else (x["Recent hits"]+1)/(x["Games"]+2),axis=1)
    eligible=eligible.sort_values(["Observed hit rate","Consensus margin"],ascending=False).head(24)
    # Cap candidate pool for predictable compute, avoid duplicate players in one parlay.
    combos=[]
    for group in itertools.combinations(eligible.to_dict("records"),leg_count):
        if len({x["Player"] for x in group})!=leg_count:continue
        if different_games and len({x["Game"] for x in group})!=leg_count:continue
        score=sum(x["Observed hit rate"] for x in group)*10+sum(min(x["Consensus margin"],10) for x in group)
        combos.append((score,group))
    combos.sort(key=lambda item:item[0],reverse=True)
    if not combos:
        st.info("No combinations satisfy the current filters. Try allowing 2/3 recent hits or shared matchups; both projections must still exceed the safe line.")
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
    st.caption("Optional: enter the offered YES price per $1 payout for an individual leg. Prices are not fetched from Robinhood. Observed hit rates are NOT calibrated probabilities; this is a sensitivity check, not a positive-EV recommendation.")
    unique_legs={}
    for group in selected:
        for leg in group:
            key=(leg["Player"],leg["Market"],leg["Safe line"])
            unique_legs[key]=leg
    price_rows=[{"Player":v["Player"],"Market":v["Market"],"Safe line":v["Safe line"],
                 "YES price ($)":None,"Fee / contract ($)":None,
                 "Observed hit frequency":round(v["Observed hit rate"],3)}
                for v in unique_legs.values()]
    price_input=st.data_editor(pd.DataFrame(price_rows),hide_index=True,
                               disabled=["Player","Market","Safe line","Observed hit frequency"],
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
            entered[(row["Player"],row["Market"],row["Safe line"])]=(float(value),fee)
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
            comparison.append({"Player":leg["Player"],"Market":leg["Market"],
                               "Line":leg["Safe line"],"Manual YES price":round(price,3),
                               "Manual fee":round(fee,3) if fee is not None else None,
                               "Price-only break-even":round(price,3),
                               "Break-even incl fee":round(threshold,3) if threshold is not None else None,
                               "Observed frequency":round(observed,3),
                               "Validated single-leg probability":round(p,3) if p is not None else None,
                               "Illustrative EV / $1 contract":round(ev,3) if ev is not None else None})
        st.dataframe(pd.DataFrame(comparison),use_container_width=True,hide_index=True)
        st.warning("Prices/fees are manually entered, not live Robinhood quotes. EV is withheld unless BOTH a fee and a held-out-validated single-leg probability are available. This is per-contract math, NOT a combo-parlay profit forecast.")
    for idx,group in enumerate(selected,1):
        with st.expander(f"Candidate parlay {idx} · {leg_count} legs",expanded=idx==1):
            for leg in group:
                prob=leg.get("Calibrated probability")
                prob_text=f"{prob:.1%} held-out-calibrated scenario" if pd.notna(prob) else "probability not validated"
                st.write(f"**{leg['Player']} — {leg['Market']} {leg['Safe line']:g}+** · {leg['Recent hits']}/3 recent hits · baseline {leg['Huie baseline']:g} · Sam {leg['Sam projection'] if leg['Sam projection'] is not None else 'N/A'} · {prob_text} · {leg['Game']}")
    st.subheader("Joint outcome uncertainty")
    st.caption("These are mathematical bounds only, not estimated parlay win probabilities. The per-leg frequencies are uncalibrated; bounds inherit that limitation. No independence assumption is made.")
    joint_rows=[]
    for idx,group in enumerate(selected,1):
        rates=[float(x["Observed hit rate"]) for x in group]
        lower,upper=joint_bounds(rates)
        joint_rows.append({"Parlay":idx,"Legs":len(rates),
                           "Illustrative lower bound":round(lower,3),
                           "Illustrative upper bound":round(upper,3),
                           "Interpretation":"Not a calibrated probability"})
    st.dataframe(pd.DataFrame(joint_rows),hide_index=True,use_container_width=True)
    st.caption("These bounds use observed frequencies as hypothetical marginals, not calibrated forecasts.")
    st.warning("Actual joint probabilities require validated marginal probabilities and dependence estimates. Do not multiply these frequencies or use these bounds to claim positive expected value.")
    st.caption("Manual injury exclusions are not verified against an official injury report. Ranked by smoothed observed hit frequency and the weaker of the two model margins. These are NOT expected-value rankings: without contract prices, calibrated probabilities and correlation estimates, no parlay can be called favorable or profitable.")
