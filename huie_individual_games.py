"""Public read-only Huie projections grouped like Sam's Individual Games."""
import pandas as pd
import streamlit as st

from parlay_context import parse_game, team_key
from parlay_predictive import audit as predictive_audit
from parlay_huie_projections import (historical_projection_results,
                                     enrich_huie_projections,
                                     opponent_adjusted_projections)
from parlay_lab import _candidates, _historical_boxscores, _recent_opponent_context


def prepare_projections(all_props,history=None,model_audit=None,context_rows=None):
    """Use All Player Props reference lines and the SAME Huie pipeline as Model Lab."""
    data=_candidates(all_props,reference_only=True)
    if data.empty:return data
    if history:
        audit=model_audit if model_audit is not None else predictive_audit(history)
        historical=historical_projection_results(data,history,audit)
        data=enrich_huie_projections(data,historical)
    if context_rows:
        data=opponent_adjusted_projections(data,context_rows)
    line=pd.to_numeric(data["Safe line"],errors="coerce")
    huie=pd.to_numeric(data["Huie baseline"],errors="coerce")
    sam=pd.to_numeric(data["Sam projection"],errors="coerce")
    data["Huie edge"]=(huie-line).round(2)
    data["Sam edge"]=(sam-line).round(2)
    data["Huie side"]=["🟢 OVER" if pd.notna(h) and h>ref else
                       "🔴 UNDER" if pd.notna(h) and h<ref else
                       "⚪ AT LINE" if pd.notna(h) and h==ref else
                       "⚪ UNVERIFIED"
                       for h,ref in zip(huie,line)]
    data["Both models OVER"]=["Yes" if pd.notna(h) and pd.notna(s) and h>ref and s>ref
                               else "Unverified" if pd.isna(h) or pd.isna(s)
                               else "No"
                               for h,s,ref in zip(huie,sam,line)]
    return data.rename(columns={"Safe line":"Reference line",
                                 "Huie baseline":"Huie projection",
                                 "Baseline source":"Projection method"})


@st.cache_data(ttl=21600,show_spinner=False)
def _validated_audit(history):
    return predictive_audit(history)


def _opponent_codes(frame):
    opponents=set()
    for _,pick in frame.iterrows():
        teams=parse_game(pick.get("Game",""))
        team=team_key(pick.get("ESPN team","")) if pd.notna(pick.get("ESPN team")) else ""
        if teams and team in teams:
            opponents.add(teams[0] if teams[1]==team else teams[1])
    return tuple(sorted(opponents))


def _table(frame,key):
    wanted=["Player","Market","Reference line","Huie projection","Huie edge",
            "Huie side","Both models OVER","Sam projection","Sam edge",
            "Last game","2 games ago","3 games ago","Recent hits",
            "Expected minutes","Minutes trend","Projection method",
            "Predictive validation","Matchup context","External games"]
    columns=[c for c in wanted if c in frame.columns]
    values=frame.sort_values("Huie edge",ascending=False,na_position="last")[columns].copy()
    for c in ("Reference line","Huie projection","Huie edge","Sam projection",
              "Sam edge","Last game","2 games ago","3 games ago","Expected minutes"):
        if c in values:
            values[c]=pd.to_numeric(values[c],errors="coerce").round(1)
    st.dataframe(values,hide_index=True,use_container_width=True,key=key,
                 column_config={
                     "Player":st.column_config.TextColumn("Player",width="medium"),
                     "Market":st.column_config.TextColumn("Market",width="small"),
                     "Reference line":st.column_config.NumberColumn("Reference line",format="%.1f"),
                     "Huie projection":st.column_config.NumberColumn("Huie projection",format="%.1f"),
                     "Huie edge":st.column_config.NumberColumn("Huie edge",format="%+.1f"),
                     "Sam projection":st.column_config.NumberColumn("Sam projection",format="%.1f"),
                     "Sam edge":st.column_config.NumberColumn("Sam edge",format="%+.1f"),
                 })


