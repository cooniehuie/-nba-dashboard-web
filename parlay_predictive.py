"""Huie's independent, conservative NBA-stat forecasting and walk-forward audit.

Inputs are observed completed ESPN games only, newest/oldest order is normalized
by recorded game date. No Sam projection or betting line enters these forecasts.
"""
from datetime import date
import math

MARKETS=("Points","Rebounds","Assists","Threes")

def _number(v, upper=None):
    try:
        if v is None or isinstance(v, bool):
            return None
        if isinstance(v, str) and ":" in v:
            minutes, seconds=v.strip().split(":")
            n=float(minutes)+float(seconds)/60
        else:
            n=float(v)
        if not math.isfinite(n) or n<0 or (upper is not None and n>upper):
            return None
        return n
    except (TypeError, ValueError):
        return None

def _clip(x, low, high):
    return max(low,min(high,x))

def clean_history(games, market):
    """Date-sort and validate each past performance. Do not impute DNP/missing."""
    if market not in MARKETS:return []
    upper={"Points":100,"Rebounds":60,"Assists":40,"Threes":20}[market]
    valid=[]
    for item in games or []:
        if not isinstance(item,dict) or not isinstance(item.get("stats"),dict):
            continue
        try:
            day=date.fromisoformat(str(item["date"]))
        except (KeyError,TypeError,ValueError):
            continue
        stats=item["stats"]
        value=_number(stats.get(market),upper)
        if value is None:continue
        minutes=_number(stats.get("Minutes"),53)
        if minutes is not None and minutes<5:
            minutes=None
        valid.append({"date":day.isoformat(),"stat":value,"minutes":minutes})
    return sorted(valid,key=lambda x:x["date"],reverse=True)

def forecast(games,market):
    """Fixed-parameter forecast: conservative recent role + rate with a long anchor.

    Last 4 valid-minute games are blended with up to 10 completed games.
    Minutes trends and rate changes are capped; no bookmaker values enter.
    """
    obs=clean_history(games,market)
    n=len(obs)
    if n<3:return None
    short=obs[:min(10,n)]
    latest=obs[:3]
    simple=sum(x["stat"] for x in obs[:5])/min(5,n)
    if n<6:
        return {"projection":round(sum(x["stat"] for x in latest)/3,2),
                "method":"Observed last-three mean (limited sample)",
                "games":n,"expected_minutes":None,"minutes_signal":"Unknown",
                "recent_rate_change":None}
    valid=[x for x in short if x["minutes"] is not None and x["minutes"]>=8]
    if len(valid)<5:
        # No reliable minute-rate estimate; do not claim a minute adjustment.
        early=sum(x["stat"] for x in obs[:3])/3
        long=sum(x["stat"] for x in short)/len(short)
        return {"projection":round(.55*early+.45*long,2),
                "method":"Recency-shrunk form (minutes unavailable)",
                "games":n,"expected_minutes":None,"minutes_signal":"Unknown",
                "recent_rate_change":None}

    recent=valid[:min(4,len(valid))]
    long=valid[:min(10,len(valid))]
    total_minutes=sum(x["minutes"] for x in long)
    rate_long=sum(x["stat"] for x in long)/total_minutes
    rate_recent=sum(x["stat"] for x in recent)/sum(x["minutes"] for x in recent)
    # Prevent single-game hot streaks from overwhelming the longer observed rate.
    recent_capped=_clip(rate_recent,.75*rate_long,1.25*rate_long) if rate_long>0 else 0.0
    rate=.55*rate_long+.45*recent_capped

    long_minutes=sum(x["minutes"] for x in long)/len(long)
    recent_minutes=sum(x["minutes"] for x in recent)/len(recent)
    expected=.65*recent_minutes+.35*long_minutes
    expected=_clip(expected,.82*long_minutes,1.18*long_minutes)
    expected=_clip(expected,8.0,42.0)
    calculated=rate*expected
    # Hard safety guard against extreme, unstable extrapolation.
    if simple>0:
        calculated=_clip(calculated,.72*simple,1.28*simple)
    role_ratio=recent_minutes/long_minutes if long_minutes else 1
    signal=("Rising minutes" if role_ratio>=1.12
            else "Falling minutes" if role_ratio<=.88 else "Stable minutes")
    rate_change=rate_recent/rate_long-1 if rate_long>0 else None
    return {"projection":round(calculated,2),
            "method":"Rate × projected minutes (recency-shrunk)",
            "games":n,"expected_minutes":round(expected,1),
            "minutes_signal":signal,
            "recent_rate_change":round(rate_change,3) if rate_change is not None else None}

def audit(history,minimum_examples=45,minimum_dates=4):
    """Fixed-formula, chronological next-game comparison against a five-game mean.

    Uses only games strictly earlier than each evaluated game. The recent
    evaluation window is observational, not a guarantee of future improvement.
    """
    by_market={m:[] for m in MARKETS}
    for games in (history or {}).values():
        for market in MARKETS:
            series=clean_history(games,market)
            chronological=list(reversed(series))
            for i in range(8,len(chronological)):
                prior=chronological[:i]
                actual=chronological[i]["stat"]
                evaluated=forecast([{"date":x["date"],"stats":{
                    market:x["stat"],"Minutes":x["minutes"]}} for x in prior],market)
                if evaluated is None or "Rate × projected minutes" not in evaluated["method"]:
                    continue
                simple=sum(x["stat"] for x in prior[-5:])/5
                by_market[market].append({"date":chronological[i]["date"],
                    "simple_error":abs(actual-simple),
                    "adaptive_error":abs(actual-evaluated["projection"])})
    result={}
    for market,rows in by_market.items():
        dates=sorted({row["date"] for row in rows})
        if not dates:continue
        # Evaluate the most recent 30% of observed dates, chronologically later.
        hold_dates=set(dates[max(0,len(dates)-max(minimum_dates,math.ceil(len(dates)*.30))):])
        held=[row for row in rows if row["date"] in hold_dates]
        if not held:continue
        simple_mae=sum(r["simple_error"] for r in held)/len(held)
        adaptive_mae=sum(r["adaptive_error"] for r in held)/len(held)
        enough=len(held)>=minimum_examples and len(hold_dates)>=minimum_dates
        passed=enough and adaptive_mae<=simple_mae*.985
        result[market]={"evaluated_games":len(held),
                        "evaluation_dates":len(hold_dates),
                        "five_game_mae":round(simple_mae,3),
                        "adaptive_mae":round(adaptive_mae,3),
                        "observed_improvement_pct":round(100*(simple_mae-adaptive_mae)/simple_mae,1)
                                                  if simple_mae else None,
                        "enabled":bool(passed),
                        "status":("Adaptive enabled" if passed else
                                  "Insufficient evidence" if not enough else
                                  "5-game baseline retained")}
    return result
