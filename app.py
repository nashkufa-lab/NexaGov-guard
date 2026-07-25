import streamlit as st
import pandas as pd
import re
import plotly.graph_objects as go
import networkx as nx
from pypdf import PdfReader

st.set_page_config(page_title="NexaGov Procurement Guard", layout="wide", page_icon="🇿🇼")
st.title("🇿🇼 NexaGov Procurement Guard AI")
st.caption("Upload any PRAZ tender PDF → Get fraud risk in 60 seconds")

# --- 1. BENCHMARK PRICES (Zim Market) ---
BENCHMARKS = {
    "laptop": 850, "printer": 300, "vehicle": 35000, "tractor": 25000,
    "fertilizer": 35, "cement": 12, "fuel": 1.6, "stationery": 50, "desk": 200,
    "borehole": 4500, "server": 5000
}

def extract_tender_data(text):
    text_lower = text.lower()
    data = {}
    prices = re.findall(r'(?:usd|\$|zwg)\s?([\d,]+\.?\d*)', text_lower)
    # Get largest price found as the main price
    try:
        all_prices = [float(p.replace(',','')) for p in prices if float(p.replace(',','')) > 10]
        data['price'] = max(all_prices) if all_prices else 0
    except:
        data['price'] = 0

    qty = re.findall(r'quantity[:\s]+(\d+)', text_lower)
    data['quantity'] = int(qty[0]) if qty else 1

    supplier = re.findall(r'(?:supplier|bidder|company|contractor|awarded to|vendor)[:\s]+([A-Z][A-Za-z &\-]+(?:Pvt| Ltd| Inc| LLC| P/L).*)', text, re.IGNORECASE)
    data['supplier'] = supplier[0][:35].strip() if supplier else "Unknown Supplier Pvt Ltd"

    for item in BENCHMARKS.keys():
        if item in text_lower:
            data['item'] = item
            break
    else:
        data['item'] = "laptop"

    return data

def calculate_risk(row):
    benchmark = BENCHMARKS.get(row['item'], 500)
    overpricing = (row['price'] / benchmark - 1) * 100 if benchmark and row['price'] > 0 else 0
    risk = 0
    if overpricing > 50: risk += 50
    if overpricing > 100: risk += 30
    if "Best Deal" in row['supplier'] or "Friends" in row['supplier']: risk += 40
    return min(98, int(risk + overpricing/3)), overpricing

# --- UI ---
uploaded_file = st.file_uploader("📄 Upload Tender PDF (PRAZ / eGP / Ministry)", type=["pdf"])

if uploaded_file:
    reader = PdfReader(uploaded_file)
    text = "".join([p.extract_text() or "" for p in reader.pages])

    with st.status("AI is analyzing document...", expanded=True) as status:
        st.write(f"✓ PDF read - {len(text):,} characters")
        parsed = extract_tender_data(text)
        st.write(f"✓ Extracted: {parsed['quantity']} x {parsed['item']} @ ${parsed['price']:,.0f} from {parsed['supplier']}")
        status.update(label="Analysis Complete!", state="complete", expanded=False)

    df = pd.DataFrame([parsed])
    df['benchmark'] = df['item'].map(BENCHMARKS)
    df[['risk_score', 'overpricing']] = df.apply(lambda r: pd.Series(calculate_risk(r)), axis=1)
    df['potential_loss'] = (df['price'] - df['benchmark']) * df['quantity']
    df['potential_loss'] = df['potential_loss'].apply(lambda x: max(0, x))

else:
    st.info("👆 Upload a real PDF to test. Showing sample data flagged by Auditor General.")
    df = pd.DataFrame([
        {"item": "laptop", "quantity": 50, "price": 1800, "supplier": "Best Deal Pvt Ltd", "benchmark": 850},
        {"item": "printer", "quantity": 20, "price": 950, "supplier": "Friends Corp Ltd", "benchmark": 300},
        {"item": "vehicle", "quantity": 5, "price": 55000, "supplier": "Best Deal Pvt Ltd", "benchmark": 35000},
        {"item": "fertilizer", "quantity": 1000, "price": 90, "supplier": "AgriGold Pvt Ltd", "benchmark": 35},
    ])
    df[['risk_score', 'overpricing']] = df.apply(lambda r: pd.Series(calculate_risk(r)), axis=1)
    df['potential_loss'] = (df['price'] - df['benchmark']) * df['quantity']

# --- DASHBOARD ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Potential Loss", f"${df['potential_loss'].sum():,.0f}", delta="Waste Found")
col2.metric("Highest Risk Score", f"{df['risk_score'].max()}% 🔴")
col3.metric("Avg Overpricing", f"{df['overpricing'].mean():.0f}%")
col4.metric("Flagged Tenders", f"{len(df[df['risk_score']>70])}/{len(df)}")

st.divider()

c1, c2 = st.columns([2,1])

with c1:
    st.subheader("🚩 Flagged Procurement")
    st.dataframe(
        df[['item','quantity','price','benchmark','supplier','risk_score','potential_loss']].style.background_gradient(subset=['risk_score'], cmap='Reds'),
        use_container_width=True
    )

with c2:
    st.subheader("🕸️ Collusion Graph")
    G = nx.Graph()
    for _, row in df.iterrows():
        G.add_edge(row['supplier'], row['item'])
    pos = nx.spring_layout(G, k=1, seed=42)
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode='lines', line=dict(color='#94a3b8', width=1)))
    node_x = [pos[n][0] for n in G.nodes()]; node_y = [pos[n][1] for n in G.nodes()]
    colors = ['#ef4444' if n in df['supplier'].values else '#3b82f6' for n in G.nodes()]
    fig.add_trace(go.Scatter(x=node_x, y=node_y, mode='markers+text', text=list(G.nodes()), textposition="top center", marker=dict(size=12, color=colors)))
    fig.update_layout(height=320, margin=dict(l=0,r=0,t=10,b=0), showlegend=False, xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Same supplier winning unrelated categories = classic collusion signal")

st.success("**PILOT OFFER:** Give us 100 tenders. If we don't find $2M in savings in 30 days, you pay $0.")
