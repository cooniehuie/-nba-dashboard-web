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
        found = re.search(r"-?\\d+(?:\\.\\d+)?", str(value))
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
    st.subheader("Smart Parlay Builder")
    leg_count=st.select_slider("Number of legs",options=[2,3,4],value=2)
    require_three=st.checkbox("Require 3 of last 3 games to hit",value=True)
    different_games=st.checkbox("Prefer different matchups",value=True)
    max_parlays=st.slider("Combinations to show",1,15,5)
    eligible=data[(data["Recent hits"]>= (3 if require_three else 2)) & (data["Baseline margin"]>=0)].copy()
    eligible=eligible.sort_values(["Recent hits","Baseline margin"],ascending=False).head(24)
    # Cap candidate pool for predictable compute, avoid duplicate players in one parlay.
    combos=[]
    for group in itertools.combinations(eligible.to_dict("records"),leg_count):
        if len({x["Player"] for x in group})!=leg_count:continue
        if different_games and len({x["Game"] for x in group})!=leg_count:continue
        score=sum(x["Recent hits"] for x in group)*10+sum(min(x["Baseline margin"],10) for x in group)
        combos.append((score,group))
    combos.sort(key=lambda item:item[0],reverse=True)
    if not combos:
        st.info("No combinations satisfy the current filters. Try allowing 2/3 recent hits or shared matchups.")
        return
    for idx,(_,group) in enumerate(combos[:max_parlays],1):
        with st.expander(f"Candidate parlay {idx} · {leg_count} legs",expanded=idx==1):
            for leg in group:
                st.write(f"**{leg['Player']} — {leg['Market']} {leg['Safe line']:g}+** · {leg['Recent hits']}/3 recent hits · baseline {leg['Huie baseline']:g} · Sam {leg['Sam projection'] if leg['Sam projection'] is not None else 'N/A'} · {leg['Game']}")
    st.caption("Ranked by recent observed hits and baseline margin only. These are NOT expected-value rankings: without contract prices, calibrated probabilities and correlation estimates, no parlay can be called favorable or profitable.")
