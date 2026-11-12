"""NFL player workload and opponent defensive adjustments for Huie's projections.

Experimental heuristics rather than trained probabilities. All inputs are verified
2026 ESPN game logs and opponent team statistics. No private betting data is used.
"""
import math
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import streamlit as st

# Market-specific player opportunities, taken from ESPN weekly game logs.
USAGE={
    "Passing yards":"Pass attempts",
    "Rushing yards":"Rush attempts",
    "Receiving yards":"Targets",
    "Receptions":"Targets",
}
# Actual opponent offensive production allowed by the chosen defense.
DEFENSE={
    "Passing yards":("passing","passingYardsPerGame"),
    "Rushing yards":("rushing","rushingYardsPerGame"),
    "Receiving yards":("receiving","receivingYardsPerGame"),
    "Receptions":("receiving","receptions"),
}
MAX_DEFENSE_CHANGE=.12
MAX_USAGE_CHANGE=.18


def numeric(x):
    try:
        if x is None or isinstance(x,bool):return None
        result=float(x)
        return result if math.isfinite(result) else None
    except (ValueError,TypeError):
        return None


def projection_from_usage(games,market,baseline):
    """Use a player's observed volume × season efficiency, blended with baseline.

    Missing game log stats are never assumed to be 0. Recent usage receives a
    slight recency emphasis while season-to-date efficiency stays stable.
    """
    usage_key=USAGE.get(market)
    if not usage_key or baseline is None:
        return {"estimate":baseline,"volume":None,"trend":None,"observations":0,
                "notes":"Baseline only"}
    pairs=[]
    for game in games:
        stats=game.get("stats") or {}
        qty=numeric(stats.get(usage_key))
        val=numeric(stats.get(market))
        if qty is not None and val is not None and qty>=0:
            pairs.append((qty,val))
    if len(pairs)<3 or sum(qty for qty,_ in pairs)<3:
        return {"estimate":baseline,"volume":None,"trend":None,"observations":len(pairs),
                "notes":"Usage unavailable"}
    season_qty=statistics.mean(qty for qty,_ in pairs)
    q=[qty for qty,_ in pairs[-3:]]
    recent_qty=.55*q[-1]+.30*q[-2]+.15*q[-3]
    weight=.65 if len(pairs)>=6 else .4
    expected_qty=max(0,weight*recent_qty+(1-weight)*season_qty)
    # Rate is measured on actual opportunities rather than per-game averaging.
    season_eff=sum(val for _,val in pairs)/max(1,sum(qty for qty,_ in pairs))
    if not math.isfinite(season_eff):
        return {"estimate":baseline,"volume":None,"trend":None,"observations":len(pairs),
                "notes":"Usage unavailable"}
    # For receptions, conversion is limited to one catch per target.
    if market=="Receptions":
        season_eff=max(0,min(1,season_eff))
    direct=max(0,expected_qty*season_eff)
    # Do not allow a small or noisy usage sample to dominate the player model.
    blended=.65*baseline+.35*direct
    upper=baseline*(1+MAX_USAGE_CHANGE) if baseline>0 else direct*.35
    lower=max(0,baseline*(1-MAX_USAGE_CHANGE))
    result=max(lower,min(upper,blended))
    trend=(recent_qty/season_qty-1) if season_qty>0 else None
    return {"estimate":round(result,2),"volume":round(expected_qty,1),
            "trend":round(trend*100,1) if trend is not None else None,
            "observations":len(pairs),"notes":"Verified workload × season efficiency"}


def _stats_per_game(result):
    """Extract *allowed*, not the listed team's offensive production."""
    sections=result.get("results",{}).get("opponent") or []
    if not isinstance(sections,list):return {}
    by_category={str(cat.get("name")):{str(s.get("name")):numeric(s.get("value"))
                                       for s in cat.get("stats") or []}
                 for cat in sections if isinstance(cat,dict)}
    games=(by_category.get("passing") or {}).get("teamGamesPlayed") or (
        by_category.get("rushing") or {}).get("teamGamesPlayed")
    if not games or games<1:return {}
    gp=int(games)
    out={"games":gp}
    for market,(category,stat) in DEFENSE.items():
        value=(by_category.get(category) or {}).get(stat)
        if value is None:continue
        # ESPN marks these as explicit per-game values. Receptions is a total.
        if stat=="receptions":
            value=value/gp
        out[market]=float(value)
    rush=(by_category.get("rushing") or {}).get("rushingTouchdowns")
    rec=(by_category.get("receiving") or {}).get("receivingTouchdowns")
    if rush is not None:
        out["Rushing TD allowed"]=rush/gp
    if rec is not None:
        out["Receiving TD allowed"]=rec/gp
    return out


