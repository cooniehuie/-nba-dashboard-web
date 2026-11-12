"""Game-scoped, ESPN-confirmed absences for the My Bets live tracker.

Do not infer DNP from missing box-score statistics. Historical injury reports
are not reconstructed from the current injury feed.
"""
import re
import unicodedata
import urllib.request
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st


def _norm(value):
    value=unicodedata.normalize("NFKD",str(value or "")).encode("ascii","ignore").decode("ascii").lower()
    return " ".join(re.sub(r"[^a-z0-9]+"," ",value).split())


def _value(item):
    if isinstance(item,dict):
        return str(item.get("name") or item.get("description") or item.get("displayName") or
                   item.get("abbreviation") or item.get("value") or "")
    return str(item or "")


def _confirmed_out(status,entry=None):
    """Only definitive OUT/inactive statuses, never doubtful or questionable."""
    value=_norm(_value(status))
    tokens=set(value.split())
    if value in ("out","inactive","did not play","dnp","injured reserve","ir","suspended",
                 "out for season","out for game") or "out" in tokens and not any(
                 phrase in value for phrase in ("ruled out of", "not ruled out", "questionable")):
        return True
    entry=entry or {}
    return entry.get("didNotPlay") is True or entry.get("inactive") is True


def _reports(payload,game=None,default_team=None,source="ESPN"):
    """Parse NBA/NFL flat or team-grouped injury and roster entries."""
    if not isinstance(payload,dict):return []
    records=[]
    def add(item,team):
        if not isinstance(item,dict):return
        athlete=item.get("athlete") or item.get("player") or {}
        if not isinstance(athlete,dict):return
        name=athlete.get("displayName") or athlete.get("fullName") or athlete.get("name")
        if not name:return
        status=item.get("status") or item.get("designation") or item.get("reason")
        if not _confirmed_out(status,item):return
        where=item.get("team") or team or {}
        records.append({"name":str(name),"athlete_id":str(athlete.get("id") or ""),
                        "team_id":str(where.get("id") or "") if isinstance(where,dict) else "",
                        "team":str(where.get("abbreviation") or "") if isinstance(where,dict) else "",
                        "status":_value(status) or "DNP", "game":game,"source":source})
    for entry in payload.get("injuries") or []:
        if not isinstance(entry,dict):continue
        if entry.get("athlete") or entry.get("player"):
            add(entry,entry.get("team") or default_team)
        for child in entry.get("injuries") or []:
            add(child,entry.get("team") or default_team)
    for group in payload.get("rosters") or []:
        if not isinstance(group,dict):continue
        team=group.get("team") or default_team
        for item in group.get("roster") or group.get("athletes") or []:
            add(item,team)
    return records


def game_reported_absences(summary,game,sport):
    """In-game, date-specific ESPN summary (safe to use for historical games)."""
    report=_reports(summary,game=game,source="ESPN game summary")
    for team in (summary.get("boxscore") or {}).get("players") or []:
        team_info=team.get("team") or {}
        for group in team.get("statistics") or []:
            for item in group.get("athletes") or []:
                if _confirmed_out(item.get("status") or item.get("reason"),item):
                    report+=_reports({"injuries":[{**item,"team":team_info}]},
                                     game=game,source="ESPN box score")
    return report


@st.cache_data(ttl=120,show_spinner=False)
def current_injury_reports(sport):
    if sport not in ("NBA","NFL"):
        return []
    segment="basketball/nba" if sport=="NBA" else "football/nfl"
    url="https://site.api.espn.com/apis/site/v2/sports/"+segment+"/injuries"
    try:
        request=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (HuieDegenCenter)","Accept":"application/json"})
        with urllib.request.urlopen(request,timeout=10) as response:
            data=json.load(response)
        return _reports(data,source="ESPN injury report")
    except Exception:
        return []


def add_confirmed_absences(games,players,sport,game_reports=None,date_string=None):
    """Append only unique, game-linked out/DNP records not already playing.

    League reports are current-only. If the selected game date differs from
    today's Pacific date, use date-specific summary records instead.
    """
    reports=list(game_reports or [])
    today=datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y%m%d")
    if date_string==today:
        reports.extend(current_injury_reports(sport))
    matching_games={}
    for game in games:
        for code in game.get("team_codes") or []:
            matching_games.setdefault(("abbr",str(code).upper()),[]).append(game)
        for ident in game.get("team_ids") or []:
            matching_games.setdefault(("id",str(ident)),[]).append(game)
    by_key={}
    for person in players:
        key=(str((person.get("game") or {}).get("id") or person.get("game",{}).get("name") or ""),
             _norm(person.get("name")))
        by_key[key]=person
    for report in reports:
        name=_norm(report.get("name"))
        if not name:continue
        candidates=[]
        if report.get("game"):
            candidates=[report["game"]]
        else:
            if report.get("team_id"):
                candidates=matching_games.get(("id",str(report["team_id"])),[])
            if not candidates and report.get("team"):
                candidates=matching_games.get(("abbr",str(report["team"]).upper()),[])
        if len(candidates)!=1:
            continue
        game=candidates[0]
        game_key=str(game.get("id") or game.get("name") or "")
        key=(game_key,name)
        existing=by_key.get(key)
        if existing is not None:
            if any(v is not None for v in (existing.get("stats") or {}).values()):
                continue  # Actual participation overrides an OUT/injury report.
            existing["out"]=True
            existing["absence_source"]=report.get("source","ESPN")
            existing["absence_reason"]=report.get("status","Out")
            existing["dnp"]=game.get("state")=="post" or bool(existing.get("dnp"))
        else:
            person={"name":report["name"],"game":game,"team":report.get("team") or "",
                    "sport":sport,"stats":{},"jersey":"","out":True,
                    "dnp":game.get("state")=="post",
                    "absence_source":report.get("source","ESPN"),
                    "absence_reason":report.get("status","Out")}
            players.append(person)
            by_key[key]=person
    return players


def leg_absence_label(player):
    """Only emit DNP/OUT where the source explicitly confirmed non-participation."""
    if not player:
        return None
    game=player.get("game") or {}
    if player.get("dnp") and game.get("state")=="post":
        return "⚪ DNP (final)"
    if player.get("out"):
        return "⚪ OUT / DNP expected" if game.get("state")!="post" else "⚪ DNP (final)"
    if player.get("dnp"):
        return "⚪ DNP (reported)"
    return None
