"""Walk-forward, holdout-tested probability calibration from verified game results.

Historical reference lines used here are synthetic integer alternate lines around
a rolling stat forecast, not historical Robinhood contracts. Validated only for
the available historical sample and market; never equate a 3-game hit rate with P.
"""
import math
from collections import defaultdict
from statistics import mean, pstdev

MARKETS=("Points","Rebounds","Assists","Threes")
CUTS=(-float("inf"),-2.,-1.,-.5,0.,.5,1.,2.,float("inf"))
OFFSETS={"Points":(-4,0,4),"Rebounds":(-2,0,2),"Assists":(-2,0,2),"Threes":(-1,0,1)}
def _sigma(values):
    return max(.75, pstdev(values)) if len(values)>=2 else None
def examples(history):
    """All rolling forecasts use *only* games before the target date."""
    rows=defaultdict(list)
    for (name,team),games in history.items():
        ordered=sorted(games,key=lambda row:row["date"])
        for market in MARKETS:
            valid=[(g["date"],g["stats"][market]) for g in ordered
                   if g.get("stats",{}).get(market) is not None]
            for i in range(5,len(valid)):
                prior=[float(v) for _,v in valid[i-5:i]]
                baseline=mean(prior); sigma=_sigma(prior)
                actual=float(valid[i][1])
                for offset in OFFSETS[market]:
                    line=max(1,round(baseline)+offset)
                    score=(baseline-line)/sigma
                    rows[market].append({"date":valid[i][0],"player":name,"team":team,
                                         "x":score,"y":int(actual>=line)})
    return rows
def bin_index(score):
    for i in range(len(CUTS)-1):
        if CUTS[i]<=score<CUTS[i+1]:return i
    return len(CUTS)-2
def _isotonic(values, weights):
    # Weighted pool-adjacent-violators algorithm, increasing in projection margin.
    blocks=[]
    for i,(value,weight) in enumerate(zip(values,weights)):
        blocks.append([i,i,float(value)*weight,float(weight)])
        while len(blocks)>1 and blocks[-2][2]/blocks[-2][3] > blocks[-1][2]/blocks[-1][3]:
            b=blocks.pop(); a=blocks[-1]
            a[1]=b[1]; a[2]+=b[2]; a[3]+=b[3]
    answer=[0.]*len(values)
    for start,end,total,weight in blocks:
        for i in range(start,end+1): answer[i]=total/weight
    return answer
def train(history, min_holdout=100):
    output={}
    for market,rows in examples(history).items():
        dates=sorted({r["date"] for r in rows})
        if len(dates)<8:continue
        split=dates[max(1,int(len(dates)*.7))]
        earlier=[r for r in rows if r["date"]<split]
        later=[r for r in rows if r["date"]>=split]
        if len(earlier)<120 or len(later)<min_holdout:continue
        hits=[0]*8; counts=[0]*8
        for row in earlier:
            idx=bin_index(row["x"]);hits[idx]+=row["y"];counts[idx]+=1
        # Smooth each cell toward the overall base rate to avoid 0/1 probabilities.
        base=(sum(hits)+1)/(sum(counts)+2)
        raw=[(hits[i]+8*base)/(counts[i]+8) for i in range(8)]
        fitted=_isotonic(raw,[n+8 for n in counts])
        predicted=[fitted[bin_index(r["x"])] for r in later]
        brier=mean([(p-r["y"])**2 for p,r in zip(predicted,later)])
        baseline_brier=mean([(base-r["y"])**2 for r in later])
        output[market]={"calibrated":brier < baseline_brier and len({r["player"] for r in later})>=20,
                        "probabilities":fitted,"train_n":len(earlier),"holdout_n":len(later),
                        "holdout_dates":len({r["date"] for r in later}),
                        "brier":round(brier,4),"naive_brier":round(baseline_brier,4),
                        "line_basis":"synthetic integer alternate lines; NOT historical contracts"}
    return output
def predict(baseline,line,sd,calibration):
    if not calibration or not calibration.get("calibrated"):return None
    try:
        x=(float(baseline)-float(line))/max(.75,float(sd))
        if not math.isfinite(x):return None
        result=float(calibration["probabilities"][bin_index(x)])
        if not .0<=result<=1.:return None
        return result
    except (ValueError,TypeError,KeyError,IndexError,OverflowError):
        return None
