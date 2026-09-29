import os
import time
import requests
import pandas as pd
import streamlit as st

from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# ---------------- CONFIGURAZIONE ----------------

API_BASE_URL = "https://api.coingecko.com/api/v3"
API_PRO_URL = "https://pro-api.coingecko.com/api/v3"
TIMEOUT = 15

st.set_page_config(
    page_title="Crypto Swarm v1.1",
    page_icon="🐝",
    layout="wide"
)

# ---------------- UTILS & HELPER ----------------

def format_price(price: float) -> str:
    """Formatta il prezzo con un numero appropriato di decimali."""
    if price >= 1.0:
        return f"${price:,.2f}"
    elif price >= 0.0001:
        return f"${price:,.4f}"
    else:
        return f"${price:,.8f}"

def get_session_with_retries() -> requests.Session:
    """Crea una sessione HTTP con retry automatico ed exponential backoff per rate limit (429/5xx)."""
    session = requests.Session()
    retries = Retry(
        total=4,
        backoff_factor=1,  # Attende 1s, 2s, 4s, 8s
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

# ---------------- MODELLI ----------------

@dataclass
class Candidate:
    id: str
    name: str
    symbol: str
    price: float = 0
    market_cap: float = 0
    fdv: float = 0
    volume: float = 0
    change_24h: float = 0
    change_7d: float = 0

@dataclass
class Result:
    agent: str
    score: float
    confidence: float
    flags: list = field(default_factory=list)

def clamp(x):
    return max(0.0, min(100.0, float(x)))

# ---------------- AGENTI MULTI-AGENTI ----------------

def market_agent(c: Candidate) -> Result:
    score = 50
    flags = []

    score += max(-20, min(20, c.change_24h * 2))
    score += max(-15, min(15, c.change_7d))

    if c.market_cap > 0:
        ratio = c.volume / c.market_cap
        if ratio > 0.25:
            score += 10
            flags.append("Volume elevato rispetto alla market cap")
        elif ratio < 0.01:
            score -= 15
            flags.append("Volume relativamente basso")

    return Result("Market", clamp(score), 0.75, flags)

def tokenomics_agent(c: Candidate) -> Result:
    score = 60
    flags = []

    if c.market_cap > 0 and c.fdv > 0:
        ratio = c.market_cap / c.fdv
        if ratio < 0.25:
            score -= 30
            flags.append("Possibile forte diluizione futura")
        elif ratio < 0.50:
            score -= 15
            flags.append("Attenzione alla diluizione")
        else:
            score += 5
    else:
        score -= 10
        flags.append("Dati FDV o market cap mancanti")

    return Result("Tokenomics", clamp(score), 0.8, flags)

def liquidity_agent(c: Candidate) -> Result:
    score = 65
    flags = []

    if c.volume < 100_000:
        score -= 25
        flags.append("Volume giornaliero molto basso")
    elif c.volume < 500_000:
        score -= 10
        flags.append("Volume da verificare")

    if c.market_cap > 0 and c.volume / c.market_cap > 1:
        score -= 15
        flags.append("Turnover anomalo da verificare")

    return Result("Liquidity", clamp(score), 0.5, flags)

def developer_agent(c: Candidate) -> Result:
    return Result("Developer", 50, 0.1, ["Dati GitHub non collegati"])

def onchain_agent(c: Candidate) -> Result:
    return Result("On-chain", 50, 0.1, ["Dati on-chain non disponibili"])

def contrarian_agent(c: Candidate) -> Result:
    score = 70
    flags = []

    if c.change_24h > 30:
        score -= 25
        flags.append("Possibile eccesso di rialzo nel breve termine")

    if c.market_cap > 0 and c.fdv > c.market_cap * 5:
        score -= 20
        flags.append("FDV molto superiore alla market cap")

    if c.volume > c.market_cap > 0:
        score -= 10
        flags.append("Volume superiore alla market cap")

    return Result("Contrarian", clamp(score), 0.6, flags)

def security_agent(c: Candidate) -> Result:
    score = 50
    flags = [
        "Audit smart contract non verificato",
        "Concentrazione holder non verificata"
    ]

    if c.market_cap <= 0:
        score -= 20
        flags.append("Market cap non disponibile")

    return Result("Security", clamp(score), 0.2, flags)

# ---------------- QUANT AGENT ----------------

WEIGHTS = {
    "Market": 0.20,
    "Tokenomics": 0.20,
    "Liquidity": 0.15,
    "Developer": 0.10,
    "On-chain": 0.10,
    "Contrarian": 0.15,
    "Security": 0.10,
}

def quant_agent(results):
    total = sum(WEIGHTS[r.agent] for r in results)

    opportunity = sum(
        r.score * WEIGHTS[r.agent] for r in results
    ) / total

    flags = [f for r in results for f in r.flags]
    risk = 100 - opportunity

    if any("Volume giornaliero molto basso" in f for f in flags):
        risk = min(100, risk + 10)

    confidence = sum(r.confidence for r in results) / len(results)

    return round(opportunity, 1), round(risk, 1), round(confidence * 100, 1)

# ---------------- SWARM ----------------

def run_swarm(c: Candidate):
    agents = [
        market_agent,
        tokenomics_agent,
        liquidity_agent,
        developer_agent,
        onchain_agent,
        contrarian_agent,
        security_agent,
    ]

    with ThreadPoolExecutor(max_workers=len(agents)) as pool:
        results = list(pool.map(lambda fn: fn(c), agents))

    opportunity, risk, confidence = quant_agent(results)

    return {
        "candidate": c,
        "results": results,
        "opportunity": opportunity,
        "risk": risk,
        "confidence": confidence,
    }

# ---------------- DATI DI MERCATO ----------------
@st.cache_data(ttl=300, show_spinner=False)
def get_market(limit: int, api_key: str = ""):
    session = get_session_with_retries()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "accept": "application/json"
    }
    
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": limit,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h,7d",
    }

    if api_key:
        headers["x-cg-demo-api-key"] = api_key

    url = f"{API_BASE_URL}/coins/markets"

    response = session.get(url, params=params, headers=headers, timeout=TIMEOUT)
    response.raise_for_status()

    data = response.json()
    coins = []

    for x in data:
        coins.append(Candidate(
            id=x["id"],
            name=x["name"],
            symbol=x["symbol"].upper(),
            price=x.get("current_price") or 0,
            market_cap=x.get("market_cap") or 0,
            fdv=x.get("fully_diluted_valuation") or 0,
            volume=x.get("total_volume") or 0,
            change_24h=x.get("price_change_percentage_24h") or 0,
            change_7d=x.get("price_change_percentage_7d_in_currency") or 0,
        ))

    return coins

