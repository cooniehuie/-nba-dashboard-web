"""Independent pregame NBA rotation risk from final ESPN games only.

Everything used to predict a slate is frozen at the start of its Pacific date.
Neither Sam's numbers, market spreads, nor results from that date are features.
"""
from collections import Counter, defaultdict
from datetime import date
from math import ceil, isfinite

from parlay_context import parse_game, team_key
from parlay_predictive import forecast, MARKETS

MINUTES_CAP = 3.5
FAMILIES = ("Minutes-normalized", "Adaptive")
ROLES = ("Starter", "Rotation", "Deep bench")


def _num(value):
    try:
        if value is None or isinstance(value, bool):
            return None
        x = float(value)
        return x if isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _seconds(clock):
    try:
        pieces = str(clock).split(":")
        if len(pieces) == 2:
            mm, ss = pieces
            return int(mm) * 60 + float(ss)
        return float(clock)
    except (ValueError, TypeError):
        return None


def espn_rotation_game(event, summary, day):
    """Record lopsided fourth quarters with observed starter exits, not final margin."""
    if (event.get("season") or {}).get("type") != 2:
        return None
    c = (event.get("competitions") or [{}])[0]
    info = {t.get("homeAway"): t for t in c.get("competitors") or []}
    home, away = info.get("home", {}), info.get("away", {})
    home_team = team_key((home.get("team") or {}).get("abbreviation"))
    away_team = team_key((away.get("team") or {}).get("abbreviation"))
    home_score, away_score = _num(home.get("score")), _num(away.get("score"))
    if not (home_team and away_team and home_team != away_team and
            home_score is not None and away_score is not None and home_score != away_score):
        return None
    starters = set()
    coverage = []
    for team in (summary.get("boxscore") or {}).get("players") or []:
        group = {str((a.get("athlete") or {}).get("id") or "")
                 for stat in team.get("statistics") or []
                 for a in stat.get("athletes") or []
                 if a.get("starter") is True and a.get("didNotPlay") is not True}
        group.discard("")
        coverage.append(len(group))
        starters.update(group)
    plays = summary.get("plays") or []
    q4 = []
    periods = []
    for p in plays:
        period = (p.get("period") or {}).get("number")
        if not isinstance(period, int):
            continue
        periods.append(period)
        if period != 4:
            continue
        clock = _seconds((p.get("clock") or {}).get("displayValue"))
        h, a = _num(p.get("homeScore")), _num(p.get("awayScore"))
        if clock is not None and 0 <= clock <= 720 and h is not None and a is not None:
            q4.append((clock, h - a, p))
    # A partial feed is unknown, not a competitive game.
    label = None
    overtime = bool(periods and max(periods) > 4)
    if (len(q4) >= 30 and q4[0][0] >= 690 and q4[-1][0] <= 1 and
            all(x[0] >= y[0] for x, y in zip(q4, q4[1:])) and sorted(coverage) == [5, 5]):
        if overtime:
            label = False
        else:
            label = _rotation_blowout(q4, starters)
    return {"id": str(event["id"]), "date": day, "home": home_team, "away": away_team,
            "home_win": home_score > away_score, "blowout": label, "overtime": overtime,
            "neutral": c.get("neutralSite") is True}


def _rotation_blowout(q4, starters):
    # Detect a large fourth-quarter lead that persists. If substitutions are
    # not observable in an otherwise lopsided game, leave its label unknown.
    had_candidate = False
    for i, (clock, gap, _) in enumerate(q4):
        if not 120 <= clock <= 480:
            continue
        threshold = 20 if clock > 240 else 17 if clock > 180 else 15
        if abs(gap) < threshold:
            continue
        sign = 1 if gap > 0 else -1
        later = q4[i:]
        if any(c > 60 and sign * margin < 10 for c, margin, _ in later):
            continue
        had_candidate = True
        exits = set()
        usable = 0
        # Allow bench changes just before the lead crosses the threshold.
        for c, margin, play in q4:
            if c > clock + 45 or (play.get("type") or {}).get("text") != "Substitution":
                continue
            players = [str((p.get("athlete") or {}).get("id") or "")
                       for p in play.get("participants") or []]
            if len(players) != 2 or not all(players):
                continue
            usable += 1
            entering, leaving = players  # ESPN substitution order
            exits.discard(entering)
            if c >= 60 and sign * margin >= 10 and leaving in starters:
                exits.add(leaving)
        if usable >= 3 and len(exits) >= 2:
            return True
    return None if had_candidate else False


def _edge(ratings, home, away, neutral=False):
    return ratings.get(home, 1500) - ratings.get(away, 1500) + (0 if neutral else 60)


def _band(edge):
    return sum(abs(edge) >= boundary for boundary in (60, 120, 185))


def _probability(model, home, away, neutral=False):
    if min(model["team_games"].get(home, 0), model["team_games"].get(away, 0)) < 5:
        return None
    cell = model["bins"].get(_band(_edge(model["ratings"], home, away, neutral)), (0, 0))
    total = model["labeled"]
    if total[0] < 40 or cell[0] < 8:
        return None
    # Shrink thin rating bands toward the historical league blowout rate.
    return (cell[1] + 15 * total[1] / total[0]) / (cell[0] + 15)


