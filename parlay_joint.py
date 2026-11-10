"""Exploratory joint parlay simulation using *observed* paired game residuals.

Never silently replace unknown dependence with zero correlation; if historical
overlap is insufficient, return None and use rigorous Frechet bounds instead.
"""
import math
from statistics import mean
import numpy as np
from parlay_context import name_key
from parlay_probability import joint_bounds

def _find_player(name, history):
    bits=name_key(name).split()
    if len(bits)<2:return None
    matches=[]
    for (full,team),games in history.items():
        tokens=name_key(full).split()
        if tokens==bits or (len(tokens)>1 and tokens[0].startswith(bits[0])
                            and tokens[1:]==bits[1:]):
            matches.append(games)
    return matches[0] if len(matches)==1 else None

def residuals(name,market,history):
    games=_find_player(name,history)
    if not games:return {}
    valid=sorted([(g["date"],float(g["stats"][market])) for g in games
                  if g.get("stats",{}).get(market) is not None])
    return {valid[i][0]:valid[i][1]-mean([v for _,v in valid[i-5:i]])
            for i in range(5,len(valid))}

def correlated_joint(group,history,minimum_overlap=10,n_draws=20000,seed=731):
    """Gaussian-copula *scenario*; not a verified joint win probability."""
    if len(group)<2 or len(group)>6:return None
    probs=[g.get("Calibrated probability") for g in group]
    if any(p is None or not isinstance(p,(float,int)) or not 0<p<1 for p in probs):
        return None
    series=[residuals(g["Player"],g["Market"],history) for g in group]
    if any(not s for s in series):return None
    size=len(group)
    cor=np.eye(size)
    overlaps=[]
    for i in range(size):
        for j in range(i+1,size):
            dates=sorted(set(series[i]).intersection(series[j]))
            if len(dates)<minimum_overlap:return None
            a=np.array([series[i][d] for d in dates],dtype=float)
            b=np.array([series[j][d] for d in dates],dtype=float)
            if np.std(a)<1e-6 or np.std(b)<1e-6:return None
            r=float(np.corrcoef(a,b)[0,1])
            if not math.isfinite(r):return None
            # Limit regression-to-noise from sparse overlapping player games.
            r=max(-.75,min(.75,r*len(dates)/(len(dates)+20)))
            cor[i,j]=cor[j,i]=r
            overlaps.append(len(dates))
    eig,vec=np.linalg.eigh(cor)
    eig=np.maximum(eig,1e-5)
    adjusted=(vec*eig)@vec.T
    std=np.sqrt(np.diag(adjusted))
    adjusted=adjusted/std[:,None]/std[None,:]
    rng=np.random.default_rng(seed)
    observations=rng.multivariate_normal(np.zeros(size),adjusted,size=n_draws)
    from statistics import NormalDist
    threshold=np.array([NormalDist().inv_cdf(float(p)) for p in probs])
    estimate=float(np.mean(np.all(observations<=threshold,axis=1)))
    low,high=joint_bounds(probs)
    # Keep within mathematical bounds despite finite Monte Carlo noise.
    estimate=max(low,min(high,estimate))
    return {"scenario_probability":round(estimate,4),"joint_lower_bound":round(low,4),
            "joint_upper_bound":round(high,4),"minimum_common_game_dates":min(overlaps),
            "simulated_draws":n_draws,"verified_joint_probability":False,
            "assumption":"Gaussian copula with shrinkage and overlapping ESPN game residuals"}
