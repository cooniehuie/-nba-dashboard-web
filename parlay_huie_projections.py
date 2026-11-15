"""Shared independent Huie projection pipeline for Model Lab and Individual Games.

Only completed ESPN games (or actual uploaded historical stats) enter Huie's
projection. Sam's projection and reference lines are never model features.
"""
from statistics import pstdev

import pandas as pd

from parlay_context import name_key, parse_game, team_key, matchup_adjustment
from parlay_predictive import forecast as predictive_forecast
from parlay_blowout import assessment, minutes_normalized


def _initials(value):
    tokens=name_key(value).split()
    return (tokens[0][:1]+" "+" ".join(tokens[1:])) if len(tokens)>1 else ""


def historical_projection_results(data, history, model_audit):
    """Build player-market results only from unique ESPN player identities."""
    if data is None or data.empty or not history:
        return pd.DataFrame()
    lookup={}
    for (player,team),games in history.items():
        key=_initials(player)
        if key:
            lookup.setdefault(key,[]).append((player,team,games))
    records=[]
    audit=model_audit or {}
    for _,pick in data.iterrows():
        matches=lookup.get(_initials(pick["Player"]),[])
        if len(matches)!=1:
            continue  # Ambiguous names are never silently reassigned.
        player,team,games=matches[0]
        games=sorted(games,key=lambda row:str(row.get("date","")),reverse=True)
        samples=[]
        for game in games:
            stat=(game.get("stats") or {}).get(pick["Market"])
            minutes=(game.get("stats") or {}).get("Minutes")
            if stat is None:continue
            try:stat=float(stat)
            except (TypeError,ValueError):continue
            samples.append((stat,minutes))
        if not samples:continue
        values=[r[0] for r in samples]
        recent=values[:3]
        minutes_baseline=minutes_normalized(list(reversed(games)),pick["Market"])
        projected_minutes,minutes_estimate=minutes_baseline or (None,None)
        adaptive=predictive_forecast(games,pick["Market"])
        validation=audit.get(pick["Market"],{})
        records.append({
            "Player":player,"Market":pick["Market"],"Reference line":pick["Safe line"],
            "Recent three games":min(3,len(recent)),
            "Recent three hits":sum(value>=pick["Safe line"] for value in recent) if len(recent)==3 else None,
            "Recent three average":round(sum(recent)/3,2) if len(recent)==3 else None,
            "Last game":recent[0] if len(recent)>0 else None,
            "2 games ago":recent[1] if len(recent)>1 else None,
            "3 games ago":recent[2] if len(recent)>2 else None,
            "Completed games":len(values),
            "Hits":sum(value>=pick["Safe line"] for value in values),
            "Historical average":round(sum(values)/len(values),2),
            "Historical SD":round(max(.75,pstdev(values[:5])),3) if len(values)>=5 else None,
            "ESPN team":team,
            "Minutes projection":round(minutes_estimate,2) if minutes_estimate is not None else None,
            "Recent minutes":projected_minutes,
            "Adaptive projection":adaptive["projection"] if adaptive else None,
            "Adaptive method":adaptive["method"] if adaptive else "Unavailable",
            "Expected minutes":adaptive["expected_minutes"] if adaptive else None,
            "Minutes trend":adaptive["minutes_signal"] if adaptive else "Unknown",
            "Recent rate change":adaptive["recent_rate_change"] if adaptive else None,
            "Predictive validation":validation.get("status","Insufficient evidence"),
            "Use adaptive":bool(validation.get("enabled",False) and adaptive is not None and
                                adaptive["method"].startswith("Rate ×")),
        })
    return pd.DataFrame(records)