def _matchup(game):
    if not isinstance(game, str):
        return None
    import re
    # "vs" has ambiguous home/away orientation, so only accept explicit
    # away-at-home source labels (the workbook's normal format).
    if not re.search(r"@|\bat\b",game,re.I):
        return None
    teams = parse_game(game)
    return tuple(team_key(t) for t in teams) if teams and teams[0] != teams[1] else None


def _playing(rows):
    return [r for r in rows if (m := _num((r.get("stats") or {}).get("Minutes"))) is not None and 0 < m <= 53]


def _role(rows):
    recent = rows[-5:]
    starters = [r["starter"] for r in recent if type(r.get("starter")) is bool]
    if len(recent) < 4 or len(starters) < 4:
        return None
    mean = sum(float(r["stats"]["Minutes"]) for r in recent) / len(recent)
    if sum(starters) / len(starters) >= .6:
        return "Starter"
    return "Deep bench" if mean < 15 else "Rotation"


def _reference_probability(rows, game_probs):
    values = [game_probs.get(str(r.get("event_id") or "")) for r in rows[-5:]]
    values = [p for p in values if p is not None]
    return sum(values) / len(values) if len(values) >= 3 else None


def _effect(effects, team, role):
    regular, lopsided = (effects.get(("*", role, lab), (0, 0)) for lab in (False, True))
    if min(regular[0], lopsided[0]) < 20:
        return None
    league = lopsided[1] / lopsided[0] - regular[1] / regular[0]
    normal, blowout = (effects.get((team, role, lab), (0, 0)) for lab in (False, True))
    count = min(normal[0], blowout[0])
    if count >= 4:
        local = blowout[1] / blowout[0] - normal[1] / normal[0]
        weight = count/(count+24)
        league = league*(1-weight)+local*weight
    return max(-8, min(8, league))


def _delta(prob, reference, effect, minutes):
    return max(max(1-minutes, -MINUTES_CAP), min(min(48-minutes, MINUTES_CAP), (prob-reference)*effect))


def _base(rows, market, family):
    if family == "Adaptive":
        candidate = forecast(rows, market)
        if candidate and candidate["method"].startswith("Rate ×"):
            return candidate["expected_minutes"], candidate["projection"]
        return None
    with_stat = [r for r in rows if _num((r.get("stats") or {}).get(market)) is not None]
    return minutes_normalized(with_stat, market)


def minutes_normalized(rows, market):
    """Use the same minutes-normalized baseline in evaluation and production."""
    observations = [(float(r["stats"]["Minutes"]), _num(r["stats"].get(market)))
                    for r in _playing(rows)]
    observations = [(m, s) for m, s in observations if s is not None]
    rates = [s / m for m, s in observations if m >= 5]
    if len(rates) < 5 or len(observations) < 5:
        return None
    expected = sum(m for m, _ in observations[-5:]) / 5
    return expected, round(expected * sum(rates) / len(rates), 2)


def _add(mapping, key, amount):
    n, total = mapping.get(key, (0, 0))
    mapping[key] = n + 1, total + amount


def _audit(errors):
    audit = {}
    for (family, market), examples in sorted(errors.items()):
        dates = sorted({x[0] for x in examples})
        holdout = set(dates[-max(4, ceil(len(dates)*.3)):])
        held = [x for x in examples if x[0] in holdout]
        if not held:
            continue
        n = len(held)
        mins_base, mins_new, base, adjusted = [sum(x[i] for x in held)/n for i in range(1, 5)]
        sufficient = n >= 45 and len(holdout) >= 4
        improved = sufficient and base > 0 and adjusted <= base * .99 and mins_new < mins_base
        audit[family, market] = {"sample": n, "dates": len(holdout),
                                 "base": round(base, 3), "adjusted": round(adjusted, 3),
                                 "minutes_base": round(mins_base, 3),
                                 "minutes_adjusted": round(mins_new, 3),
                                 "enabled": improved,
                                 "status": "Validated" if improved else
                                           "Baseline retained" if sufficient else "Insufficient history"}
    return audit


