"""Exploratory, read-only parlay builder and independent baseline comparison."""
import itertools
import math
import re
import pandas as pd
import streamlit as st

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
    if not p or not line: return pd.DataFrame()
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
                                try:return float(str(value).split("-")[0])
                                except (ValueError,TypeError):return None
                            info=athlete.get("athlete",{})
                            players.append({"name":info.get("displayName",info.get("fullName","")),
                                            "team":team.get("team",{}).get("abbreviation",""),
                                            "game":{"state":"post"},
                                            "stats":{"Points":numeric(stat("pts","points")),
                                                     "Rebounds":numeric(stat("reb","rebs","rebounds")),
                                                     "Assists":numeric(stat("ast","assists")),
                                                     "Threes":numeric(stat("3pt","3pm","3-pt"))}})
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
        return
    with st.spinner("Checking recent completed NBA box scores..."):
        try:
            history,failures=_historical_boxscores()
        except Exception as exc:
            st.warning("Historical results could not be retrieved: "+str(exc))
            return
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
        values=[g["stats"].get(pick["Market"]) for g in games]
        values=[float(v) for v in values if v is not None]
        if not values:continue
        output.append({"Player":name,"Market":pick["Market"],"Safe line":pick["Safe line"],
                       "Completed games":len(values),"Hits":sum(v>=pick["Safe line"] for v in values),
                       "Historical average":round(sum(values)/len(values),2),
                       "Sam projection":pick["Sam projection"],
                       "Huie baseline":pick["Huie baseline"]})
    if output:
        st.session_state["lab_history_results"]=pd.DataFrame(output)
        st.dataframe(pd.DataFrame(output),use_container_width=True,hide_index=True)
    else:
        st.info("No unambiguous completed-game records were found for the current candidates.")
    if failures:st.warning(str(failures)+" dates could not be fetched; historical samples are incomplete.")

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
    st.caption("A 3/3 historical hit rate is a three-game observation, NOT a 100% forecast probability. No opponent, minutes, injury, odds or correlation adjustments yet.")
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
            # Historical average is an independent projection baseline.
            data.at[idx,"Huie baseline"]=float(rec["Historical average"])
            data.at[idx,"Baseline margin"]=round(float(rec["Historical average"])-pick["Safe line"],2)
            data.at[idx,"External games"]=int(rec["Completed games"])
            data.at[idx,"External hits"]=int(rec["Hits"])
    st.subheader("Smart Parlay Builder")
    st.info("Only OVER legs where BOTH Sam's projection and Huie's independent baseline are strictly above the safe line can qualify. Missing projections are excluded.")
    leg_count=st.select_slider("Number of legs",options=[2,3,4],value=2)
    require_three=st.checkbox("Require 3 of last 3 games to hit",value=True)
    require_history=st.checkbox("Require at least 5 verified external games",value=False)
    different_games=st.checkbox("Prefer different matchups",value=True)
    max_parlays=st.slider("Combinations to show",1,15,5)
    # Both models MUST project strictly above the safe line. Missing Sam
    # projections are ineligible, rather than silently treated as agreement.
    eligible=data[
        (data["Recent hits"] >= (3 if require_three else 2))
        & (data["Huie baseline"] > data["Safe line"])
        & data["Sam projection"].notna()
        & (data["Sam projection"] > data["Safe line"])
    ].copy()
    if require_history:
        eligible=eligible[eligible.get("External games",pd.Series(0,index=eligible.index)).fillna(0)>=5]
    eligible["Consensus margin"] = eligible[["Baseline margin","Sam margin"]].min(axis=1)
    eligible=eligible.sort_values(["Recent hits","Consensus margin"],ascending=False).head(24)
    # Cap candidate pool for predictable compute, avoid duplicate players in one parlay.
    combos=[]
    for group in itertools.combinations(eligible.to_dict("records"),leg_count):
        if len({x["Player"] for x in group})!=leg_count:continue
        if different_games and len({x["Game"] for x in group})!=leg_count:continue
        score=sum(x["Recent hits"] for x in group)*10+sum(min(x["Consensus margin"],10) for x in group)
        combos.append((score,group))
    combos.sort(key=lambda item:item[0],reverse=True)
    if not combos:
        st.info("No combinations satisfy the current filters. Try allowing 2/3 recent hits or shared matchups; both projections must still exceed the safe line.")
        return
    for idx,(_,group) in enumerate(combos[:max_parlays],1):
        with st.expander(f"Candidate parlay {idx} · {leg_count} legs",expanded=idx==1):
            for leg in group:
                st.write(f"**{leg['Player']} — {leg['Market']} {leg['Safe line']:g}+** · {leg['Recent hits']}/3 recent hits · baseline {leg['Huie baseline']:g} · Sam {leg['Sam projection'] if leg['Sam projection'] is not None else 'N/A'} · {leg['Game']}")
    st.caption("Ranked by recent observed hits and the weaker of the two model margins.  These are NOT expected-value rankings: without contract prices, calibrated probabilities and correlation estimates, no parlay can be called favorable or profitable.")