def enrich_huie_projections(data, historical):
    """Apply the SAME model-selection rules across Lab and Individual Games."""
    result=data.copy()
    if result.empty or historical is None or historical.empty:return result
    history=historical.copy()
    history["_key"]=history["Player"].map(_initials)
    history=history[history["_key"]!=""]
    groups=history.groupby(["_key","Market"]).size()
    history=history[history.apply(lambda r:groups.loc[(r["_key"],r["Market"])]==1,axis=1)]
    records={(r["_key"],r["Market"]):r for _,r in history.iterrows()}
    for idx,pick in result.iterrows():
        rec=records.get((_initials(pick["Player"]),pick["Market"]))
        if rec is None or rec["Completed games"]<3:continue
        if rec["Recent three games"]==3:
            result.at[idx,"Recent hits"]=int(rec["Recent three hits"])
            result.at[idx,"Games"]=3
            result.at[idx,"Recent hit rate"]=int(rec["Recent three hits"])/3
            for key in ("Last game","2 games ago","3 games ago"):
                result.at[idx,key]=rec.get(key)
        minutes_based=rec.get("Minutes projection")
        if rec.get("Use adaptive") and pd.notna(rec.get("Adaptive projection")):
            baseline=float(rec["Adaptive projection"])
            source="Validated adaptive minutes × recent stat rate"
            minutes=rec.get("Expected minutes")
        elif rec["Completed games"]>=5 and pd.notna(minutes_based):
            baseline=float(minutes_based)
            source="ESPN historical minutes-normalized fallback"
            minutes=rec.get("Recent minutes")
        else:
            baseline=float(rec["Recent three average"])
            source="ESPN latest 3 completed games (limited)"
            minutes=None
        result.at[idx,"Adaptive candidate"]=rec.get("Adaptive projection")
        result.at[idx,"Expected minutes"]=minutes
        result.at[idx,"ESPN player"]=rec.get("Player")
        result.at[idx,"Minutes trend"]=rec.get("Minutes trend")
        result.at[idx,"Predictive validation"]=rec.get("Predictive validation")
        result.at[idx,"Huie baseline"]=round(baseline,2)
        result.at[idx,"Baseline source"]=source
        result.at[idx,"Baseline margin"]=round(baseline-float(pick["Safe line"]),2)
        result.at[idx,"External games"]=int(rec["Completed games"])
        result.at[idx,"External hits"]=int(rec["Hits"])
        result.at[idx,"Historical SD"]=rec.get("Historical SD")
        result.at[idx,"ESPN team"]=rec.get("ESPN team")
    return result


def opponent_adjusted_projections(data, context_rows):
    """Matchup adjustments require confirmed player team and parsed matchup."""
    result=data.copy()
    if result.empty or not context_rows:return result
    for idx,pick in result.iterrows():
        if pd.isna(pick.get("External games")):continue
        teams=parse_game(pick.get("Game",""))
        team=team_key(pick.get("ESPN team","")) if pd.notna(pick.get("ESPN team")) else ""
        if not teams or team not in teams:continue
        opponent=teams[0] if teams[1]==team else teams[1]
        adjustment=matchup_adjustment(context_rows,opponent,pick["Market"])
        current=pick.get("Huie baseline")
        if adjustment is None or pd.isna(current):continue
        value=round(float(current)*adjustment["factor"],2)
        result.at[idx,"Huie baseline"]=value
        result.at[idx,"Baseline margin"]=round(value-float(pick["Safe line"]),2)
        result.at[idx,"Matchup context"]=(
            f'{opponent} · {adjustment["games"]} games · x{adjustment["factor"]:.3f}')
        result.at[idx,"Baseline source"]=str(pick.get("Baseline source",""))+" + exploratory opponent pace/defense"
    return result


def blowout_adjusted_projections(data, model, enabled=True):
    """Apply validated minute shifts before the page computes edges and sides."""
    result=data.copy()
    if result.empty or model is None:
        return result
    for idx,pick in result.iterrows():
        current=pick.get("Huie baseline")
        minutes=pick.get("Expected minutes")
        context=assessment(model,pick.get("Game"),pick.get("ESPN player"),
                           pick.get("ESPN team"),pick.get("Market"),
                           str(pick.get("Baseline source","")),minutes)
        for key,value in context.items():
            if key!="factor":
                result.at[idx,key]=value
        if not enabled:
            result.at[idx,"Minutes adjustment"]=0.0
            result.at[idx,"Blowout validation"]="Off"
            continue
        if (context["factor"]==1 or pd.isna(current) or pd.isna(minutes)):
            continue
        value=round(float(current)*context["factor"],2)
        result.at[idx,"Huie baseline"]=value
        result.at[idx,"Baseline margin"]=round(value-float(pick["Safe line"]),2)
        result.at[idx,"Expected minutes"]=round(float(minutes)*context["factor"],2)
        result.at[idx,"Baseline source"]=str(pick.get("Baseline source",""))+" + blowout rotation"
    return result
