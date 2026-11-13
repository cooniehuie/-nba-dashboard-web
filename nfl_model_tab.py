"""Sam's NFL HTML model archive. Separate from NBA and Huie forecasts."""
import hashlib,json,re
from datetime import date,datetime,timezone
from html.parser import HTMLParser
import pandas as pd
import streamlit as st

PATH="nfl_models/sam_nfl_archive.json"
MARKETS={"Passing yards","Rushing yards","Receiving yards","Receptions"}

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack=[];self.market=None;self.rows=[];self.card=None;self.capture=[];self.heading=None
    def handle_starttag(self,tag,attrs):
        cls=set(dict(attrs).get("class","").split());self.stack.append((tag,cls))
        if tag=="div" and "pp-mkt" in cls:self.heading=""
        if tag=="details" and "pp" in cls:
            self.card={"Market":self.market,"Player":None,"Team":None,"Sam projection":None,"Reference line":None}
        if self.card is not None:
            for key,name in {"nm":"Player","tm":"Team","pp-proj":"Sam projection","pp-line":"Reference line"}.items():
                if key in cls:self.capture.append([len(self.stack),name,""])
    def handle_data(self,data):
        if self.heading is not None:self.heading+=data
        for item in self.capture:item[2]+=data
    def handle_endtag(self,tag):
        if not self.stack:return
        depth=len(self.stack)
        for item in self.capture[:]:
            if item[0]==depth:
                value=item[2].strip()
                if self.card is not None:
                    if item[1] in ("Sam projection","Reference line"):
                        match=re.search(r"[-+]?\d+(?:\.\d+)?",value)
                        self.card[item[1]]=float(match.group()) if match else None
                    else:self.card[item[1]]=value
                self.capture.remove(item)
        opened,cls=self.stack.pop()
        if opened=="div" and "pp-mkt" in cls:
            heading=re.sub(r"\s+"," ",self.heading or "").strip()
            self.market=heading if heading in MARKETS else None;self.heading=None
        if opened=="details" and "pp" in cls and self.card is not None:
            if self.card["Market"] in MARKETS and self.card["Player"] and self.card["Sam projection"] is not None:
                self.rows.append(self.card)
            self.card=None;self.capture=[]

def parse_html(raw):
    html=raw.decode("utf-8-sig",errors="replace") if isinstance(raw,bytes) else str(raw)
    match=re.search(r"<title[^>]*>(.*?)</title>",html,re.I|re.S)
    title=re.sub(r"\s+"," ",match.group(1)).strip() if match else ""
    game=re.search(r"\b([A-Z]{2,3})\s+(?:at|@|vs)\s+([A-Z]{2,3})\b",title,re.I)
    if not game:raise ValueError("Cannot identify NFL matchup from HTML title")
    parser=Parser();parser.feed(html)
    if not parser.rows:raise ValueError("No Sam NFL prop cards found in uploaded HTML")
    rows={(r["Player"],r["Team"],r["Market"]):r for r in parser.rows}
    return {"matchup":game.group(1).upper()+" @ "+game.group(2).upper(),
            "title":title,"rows":list(rows.values())}

def render(storage_read,storage_write=None,is_admin=False):
    st.title("🏈 NFL Model")
    st.caption("Sam's NFL projections · archived separately from NBA and Huie models")
    try:
        raw=storage_read(PATH)
        archive=json.loads(raw.decode("utf-8") if isinstance(raw,bytes) else raw) if raw else {"schema":1,"games":{}}
        if not isinstance(archive.get("games"),dict):raise ValueError("Invalid NFL archive")
    except Exception as exc:
        st.error("Could not read NFL archive: "+str(exc));return
    if is_admin and storage_write:
        with st.expander("Upload Sam NFL game HTML",expanded=not bool(archive["games"])):
            upload=st.file_uploader("Original NFL player props HTML",type=["html","htm"],key="sam_nfl_html_upload")
            game_date=st.date_input("Game date (Pacific)",value=date.today(),key="sam_nfl_game_date")
            if upload:
                data=upload.getvalue()
                try:
                    parsed=parse_html(data)
                    st.success(f"Found {len(parsed['rows'])} props for {parsed['matchup']}")
                    st.dataframe(pd.DataFrame(parsed["rows"]),hide_index=True,use_container_width=True)
                    digest=hashlib.sha256(data).hexdigest()
                    key=f"{game_date.isoformat()}|{parsed['matchup']}"
                    old=archive["games"].get(key)
                    if old and old.get("sha256")!=digest:
                        st.warning("This date/game already has an archive. Saving replaces only this game.")
                    elif old:st.info("This exact file is already archived for the selected date.")
                    if st.button("Save NFL model",type="primary",key="sam_nfl_save",
                                 disabled=bool(old and old.get("sha256")==digest)):
                        archive["games"][key]={**parsed,"date":game_date.isoformat(),
                            "sha256":digest,"uploaded_at":datetime.now(timezone.utc).isoformat(),
                            "source":"Sam NFL HTML"}
                        storage_write(PATH,json.dumps(archive,ensure_ascii=False,indent=2).encode())
                        st.success("Saved NFL model.");st.rerun()
                except Exception as exc:st.error("Import failed: "+str(exc))
    if not archive["games"]:
        st.info("No saved NFL models yet. Admins can upload original Sam NFL HTML directly—no Excel needed.")
        return
    key=st.selectbox("Saved NFL game",sorted(archive["games"],reverse=True),key="sam_nfl_saved_game")
    record=archive["games"][key];frame=pd.DataFrame(record["rows"])
    if frame.empty:return
    frame["Model side"]=frame.apply(lambda r:
        "OVER" if r["Sam projection"]>r["Reference line"] else
        ("UNDER" if r["Sam projection"]<r["Reference line"] else "EVEN")
        if pd.notna(r["Reference line"]) else "—",axis=1)
    frame["Difference"]=frame["Sam projection"]-frame["Reference line"]
    a,b,c=st.columns(3)
    a.metric("Players",frame["Player"].nunique());b.metric("Props",len(frame));c.metric("Markets",frame["Market"].nunique())
    options=sorted(frame["Market"].unique())
    selected=st.multiselect("Markets",options,default=options,key="sam_nfl_markets")
    view=frame[frame["Market"].isin(selected)]
    st.dataframe(view[["Player","Team","Market","Sam projection","Reference line","Model side","Difference"]],
                 hide_index=True,use_container_width=True)
    st.download_button("Download NFL model CSV",view.to_csv(index=False).encode(),
        file_name="sam_nfl_"+record["date"]+"_"+record["matchup"].replace(" @ ","_")+".csv",
        mime="text/csv")
    st.caption("Uploaded Sam HTML only. No invented lines. Huie comparison and historical grading require verified model snapshots and results.")