def fit(history, games, as_of):
    """Walk forward by date, learning a risk model and residual minutes effects.

    Player history and ratings are updated only after every game on that date
    has been evaluated. The same estimator is applied to upcoming matchups.
    """
    cutoff = date.fromisoformat(str(as_of)).isoformat()
    game_by_id = {g["id"]: g for g in games if g["date"] < cutoff}
    daily_games = defaultdict(list)
    daily_players = defaultdict(list)
    for g in game_by_id.values():
        daily_games[g["date"]].append(g)
    for (name, team), rows in history.items():
        for r in _playing(rows):
            if r["date"] < cutoff:
                daily_players[r["date"]].append(((name, team_key(team)), r))
    model = {"ratings": {}, "team_games": Counter(), "bins": {}, "labeled": (0, 0),
             "effects": {}, "history": {}, "game_probs": {}, "audit": {}}
    outcomes = defaultdict(list)
    player_rows = defaultdict(list)
    for day in sorted(daily_games.keys() | daily_players.keys()):
        # Compute same-day predictions using only information from earlier dates.
        for g in daily_games[day]:
            prob = _probability(model, g["home"], g["away"], g["neutral"])
            if prob is not None:
                model["game_probs"][g["id"]] = prob
        update_effects = []
        staged = []
        for key, row in daily_players[day]:
            prior = player_rows[key]
            staged.append((key, row))
            g = game_by_id.get(str(row.get("event_id") or ""))
            if not g or g["overtime"] or row.get("exit_flag"):
                continue
            role = _role(prior)
            if role is None:
                continue
            team = key[1]
            if team not in (g["home"], g["away"]):
                continue
            risk = model["game_probs"].get(g["id"])
            prior_risk = _reference_probability(prior, model["game_probs"])
            effect = _effect(model["effects"], team, role)
            actual = float(row["stats"]["Minutes"])
            label = g["blowout"]
            if isinstance(label, bool):
                expected = sum(float(r["stats"]["Minutes"]) for r in prior[-5:]) / len(prior[-5:])
                update_effects.append((team, role, label, max(-12, min(12, actual - expected))))
            if risk is None or prior_risk is None or effect is None:
                continue
            for market in MARKETS:
                stat = _num(row["stats"].get(market))
                if stat is None:
                    continue
                for family in FAMILIES:
                    base = _base(prior, market, family)
                    if not base:
                        continue
                    minutes, projection = base
                    changed_minutes = minutes + _delta(risk, prior_risk, effect, minutes)
                    adjusted = projection * changed_minutes / minutes
                    outcomes[family, market].append((day, abs(minutes-actual),
                                                     abs(changed_minutes-actual), abs(projection-stat),
                                                     abs(adjusted-stat)))
        for key, row in staged:
            player_rows[key].append(row)
        for team, role, label, residual in update_effects:
            _add(model["effects"], (team, role, label), residual)
            _add(model["effects"], ("*", role, label), residual)
        moves = Counter()
        for g in daily_games[day]:
            home, away = g["home"], g["away"]
            edge = _edge(model["ratings"], home, away, g["neutral"])
            count, wins = model["labeled"]
            if isinstance(g["blowout"], bool):
                _add(model["bins"], _band(edge), int(g["blowout"]))
                model["labeled"] = (count + 1, wins + int(g["blowout"]))
            expected = 1 / (1 + 10 ** (-edge / 400))
            move = 24 * (int(g["home_win"]) - expected)
            moves[home] += move
            moves[away] -= move
            model["team_games"].update((home, away))
        for team, move in moves.items():
            model["ratings"][team] = model["ratings"].get(team, 1500) + move
    model["history"] = dict(player_rows)
    model["audit"] = _audit(outcomes)
    return model


def assessment(model, game, player, team, market, method, minutes):
    """Return explanatory columns and a factor applied only after validation."""
    sides = _matchup(game)
    out = {"Blowout risk": None, "Minutes adjustment": None,
           "Blowout role": "Unverified", "Blowout validation": "Insufficient history",
           "factor": 1.0}
    if not sides:
        return out
    away, home = sides
    risk = _probability(model, home, away)
    if risk is None:
        return out
    out["Blowout risk"] = risk
    team = team_key(team)
    if team not in sides or not player:
        return out
    rows = model["history"].get((str(player).casefold(), team), [])
    role = _role(rows)
    if role is None:
        return out
    out["Blowout role"] = role
    if method.startswith("Validated adaptive"):
        family = "Adaptive"
    elif method.startswith("ESPN historical minutes-normalized"):
        family = "Minutes-normalized"
    else:
        out["Blowout validation"] = "Minutes unavailable"
        return out
    minutes = _num(minutes)
    if minutes is None or not 1 <= minutes <= 48:
        return out
    prior_risk = _reference_probability(rows, model["game_probs"])
    effect = _effect(model["effects"], team, role)
    evidence = model["audit"].get((family, market), {})
    if not evidence.get("enabled"):
        out["Blowout validation"] = evidence.get("status", "Insufficient history")
        out["Minutes adjustment"] = 0.0
        return out
    if prior_risk is None or effect is None:
        return out
    delta = _delta(risk, prior_risk, effect, minutes)
    out["Minutes adjustment"] = round(delta, 2)
    out["Blowout validation"] = "Validated"
    out["factor"] = (minutes + delta) / minutes
    return out


def audit_rows(model):
    return [
        {"Baseline": family, "Market": market, "Held-out forecasts": row["sample"],
         "Dates": row["dates"], "Stat MAE before": row["base"], "Stat MAE after": row["adjusted"],
         "Minutes MAE before": row["minutes_base"], "Minutes MAE after": row["minutes_adjusted"],
         "Status": row["status"]}
        for (family, market), row in model.get("audit", {}).items()
    ]
