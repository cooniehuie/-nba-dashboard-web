"""Reusable 30-second NBA combo tracker for model-specific performance pages."""
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

def render_live_parlays(bets, espn_nba_boxscores, match_espn_player, settlements=None, prefix="model", title="Live tracking"):
    settlements=settlements or {}
    @st.fragment(run_every="30s")
    def live_panel():
        st.subheader("🔴 "+title)
        st.caption("Refreshes every 30 seconds while this page is open · ESPN NBA box scores · Game progress is not Robinhood settlement.")
        if st.button("↻ Refresh stats",key=prefix+"_refresh"):
            espn_nba_boxscores.clear()
            st.rerun(scope="fragment")
        by_date={}
        for bet in bets:
            by_date.setdefault(bet["date"],[]).append(bet)
        feeds={}
        for day in by_date:
            try:
                feeds[day]=espn_nba_boxscores(day.replace("-",""))
            except Exception as exc:
                feeds[day]=([],[])
                st.warning(f"{day}: Live box scores unavailable ({type(exc).__name__}). No results inferred.")
        result_rows=[]
        summaries=[]
        for bet in bets:
            games,players=feeds[bet["date"]]
            if any(g.get("boxscore_error") for g in games):
                st.warning(bet["date"]+": One or more game box scores failed; unavailable stats remain unverified.")
            hit=miss=unverified=0
            leg_rows=[]
            for name,market,target in bet["legs"]:
                athlete=match_espn_player(name,players,market)
                game=athlete.get("game",{}) if athlete else {}
                actual=athlete.get("stats",{}).get(market) if athlete else None
                state=game.get("state","unknown")
                dnp=bool(athlete.get("dnp")) if athlete else False
                if dnp:
                    status="⚪ DNP · settlement pending"
                    unverified+=1
                elif actual is None:
                    status="🟡 Stats pending" if state=="in" else "⚪ Not started" if state=="pre" else "⚪ Unmatched / unavailable"
                    unverified+=1
                elif actual>=target:
                    status="🟢 Hit" if state=="post" else "🟢 Target reached"
                    hit+=1
                elif state=="post":
                    status="🔴 Miss"
                    miss+=1
                else:
                    status="🟡 In progress" if state=="in" else "⚪ Not started"
                    unverified+=1
                start=game.get("start_utc","")
                try:
                    game_time=datetime.fromisoformat(start.replace("Z","+00:00")).astimezone(ZoneInfo("America/Los_Angeles")).strftime("%-I:%M %p PT")
                except (ValueError,TypeError):
                    game_time="—"
                row={"Player":name+(" #"+str(athlete.get("jersey")) if athlete and athlete.get("jersey") else ""),
                     "Market":market,"Target":f"{target}+","Actual":actual if actual is not None else "—",
                     "Needed":max(0,target-actual) if actual is not None else "—",
                     "Progress":f"{min(100,actual/target*100):.0f}%" if actual is not None and target>0 else "—",
                     "Status":status,"Game":game.get("name","—"),"Tipoff":game_time,
                     "Game status":game.get("detail","Unavailable")}
                leg_rows.append(row)
                result_rows.append({"Date":bet["date"],"Parlay":bet["label"],**row})
            settlement=settlements.get(bet.get("my_bets",""),{})
            settled=settlement.get("status") in ("Won","Loss","Lost","Closed") and settlement.get("realized_profit") is not None
            if settled:
                status="✅ Settled won" if settlement["status"]=="Won" else "🔴 Settled lost"
            elif miss:
                status="🔴 Game result: lost"
            elif hit==len(bet["legs"]):
                status="🟢 All targets reached"
            else:
                status="🟡 In progress" if any(r["Status"].startswith("🟡") or r["Status"]=="🟢 Target reached" for r in leg_rows) else "⚪ Pending"
            summaries.append({"bet":bet,"rows":leg_rows,"hits":hit,"misses":miss,"unverified":unverified,"settlement":settlement,"settled":settled,"status":status})
        invested=sum(x["cost"] for x in bets)
        possible=sum(x["quantity"]-x["cost"] for x in bets)
        realized=sum(float(x["settlement"]["realized_profit"]) for x in summaries if x["settled"])
        a,b,c=st.columns(3)
        a.metric("Invested",f"${invested:,.2f}")
        b.metric("Max potential profit",f"+${possible:,.2f}")
        c.metric("Realized P/L",f"${realized:+,.2f}" if any(x["settled"] for x in summaries) else "Pending")
        a,b,c=st.columns(3)
        a.metric("Parlays",len(bets))
        b.metric("Leg targets reached",f'{sum(x["hits"] for x in summaries)}/{sum(len(x["bet"]["legs"]) for x in summaries)}')
        c.metric("Confirmed settlements",sum(x["settled"] for x in summaries))
        st.caption("Realized P/L uses confirmed settlement amounts only, never hypothetical payouts or box-score-based assumed returns.")
        # Unsettled in-progress first; game-completed and settled combos last.
        summaries.sort(key=lambda x:(2 if x["settled"] else 1 if x["misses"] or x["hits"]==len(x["rows"]) else 0,
                                     x["bet"].get("time",x["bet"].get("filled_at","")),x["bet"]["label"]))
        dates=sorted({item["bet"]["date"] for item in summaries},reverse=True)
        if len(dates)>1:
            selected_date=st.selectbox(
                "Parlay history by date",
                options=dates,
                format_func=lambda d: datetime.strptime(d,"%Y-%m-%d").strftime("%b %d, %Y"),
                key=prefix+"_history_date",
            )
            st.caption(f"Showing {sum(item['bet']['date']==selected_date for item in summaries)} parlays for the selected date")
        else:
            selected_date=dates[0] if dates else None
        for item in summaries:
            if item["bet"]["date"]!=selected_date:
                continue
            b=item["bet"]
            with st.expander(f'{b["label"]} · {item["status"]} · {item["hits"]}/{len(b["legs"])} reached',expanded=not item["settled"]):
                st.caption(f'{b["date"]} · {b.get("time",b.get("filled_at",""))} PT · {b["quantity"]:,} contracts · Cost ${b["cost"]:.2f} (fees included) · Max profit +${b["quantity"]-b["cost"]:,.2f}')
                st.dataframe(pd.DataFrame(item["rows"]),hide_index=True,use_container_width=True)
                if b.get("id") and len(b["id"])>12:
                    st.link_button("View Robinhood event","https://robinhood.com/events/combos/"+b["id"]+"?source=event_contract_order")
                if item["settled"]:
                    st.caption(f'Confirmed Realized P/L: ${float(item["settlement"]["realized_profit"]):+,.2f}')
                else:
                    st.caption("Realized P/L: pending Robinhood settlement")
        st.caption("Last checked: "+datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%-I:%M:%S %p PT"))
        if result_rows:
            with st.expander("All individual legs · export",expanded=False):
                out=pd.DataFrame(result_rows)
                st.dataframe(out,hide_index=True,use_container_width=True)
                st.download_button("Download live leg results CSV",out.to_csv(index=False),
                                   prefix+"_live_legs.csv","text/csv",key=prefix+"_export")
    live_panel()
