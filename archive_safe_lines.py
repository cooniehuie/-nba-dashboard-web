"""Scheduled safe-line archive. Reuses the dashboard's grading functions without running its UI."""
import ast
import base64
import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd

TOKEN=os.environ.get("GITHUB_STORAGE_TOKEN","")
REPO=os.environ.get("GITHUB_STORAGE_REPO","")
if not TOKEN or not REPO:
    raise SystemExit("Configure GITHUB_STORAGE_TOKEN and GITHUB_STORAGE_REPO in Actions secrets.")
def request(path,payload=None):
    url="https://api.github.com/repos/"+REPO+"/contents/"+path
    headers={"Authorization":"Bearer "+TOKEN,"Accept":"application/vnd.github+json","User-Agent":"Huie-safe-line-archive"}
    req=urllib.request.Request(url,headers=headers,data=json.dumps(payload).encode() if payload is not None else None,method="PUT" if payload is not None else "GET")
    try:
        with urllib.request.urlopen(req,timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code==404 and payload is None:return None
        raise
def read(path):
    item=request(path)
    return base64.b64decode(item["content"]) if item else None
def write(path,data):
    old=request(path)
    payload={"message":"Archive verified daily NBA safe lines","content":base64.b64encode(data).decode()}
    if old:payload["sha"]=old["sha"]
    request(path,payload)
# Select only pure functions; do not execute Streamlit's top-level UI or auth.
names={"load_workbook","clean_sheet","lookup","espn_matchup_score","espn_nba_boxscores","match_espn_player","grade_bankroll_sheet"}
tree=ast.parse(Path("app.py").read_text())
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
assert {n.name for n in nodes}==names
for n in nodes:n.decorator_list=[]
exec(compile(ast.Module(body=nodes,type_ignores=[]),"app.py","exec"),globals())
def main():
    import re
    today=datetime.now(ZoneInfo("America/Los_Angeles")).date()
    index=request("history") or []
    archived={}
    for item in index:
        m=re.fullmatch(r"(\d{8})_(\d{6})\.xlsx",item.get("name",""))
        if not m:continue
        stamp=datetime.strptime("".join(m.groups()),"%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        day=stamp.astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat()
        if day not in archived or stamp>archived[day][0]:archived[day]=(stamp,item["path"])
    # Retry the past 14 days; never use latest.xlsx for historical picks.
    for offset in range(14,0,-1):
        day=(today-timedelta(days=offset)).isoformat()
        saved=json.loads(read("bankroll_verified_results.json") or b"{}")
        if day in saved and saved[day].get("picks") and all(p.get("Result") in ("Hit","Loss","DNP") for p in saved[day]["picks"]):continue
        path="bankroll_picks_"+day+".json"
        raw=read(path)
        if raw:
            frame=pd.DataFrame(json.loads(raw).get("picks",[]))
        elif day in archived:
            books=load_workbook(read(archived[day][1]))
            sheet=next((s for s in books if "bankroll" in s.lower()),None)
            if not sheet:continue
            frame=clean_sheet(books[sheet])
            if frame.empty or not lookup(frame,"Player") or not lookup(frame,"Safer line","Safe line","Safe alternate line","Alternate line"):continue
            write(path,frame_to_snapshot(frame,day))
        else:
            print(day,"no dated workbook; skipped")
            continue
        if frame.empty:continue
        rows=grade_bankroll_sheet(frame,day)
        if len(rows)!=len(frame) or any(r["Result"] not in ("Hit","Loss","DNP") for r in rows):
            print(day,"unverified selections; retry next run")
            continue
        saved=json.loads(read("bankroll_verified_results.json") or b"{}")
        saved[day]={"picks":rows,"saved_at":datetime.now(timezone.utc).isoformat(),"source":"scheduled final box scores"}
        write("bankroll_verified_results.json",json.dumps(saved,allow_nan=False).encode())
        print(day,"archived",len(rows),"selections")
def frame_to_snapshot(frame,day):
    return json.dumps({"date":day,"picks":json.loads(frame.to_json(orient="records"))}).encode()
if __name__=="__main__":main()