@st.cache_data(ttl=3600,show_spinner=False)
def league_defensive_snapshot(season):
    """Only for *upcoming* games: ESPN live team season stats are not dated
    snapshots and therefore cannot safely be used for historical backtests.
    """
    from huie_nfl_projections import SITE,_fetch
    listing=_fetch(SITE+"teams?limit=40")
    sports=listing.get("sports") or []
    teams=(sports[0].get("leagues") or [{}])[0].get("teams") or [] if sports else []
    ids={str((t.get("team") or {}).get("id") or ""):str((t.get("team") or {}).get("abbreviation") or "")
         for t in teams if str((t.get("team") or {}).get("id") or "").isdigit()}
    if len(ids)<24:
        return {"teams":{},"league":{},"total":len(ids),"coverage":0}
    data={}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures={pool.submit(_fetch,SITE+"teams/"+team_id+"/statistics?season="+str(season)):team_id for team_id in ids}
        for fut in as_completed(futures):
            team_id=futures[fut]
            try:
                parsed=_stats_per_game(fut.result())
                if parsed.get("games",0)>=3:
                    data[team_id]=parsed
            except Exception:
                continue
    league={}
    keys=list(DEFENSE)+["Rushing TD allowed","Receiving TD allowed"]
    for key in keys:
        weighted=[(entry[key],entry["games"]) for entry in data.values() if key in entry]
        if len(weighted)>=24:
            denom=sum(n for _,n in weighted)
            league[key]=sum(v*n for v,n in weighted)/denom if denom else None
    return {"teams":data,"league":league,"total":len(ids),"coverage":len(data)}


def defense_adjustment(snapshot,team_id,market,position):
    """Shrunk, capped opponent-strength multiplier, not a claimed win probability."""
    if not snapshot or snapshot.get("coverage",0)<24:
        return {"factor":1.0,"label":"Unavailable","defense_allowed":None,
                "league_allowed":None,"sample":0}
    team=(snapshot.get("teams") or {}).get(str(team_id)) or {}
    league=snapshot.get("league") or {}
    if market=="Anytime TD":
        # A QB's rushing score and a RB's rushing/receiving scores use rushing
        # and/or receiving TD allowed. WR and TE use receiving TDs allowed.
        keys=(("Rushing TD allowed",) if position=="QB" else
              ("Receiving TD allowed",) if position in ("WR","TE") else
              ("Rushing TD allowed","Receiving TD allowed"))
        components=[]
        for key in keys:
            own=numeric(team.get(key));typical=numeric(league.get(key))
            if own is not None and typical and typical>0:
                components.append((own,typical))
        if not components:
            return {"factor":1.0,"label":"Unavailable","defense_allowed":None,
                    "league_allowed":None,"sample":team.get("games",0)}
        # RB averages both scoring avenues; no claim about unmeasured red-zone share.
        defense_avg=statistics.mean(v for v,_ in components)
        league_avg=statistics.mean(v for _,v in components)
    else:
        defense_avg=numeric(team.get(market))
        league_avg=numeric(league.get(market))
    if defense_avg is None or not league_avg or league_avg<=0:
        return {"factor":1.0,"label":"Unavailable","defense_allowed":None,
                "league_allowed":None,"sample":team.get("games",0)}
    games=int(team.get("games") or 0)
    # Strength-of-schedule/variance mean reversion: only one-third of observed
    # defensive deviation is used, never beyond +/-12%.
    deviation=(defense_avg/league_avg)-1
    confidence=min(1.0,games/8)
    delta=max(-MAX_DEFENSE_CHANGE,min(MAX_DEFENSE_CHANGE,deviation*.30*confidence))
    return {"factor":round(1+delta,4),
            "label":"Favorable" if delta>.015 else "Tough" if delta<-.015 else "Neutral",
            "defense_allowed":round(defense_avg,1),
            "league_allowed":round(league_avg,1),"sample":games}


def anytime_touchdown_probability(games):
    """Beta(1,1) smoothed empirical P(>=1 rushing/receiving TD), not sportsbook odds."""
    vals=[numeric(g.get("stats",{}).get("Anytime TD")) for g in games]
    vals=[v for v in vals if v is not None]
    if len(vals)<3:return None
    wins=sum(x>=1 for x in vals)
    return round(100*(wins+1)/(len(vals)+2),1)


def apply_context(baseline,games,market,position,defense_snapshot=None,opponent_id=None):
    """Combine individual baseline, verified usage and league-normalized defense."""
    volume=projection_from_usage(games,market,baseline)
    adjusted=volume["estimate"] if volume["estimate"] is not None else baseline
    defense=defense_adjustment(defense_snapshot,opponent_id,market,position)
    final=max(0,adjusted*defense["factor"]) if adjusted is not None else None
    return {"final":round(final,2) if final is not None else None,
            "usage":volume,"defense":defense,
            "td_probability":anytime_touchdown_probability(games) if market=="Anytime TD" else None}