def render(all_props):
    st.title("🏀 Huie Projections · Individual Games")
    st.caption("All Player Props · Huie's independently calculated NBA projections vs the Reference line. Public read-only. Sam's projections are displayed for comparison only, not used to calculate Huie's.")

    if all_props is None or all_props.empty:
        st.info("No All Player Props sheet is loaded. Upload the daily workbook as administrator.")
        return
    candidates=_candidates(all_props,reference_only=True)
    if candidates.empty:
        st.warning("No player props with a recognized market and numeric Reference line were found in All Player Props.")
        return

    games=list(dict.fromkeys(candidates["Game"].dropna().astype(str).tolist()))
    game_choice=st.selectbox("Choose matchup",["All games"]+games,key="huie_game_choice")
    matching=candidates if game_choice=="All games" else candidates[candidates["Game"]==game_choice]

    with st.spinner("Preparing independently verified Huie projections..."):
        try:
            history,failures=_historical_boxscores()
        except Exception as exc:
            history={};failures=0
            st.warning("ESPN historical results unavailable; only verified stats already in the workbook can be used. "+str(exc))
        try:
            audit=_validated_audit(history) if history else {}
        except Exception as exc:
            audit={}
            st.warning("Historical model validation is unavailable; no enhanced model is activated. "+str(exc))
        data=prepare_projections(matching,history,model_audit=audit)
    if data.empty:
        st.info("No usable projection rows for this matchup.")
        return

    use_matchup=st.checkbox("Include verified opponent pace/defense adjustment where available",
                            value=False,key="huie_games_matchup",
                            help="Optional: uses ESPN completed-team boxscores. This may take longer for All games.")
    if use_matchup:
        opponents=_opponent_codes(data)
        if opponents:
            with st.spinner("Checking recent opponent pace and defense..."):
                try:
                    context=_recent_opponent_context(opponents)
                    data=opponent_adjusted_projections(data,context.get("rows",[]))
                    # Recompute displayed edges and sides after final adjustments.
                    data=prepare_side_metrics(data)
                    if context.get("failures"):
                        st.caption(f'{context["failures"]} opponent-data requests were unavailable; missing values were not imputed.')
                except Exception as exc:
                    st.warning("Opponent adjustments unavailable; unadjusted forecasts are shown. "+str(exc))
        else:
            st.caption("Opponent adjustments require an unambiguous ESPN player team and workbook matchup.")

    market_choices=sorted(data["Market"].dropna().unique().tolist())
    c1,c2=st.columns([2,2])
    markets=c1.multiselect("Markets",market_choices,default=market_choices,key="huie_games_markets")
    keyword=c2.text_input("Search player",key="huie_games_search")
    filtered=data[data["Market"].isin(markets)].copy()
    if keyword.strip():
        filtered=filtered[filtered["Player"].str.contains(keyword.strip(),case=False,regex=False,na=False)]
    over_only=st.checkbox("Only Huie OVER projections",value=False,key="huie_games_over_only")
    both_only=st.checkbox("Only props where BOTH Huie and Sam project OVER",value=False,key="huie_games_both_only")
    if over_only:
        filtered=filtered[filtered["Huie side"]=="🟢 OVER"]
    if both_only:
        filtered=filtered[filtered["Both models OVER"]=="Yes"]

    m1,m2,m3,m4=st.columns(4)
    m1.metric("Displayed props",len(filtered))
    m2.metric("Huie OVER",int((filtered["Huie side"]=="🟢 OVER").sum()))
    m3.metric("Both models OVER",int((filtered["Both models OVER"]=="Yes").sum()))
    m4.metric("Unverified Huie",int(filtered["Huie projection"].isna().sum()))

    if failures:
        st.caption(f"{failures} historical ESPN date requests were unavailable. Incomplete player records are never treated as results.")
    st.caption("🟢 OVER means Huie's projection is strictly above the reference line; 🔴 UNDER means strictly below. Missing data stays unverified. These projections do not establish a profitable wager.")

    if filtered.empty:
        st.info("No player props match these filters. Try clearing one of the OVER-only filters.")
        return

    if game_choice!="All games":
        st.subheader(game_choice)
        _table(filtered,"huie_individual_selected")
    else:
        st.subheader("All games · matchup breakdown")
        for i,game in enumerate(games):
            subset=filtered[filtered["Game"]==game]
            if subset.empty:continue
            count=int((subset["Huie side"]=="🟢 OVER").sum())
            with st.expander(f"{game} · {len(subset)} props · {count} Huie OVER",expanded=i==0):
                _table(subset,"huie_individual_"+str(i))

    with st.expander("How Huie's independent projection is calculated"):
        st.write("Verified ESPN box scores supply points, rebounds, assists, threes and playing time. Huie's rate × minutes projection activates for a stat market only when chronological evaluation supports it; otherwise it uses a verified historical fallback. No Sam projections, sportsbook odds or reference lines are used to calculate Huie's stat forecast.")
        if audit:
            st.dataframe(pd.DataFrame([{"Market":k,**v} for k,v in audit.items()]),hide_index=True,use_container_width=True)
        else:
            st.caption("Not enough verified games to evaluate enhanced forecasts. Player projections without reliable underlying history remain unverified.")


def prepare_side_metrics(data):
    """Recompute displayed values from the post-matchup Huie forecast."""
    out=data.copy()
    huie=pd.to_numeric(out["Huie projection"],errors="coerce")
    ref=pd.to_numeric(out["Reference line"],errors="coerce")
    sam=pd.to_numeric(out["Sam projection"],errors="coerce")
    out["Huie edge"]=(huie-ref).round(2)
    out["Huie side"]=["🟢 OVER" if pd.notna(h) and h>r else
                      "🔴 UNDER" if pd.notna(h) and h<r else
                      "⚪ AT LINE" if pd.notna(h) and h==r else
                      "⚪ UNVERIFIED" for h,r in zip(huie,ref)]
    out["Both models OVER"]=["Yes" if pd.notna(h) and pd.notna(s) and h>r and s>r
                              else "Unverified" if pd.isna(h) or pd.isna(s)
                              else "No" for h,s,r in zip(huie,sam,ref)]
    return out
