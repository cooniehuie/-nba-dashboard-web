# Huie's Degen Center

Public Streamlit NBA projection dashboard with private admin functions, Bankroll Builder, My Bets and Smart Parlay Builder.

Dashboard: https://huie-dashboard.streamlit.app

## Smart Parlay Builder

The builder creates research-only OVER parlays only when BOTH Sam's and Huie's independently calculated baseline are strictly above the same safe line. Missing projections are excluded. It will never place an order.

Game-day checks are based on ESPN injury listings and live/final boxscore starters. Injury entries are automatically flagged and doubtful/out players excluded; unlisted players are NOT confirmed healthy. Only live/final boxscore starters can be confirmed. Pregame starter status is unknown without a separately verified starting-lineup provider.

Huie's model can use ESPN completed player games, a five-game minutes projection and conservative matchup adjustments derived from actual opponent team pace/defense. Adjustments require five completed opponent games, are capped and benchmarked to the observed opponent sample, not a complete NBA league rating.

The probability calibrator backtests rolling forecasts using historical completed games, trains on earlier dates, evaluates later dates with Brier score, and withholds all forecasts that fail validation. It benchmarks synthetic alternate lines, NOT past Robinhood contracts. Joint Fréchet bounds are computed only with calibrated marginals; a Gaussian copula scenario is only calculated when paired historical dates support correlation estimates. This is a scenario and is not validated as a true parlay win probability.

Contract prices and fees are manual unless the admin sets up a real read-only quote feed. The current connected Robinhood integration does NOT expose live prediction-contract quotes. A positive historical frequency-price gap is not a verified edge, and no parlay is labeled profitable.

## Optional secure quote feed

Set the following in Streamlit Secrets (never in this public GitHub repository):

- ADMIN_PASSWORD: strong administrator password (required for public access)
- PREDICTION_QUOTES_URL: trusted HTTPS URL for read-only structured quotes (optional)
- PREDICTION_QUOTES_BEARER: private token for that feed (optional)

The feed returns a JSON object with a contracts array. Each quote needs contract_id, player, market (Points, Rebounds, Assists, Threes), line, side (yes/over), price between 0 and 1, fee per contract, a time-zone-aware timestamp, and payout=1. Quotes older than 20 minutes, ambiguous player matches, missing fees and mismatched lines are rejected. A configured third-party feed is NOT independently verified to represent Robinhood prices.

Example quote record:

~~~json
{"contracts":[{"contract_id":"provider-123","player":"Stephen Curry","market":"Threes","line":3,"side":"yes","price":0.47,"fee":0.02,"payout":1,"timestamp":"2026-11-09T19:00:00Z","source":"Configured feed"}]}
~~~

## Testing and deployment

Install dependencies and run:

~~~bash
pip install -r requirements.txt
python -m py_compile app.py parlay_*.py
python -m unittest discover -s tests -p 'test_*.py' -v
~~~

The GitHub Actions Parlay Lab checks workflow compiles the app/modules, runs all regression tests, and checks the Smart Parlay screen using Streamlit AppTest. A separate Streamlit production UI smoke workflow uses Playwright to verify public desktop/mobile rendering and saves screenshots. Passing unit tests does NOT establish that the deployed site works; check that workflow separately.

Sam's Models HTML collector remains validation-only: it needs privately stored GitHub Actions secret SAM_MODELS_STORAGE_STATE_B64 and does not publish a daily workbook or modify My Bets. Automatic end-to-end HTML ingestion is not yet connected.

## Limitations

ESPN's public site API is unofficial and may change or fail. All unavailable or ambiguous data remains unknown. Historical model validation and experimental correlation estimates cannot guarantee future outcomes or investment returns. Preserve private bet/settlement data and avoid publishing credentials or private account details.
