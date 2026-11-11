"""Daily Huie projection hit-rate summary, graded only against completed NBA box scores.

This grades the Huie direction versus the workbook Reference line. It is not a
parlay/Robinhood settlement tracker and does not infer outcomes from absent data.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from parlay_context import parse_game, team_key

MARKETS=("Points","Rebounds","Assists","Threes")
SIDES=("OVER","UNDER")


def grade_predictions(projections, games, players, player_match):
    """Return every eligible projection with a conservative, date-scoped outcome."""
    # Both the workbook matchup and the ESPN game's matchup must agree.
    by_matchup={}
    for game in games:
        matchup=parse_game(game.get("name",""))
        if matchup:
            by_matchup[frozenset(team_key(t) for t in matchup)]=game
    results=[]
    for _,p in projections.iterrows():
        market=str(p.get("Market",""))
        if market not in MARKETS:
            continue
        player_name=str(p.get("Player","")).strip()
        game_name=str(p.get("Game","")).strip()
        ref=pd.to_numeric(p.get("Reference line"),errors="coerce")
        projected=pd.to_numeric(p.get("Huie projection"),errors="coerce")
        if pd.isna(ref) or pd.isna(projected):
            side="Unverified"
        elif projected>ref:
            side="OVER"
        elif projected<ref:
            side="UNDER"
        else:
            side="At line"
        record={"Player":player_name,"Game":game_name,"Market":market,
                "Side":side,"Reference line":ref,"Huie projection":projected,
                "Actual":None,"Result":"Unverified"}
        expected=parse_game(game_name)
        game=by_matchup.get(frozenset(team_key(t) for t in expected)) if expected else None
        if side not in SIDES:
            record["Result"]="No side" if side=="At line" else "Unverified projection"
        elif game is None:
            record["Result"]="Matchup not verified for date"
        elif game.get("state")!="post":
            record["Result"]="Pending game"
        elif game.get("boxscore_error"):
            record["Result"]="Box score unavailable"
        else:
            # Only match players from this exact final game; avoid same-initial
            # collisions across different games and teams.
            eligible=[a for a in players if
                      str(a.get("game",{}).get("id",""))==str(game.get("id",""))]
            athlete=player_match(player_name,eligible,market)
            if athlete is None:
                record["Result"]="Unmatched"
            elif athlete.get("dnp"):
                record["Result"]="DNP"
            else:
                actual=athlete.get("stats",{}).get(market)
                actual=pd.to_numeric(actual,errors="coerce")
                if pd.isna(actual):
                    record["Result"]="Unverified stat"
                else:
                    record["Actual"]=float(actual)
                    if actual==ref:
                        record["Result"]="Push"
                    elif (side=="OVER" and actual>ref) or (side=="UNDER" and actual<ref):
                        record["Result"]="Hit"
                    else:
                        record["Result"]="Miss"
        results.append(record)
    return pd.DataFrame(results)


def _stat_summary(graded):
    rows=[]
    for market in MARKETS:
        row={"Stat":market}
        total_hits=total_graded=0
        for side in SIDES:
            subset=graded[(graded["Market"]==market)&(graded["Side"]==side)]
            hits=int((subset["Result"]=="Hit").sum())
            misses=int((subset["Result"]=="Miss").sum())
            n=hits+misses
            row[side.title()+" hits"]=hits
            row[side.title()+" graded"]=n
            row[side.title()+" hit rate"]=f"{100*hits/n:.1f}%" if n else "—"
            total_hits+=hits
            total_graded+=n
        row["Total hits"]=total_hits
        row["Total graded"]=total_graded
        row["Hit rate"]=f"{100*total_hits/total_graded:.1f}%" if total_graded else "—"
        rows.append(row)
    return pd.DataFrame(rows)


def render_summary(projections, espn_nba_boxscores, match_espn_player, selected_date):
    """Show the independently graded chart before per-game projections."""
    @st.fragment(run_every="30s")
    def live_summary():
        st.subheader("📊 Huie Projections Daily Hit Summary")
        st.caption("All Huie projections in the selected matchup scope · Final NBA results only · Auto-refreshes every 30 seconds while open")
        st.caption("Selected NBA game date: **"+selected_date.strftime("%b %-d, %Y")+"**. The current workbook must be for this date; switching dates does not load an older workbook.")
        if st.button("↻ Refresh box scores",key="huie_daily_refresh"):
            espn_nba_boxscores.clear()
            st.rerun(scope="fragment")
        try:
            games,players=espn_nba_boxscores(selected_date.strftime("%Y%m%d"))
        except Exception as exc:
            st.warning("ESPN box scores are temporarily unavailable ("+type(exc).__name__+"). No projections were counted as wins or losses.")
            return
        if not games:
            st.info("No NBA games were returned for this date. Nothing has been graded.")
            return
        # Block false hit rates when the latest workbook belongs to another
        # slate. November 10 and November 11 can share one matchup, so a few
        # legitimate-looking graded props do NOT prove the date is correct.
        workbook_matchups={frozenset(team_key(t) for t in parsed)
                           for label in projections.get("Game",pd.Series(dtype=str)).dropna().unique()
                           if (parsed:=parse_game(label))}
        scoreboard_matchups={frozenset(team_key(t) for t in parsed)
                             for event in games
                             if (parsed:=parse_game(event.get("name","")))}
        matching_games=len(workbook_matchups & scoreboard_matchups)
        expected_games=len(workbook_matchups)
        if not expected_games:
            st.error("The workbook's game labels could not be validated. No box-score results were graded.")
            return
        if matching_games!=expected_games:
            st.warning(f"Only {matching_games} of {expected_games} workbook matchups match the "
                       f"ESPN schedule for {selected_date:%b %d, %Y}.")
        if matching_games/expected_games<0.8:
            st.error("The workbook appears to belong to a different NBA date. "
                     "Grading is blocked to prevent a misleading hit rate. "
                     "Select the workbook's actual game date or load the matching archived projections.")
            return
        graded=grade_predictions(projections,games,players,match_espn_player)
        if graded.empty:
            st.info("No Huie player projections were available to grade.")
            return
        scoped=graded[graded["Side"].isin(SIDES)]
        finished=scoped[scoped["Result"].isin(("Hit","Miss"))]
        hits=int((finished["Result"]=="Hit").sum())
        over=int(((finished["Side"]=="OVER")&(finished["Result"]=="Hit")).sum())
        under=int(((finished["Side"]=="UNDER")&(finished["Result"]=="Hit")).sum())
        attempts=len(finished)
        a,b,c,d=st.columns(4)
        a.metric("Total hits",hits)
        b.metric("Over hits",over)
        c.metric("Under hits",under)
        d.metric("Hit rate",f"{100*hits/attempts:.1f}%" if attempts else "—")
        st.caption(f"{attempts} graded (hit/miss) · {int((scoped['Result']=='Push').sum())} pushes · "
                   f"{int((scoped['Result']=='DNP').sum())} DNP · "
                   f"{len(scoped)-attempts-int((scoped['Result']=='Push').sum())-int((scoped['Result']=='DNP').sum())} pending/unverified")
        table=_stat_summary(graded)
        with st.expander("Grading coverage and unverified reasons",expanded=attempts==0 or attempts<len(scoped)*0.6):
            st.caption(f"Matched NBA games: {matching_games}/{expected_games} · "
                       f"Final box-score outcomes: {attempts}/{len(scoped)} projected Over/Under picks")
            breakdown=(scoped["Result"].value_counts(dropna=False)
                       .rename_axis("Result").reset_index(name="Projections"))
            st.dataframe(breakdown,hide_index=True,use_container_width=True)
            st.caption("Unmatched players and missing stats are not silently treated as misses.")
        if attempts:
            try:
                import altair as alt
                chart_rows=[]
                for _,r in table.iterrows():
                    for side in SIDES:
                        chart_rows.append({"Stat":r["Stat"],"Side":side,
                                           "Hits":r[side.title()+" hits"],
                                           "Graded":r[side.title()+" graded"],
                                           "Hit rate":r[side.title()+" hit rate"]})
                plot=pd.DataFrame(chart_rows)
                chart=(alt.Chart(plot).mark_bar().encode(
                    x=alt.X("Stat:N",sort=list(MARKETS),title=None,
                            axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("Hits:Q",title="Projections hit",stack="zero",
                            axis=alt.Axis(tickMinStep=1)),
                    color=alt.Color("Side:N",sort=list(SIDES),
                                    scale=alt.Scale(domain=["OVER","UNDER"],range=["#16a34a","#dc2626"]),
                                    legend=alt.Legend(title="Huie model side")),
                    tooltip=["Stat:N","Side:N","Hits:Q","Graded:Q","Hit rate:N"]
                    ).properties(height=290))
                st.altair_chart(chart,use_container_width=True)
            except ImportError:
                st.bar_chart(table.set_index("Stat")[["Over hits","Under hits"]],stack=True)
        else:
            st.info("Games have not produced any final, verified Huie hits or misses yet. The chart will populate after games finish.")
        st.dataframe(table,hide_index=True,use_container_width=True,
                     column_config={"Stat":st.column_config.TextColumn("Stat",width="small")})
        with st.expander("See every projection and final result",expanded=False):
            choices=["All","Hit","Miss","Pending/unverified","DNP","Push"]
            choice=st.selectbox("Show results",choices,key="huie_daily_result_filter")
            shown=graded
            if choice in ("Hit","Miss","DNP","Push"):
                shown=graded[graded["Result"]==choice]
            elif choice=="Pending/unverified":
                shown=graded[~graded["Result"].isin(("Hit","Miss","DNP","Push"))]
            st.dataframe(shown[["Player","Game","Market","Side","Reference line",
                                "Huie projection","Actual","Result"]],
                         hide_index=True,use_container_width=True)
            st.download_button("Export daily Huie results CSV",graded.to_csv(index=False),
                               file_name="huie_projections_"+selected_date.isoformat()+".csv",
                               mime="text/csv",key="huie_daily_export")
        st.caption("Grading: OVER wins above the reference line; UNDER wins below. Exact ties are pushes. Live, unplayed, missing and DNP records never count as losses.")
    live_summary()
