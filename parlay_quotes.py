"""Optional read-only HTTPS market-quote feed. Never fabricates Robinhood prices.

Feed is administrator-configured in Streamlit Secrets and MUST explicitly supply
actual fees, contract side, instrument ID, and timestamp. Not a Robinhood API.
"""
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import json
import math
from parlay_context import name_key

def validate_quotes(payload, now=None, max_age_minutes=20):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None: raise ValueError("now must be timezone-aware")
    if not isinstance(payload,dict) or not isinstance(payload.get("contracts"),list):
        raise ValueError("Invalid contract quote format")
    output=[]
    for entry in payload["contracts"]:
        if not isinstance(entry,dict):continue
        if str(entry.get("side","")).lower() not in ("yes","over"):continue
        if str(entry.get("market","")).title() not in ("Points","Rebounds","Assists","Threes"):continue
        if not entry.get("contract_id") or not entry.get("player"):continue
        try:
            timestamp=datetime.fromisoformat(str(entry["timestamp"]).replace("Z","+00:00"))
            if timestamp.tzinfo is None:continue
            age=(now-timestamp.astimezone(timezone.utc)).total_seconds()
            if age < -180 or age>max_age_minutes*60:continue
            line=float(entry["line"]);price=float(entry["price"]);fee=float(entry["fee"])
            if not all(math.isfinite(v) for v in (line,price,fee)):continue
            if line<=0 or not 0<price<1 or fee<0 or price+fee>=1:continue
            # $1 binary YES contract; reject other payout conventions.
            if float(entry.get("payout",1))!=1:continue
        except (ValueError,TypeError,KeyError,OverflowError):continue
        output.append({"player":str(entry["player"]),"key":name_key(entry["player"]),
                       "market":str(entry["market"]).title(),"line":line,
                       "contract_id":str(entry["contract_id"]),"price":price,"fee":fee,
                       "timestamp":timestamp.isoformat(),"source":str(entry.get("source","Configured quote feed"))})
    return output

def fetch_quote_feed(url,bearer_token="",timeout=8):
    parsed=urlparse(url)
    if parsed.scheme!="https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Quote feed requires a trusted HTTPS URL")
    headers={"User-Agent":"DegenCenter-QuoteReader/1.0","Accept":"application/json"}
    if bearer_token:headers["Authorization"]="Bearer "+bearer_token
    with urlopen(Request(url,headers=headers),timeout=timeout) as r:
        raw=r.read(2_000_001)
    if len(raw)>2_000_000:raise ValueError("Quote feed response too large")
    return validate_quotes(json.loads(raw))

def match_quote(player,market,line,quotes):
    """Require unambiguous full or first-initial surname identity and exact line."""
    tokens=name_key(player).split()
    if len(tokens)<2:return None
    candidates=[]
    for q in quotes:
        if q["market"]!=str(market).title() or q["line"]!=float(line):continue
        bits=q["key"].split()
        if bits==tokens or (len(bits)>=2 and bits[0].startswith(tokens[0]) and bits[1:]==tokens[1:]):
            candidates.append(q)
    return candidates[0] if len(candidates)==1 else None
