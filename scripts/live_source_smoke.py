"""Live provider integration check. Uses only public NBA data, no login or bet writes."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import sys
from parlay_context import (BASE,fetch_json,parse_injuries,scoreboard,game_metrics,
                            game_day_context, nba_live_json, nba_confirmed_starters)

def main():
    today=datetime.now(ZoneInfo("America/Los_Angeles")).date()
    injury=fetch_json(BASE+"/injuries")
    if "injuries" not in injury or not isinstance(injury["injuries"],list):
        raise RuntimeError("Unexpected ESPN injuries schema")
    listing=parse_injuries(injury)
    print(f"ESPN injuries schema verified; parsed {len(listing)} injury listings")
    board=fetch_json(BASE+"/scoreboard?dates="+today.strftime("%Y%m%d"))
    if "events" not in board:raise RuntimeError("ESPN scoreboard missing events")
    games=scoreboard(board)
    print(f"ESPN scoreboard schema verified; {len(games)} games")
    context=game_day_context(today)
    if context["injury_error"] or context["schedule_error"]:
        raise RuntimeError("Game-day source read returned an error")
    print(f"Game-day availability sources retrieved; {len(context['starters'])} ESPN live/final lineup listings")
    example=None
    for offset in range(1,4):
        day=today-timedelta(days=offset)
        past=scoreboard(fetch_json(BASE+"/scoreboard?dates="+day.strftime("%Y%m%d")))
        example=next((g for g in past if g["state"]=="post" and g["id"].isdigit()),None)
        if example:break
    if example:
        summary=fetch_json(BASE+"/summary?event="+example["id"])
        metrics=game_metrics(summary)
        if len(metrics)!=2:
            names=[str(x.get("name","")) for t in (summary.get("boxscore") or {}).get("teams",[])
                   for x in t.get("statistics",[])]
            raise RuntimeError("ESPN final team stats missing pace ingredients; found: "+",".join(sorted(set(names))[:40]))
        print("ESPN final-game pace/defense inputs validated:",metrics)
    else:
        print("No recent completed games available for pace smoke (not a failure)")
    try:
        source=nba_live_json("https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json")
        official=nba_confirmed_starters(source,today)
        print(f"NBA official starter source readable; {len(official)} complete lineups as of check")
    except Exception as exc:
        print("NBA official live starter source unavailable (ESPN fallback remains):",type(exc).__name__)
    print("Live-source verification succeeded")
if __name__=="__main__":
    try:main()
    except Exception as exc:
        print("Live-source verification failed:",type(exc).__name__,str(exc),file=sys.stderr)
        sys.exit(1)