# ---------------- INTERFACCIA ----------------

st.title("🐝 Crypto Swarm")
st.caption("Multi-agent crypto research • Screening, non financial advice")

with st.sidebar:
    st.header("Scanner Config")
    limit = st.slider("Numero di asset", 10, 100, 30)
    min_score = st.slider("Score minimo", 0, 100, 50)
    
    st.divider()
    st.subheader("API Options")
    api_key_input = st.text_input("CoinGecko API Key (Opzionale)", type="password", help="Inserisci la chiave API per prevenire blocchi di rate limit.")
    
    start = st.button("🔎 Avvia scansione", type="primary")

if start:
    try:
        with st.spinner("Raccolta dati e analisi degli agenti..."):
            coins = get_market(limit, api_key_input)

            reports = []
            for coin in coins:
                reports.append(run_swarm(coin))

        rows = []

        for r in reports:
            c = r["candidate"]
            rows.append({
                "ID": c.id,
                "Asset": f"{c.name} ({c.symbol})",
                "Prezzo USD": c.price,
                "Variazione 24h %": c.change_24h / 100,
                "Variazione 7d %": c.change_7d / 100,
                "Market cap USD": c.market_cap,
                "Volume 24h USD": c.volume,
                "Opportunità": r["opportunity"],
                "Rischio": r["risk"],
                "Confidenza dati": r["confidence"] / 100,
            })

        df = pd.DataFrame(rows)
        df = df[df["Opportunità"] >= min_score]
        df = df.sort_values("Opportunità", ascending=False)

        st.subheader(f"Asset trovati: {len(df)}")
        
        # Formattazione avanzata con st.column_config
        st.dataframe(
            df.drop(columns=["ID"]),
            column_config={
                "Prezzo USD": st.column_config.NumberColumn(
                    "Prezzo USD",
                    format="$%.4f"
                ),
                "Variazione 24h %": st.column_config.NumberColumn(
                    "24h %",
                    format="%.2f%%"
                ),
                "Variazione 7d %": st.column_config.NumberColumn(
                    "7d %",
                    format="%.2f%%"
                ),
                "Market cap USD": st.column_config.NumberColumn(
                    "Market Cap",
                    format="$%,.0f"
                ),
                "Volume 24h USD": st.column_config.NumberColumn(
                    "Volume 24h",
                    format="$%,.0f"
                ),
                "Opportunità": st.column_config.ProgressColumn(
                    "Opportunità",
                    min_value=0,
                    max_value=100,
                    format="%.1f"
                ),
                "Rischio": st.column_config.ProgressColumn(
                    "Rischio",
                    min_value=0,
                    max_value=100,
                    format="%.1f"
                ),
                "Confidenza dati": st.column_config.NumberColumn(
                    "Confidenza Dati",
                    format="%.1f%%"
                ),
            },
            use_container_width=True,
            hide_index=True
        )

        if reports:
            st.divider()
            st.subheader("Analisi Dettagliata Asset")

            ids = [r["candidate"].id for r in reports]
            selected = st.selectbox("Seleziona asset da analizzare", ids)

            report = next(
                r for r in reports
                if r["candidate"].id == selected
            )

            c = report["candidate"]

            col1, col2, col3 = st.columns(3)
            col1.metric("Score Opportunità", report["opportunity"])
            col2.metric("Livello Rischio", report["risk"])
            col3.metric("Confidenza Dati", f"{report['confidence']}%")

            st.write(f"### {c.name} ({c.symbol})")
            st.write(f"**Prezzo**: {format_price(c.price)}")
            st.write(f"**Market Cap**: ${c.market_cap:,.0f}")
            st.write(f"**FDV**: ${c.fdv:,.0f}")

            detail = pd.DataFrame([{
                "Agente": a.agent,
                "Score": a.score,
                "Confidenza": a.confidence,
                "Segnali / Avvertenze": "; ".join(a.flags) or "Nessuno"
            } for a in report["results"]])

            st.dataframe(
                detail,
                column_config={
                    "Score": st.column_config.ProgressColumn(
                        "Score",
                        min_value=0,
                        max_value=100,
                        format="%.0f"
                    ),
                    "Confidenza": st.column_config.NumberColumn(
                        "Confidenza Agente",
                        format="%.2f"
                    ),
                },
                use_container_width=True,
                hide_index=True
            )

            st.warning(
                "Uno score elevato non è una previsione di rendimento. "
                "Gli agenti Developer, On-chain e Security hanno ancora "
                "dati incompleti: controlla le relative avvertenze."
            )

    except requests.RequestException as e:
        st.error(
            "Impossibile recuperare i dati da CoinGecko. "
            f"Verifica la connessione o l'API Key. Dettaglio: {e}"
        )
    except Exception as e:
        st.error(f"Errore durante l'esecuzione dello Swarm: {e}")

else:
    st.info("Premi «Avvia scansione» per analizzare il mercato.")
    st.markdown("""
    **Agenti inclusi nello Swarm**
    - **Market**: Analizza variazioni di prezzo a 24h e 7d e ratio volume/market cap.
    - **Tokenomics**: Valuta la diluizione futura basandosi sul rapporto Market Cap / FDV.
    - **Liquidity**: Rileva volumi ridotti e anomalie nel turnover.
    - **Developer**: Monitora l'attività su GitHub *(dati simulati in attesa di API)*.
    - **On-chain**: Valuta dati sulla blockchain *(in attesa di provider)*.
    - **Contrarian**: Identifica segnali di surriscaldamento del prezzo/volume.
    - **Security**: Evidenzia rischi su smart contract e concentrazione di token.
    - **Quant Aggregator**: Combina i punteggi ponderati per calcolare Opportunità e Rischio.
    """)
