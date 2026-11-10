"""Conservative probability utilities. No odds or live-data assumptions."""
import math

def wilson_interval(hits, games, z=1.96):
    """95% Wilson interval for a binary historical outcome."""
    if not isinstance(games, int) or not isinstance(hits, int) or games < 1 or hits < 0 or hits > games:
        return None
    p = hits / games
    den = 1 + z*z/games
    center = (p + z*z/(2*games))/den
    half = z*math.sqrt(p*(1-p)/games + z*z/(4*games*games))/den
    return max(0.0, center-half), min(1.0, center+half)

def joint_bounds(probabilities):
    """Frechet bounds; valid for arbitrary dependence given valid marginals."""
    ps = list(probabilities)
    if not ps or any(not isinstance(p, (float, int)) or not math.isfinite(p) or p < 0 or p > 1 for p in ps):
        return None
    return max(0.0, sum(ps) - len(ps) + 1), min(ps)

def yes_break_even(price, fee=0.0):
    """Per-contract cost including fee, assuming $1 gross payout on a win."""
    if not all(isinstance(x, (float, int)) and math.isfinite(x) for x in (price, fee)):
        return None
    if price <= 0 or price >= 1 or fee < 0 or price+fee >= 1:
        return None
    return price + fee

def yes_expected_value(probability, price, fee=0.0):
    """EV per $1 winning contract; only meaningful with calibrated probability."""
    threshold = yes_break_even(price, fee)
    if threshold is None or not isinstance(probability, (float, int)) or not math.isfinite(probability) or not 0 <= probability <= 1:
        return None
    return probability - threshold
