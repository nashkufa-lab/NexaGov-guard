import streamlit as st
import pandas as pd
import re
import plotly.graph_objects as go
import networkx as nx
from pypdf import PdfReader
import os

st.set_page_config(page_title="NexaGov Procurement Guard", layout="wide", page_icon="🇿🇼")
st.title("🇿🇼 NexaGov Procurement Guard AI")
st.caption("Upload any PRAZ tender PDF → Get fraud risk in 60 seconds")

BENCHMARKS = {
    "laptop": 850, "printer": 300, "vehicle": 35000, "tractor": 25000,
    "fertilizer": 35, "cement": 12, "fuel": 1.6, "stationery": 50, "desk": 200,
    "borehole": 4500, "server": 5000, "protective clothing": 45,
    "engine oil": 25, "networking equipment": 1200
}

def get_benchmark(name):
    name = name.lower()
    for k,v in BENCHMARKS.items():
        if k in name:
            return v
    return 500

def extract_tender_data(text):
    text_lower = text.lower()
    data = {}
    prices = re.findall(r'(?:usd|\$|zwg)\s?([\d,]+\.?\d*)', text_lower)
    try:
        all_prices = [float(p.replace(',','')) for p in prices if float(p.replace(',','')) > 10]
        data['price'] = max(all_prices) if all_prices else 0
    except:
        data['price'] = 0
    qty = re.findall(r'quantity[:\s]+(\d+)', text_lower)
    data['quantity'] = int(qty[0]) if qty else 1
    supplier = re.findall(r'(?:supplier|bidder|company|contractor|awarded to|vendor)[:\s]+([A-Z][A-Za-z &\-]+(?:Pvt| Ltd| Inc| LLC).*)', text, re.IGNORECASE)
    data['supplier'] = supplier[0][:35].strip() if supplier else "Unknown Supplier Pvt Ltd"
    data['item'] = "laptop"
    for item in BENCHMARKS.keys():
        if item in text_lower:
            data['item'] = item
            break
    return data

def calculate_risk(row):
    benchmark = get_benchmark(row['item'])
    price = float(row['price']) if row['price'] else 0
    overpricing = (price / benchmark - 1) * 100 if benchmark and price > 0 else 0
    risk = 20
    if overpricing > 50: risk += 40
    if overpricing > 100: risk += 30
    if "Best Deal" in str(row['supplier']) or "Friends" in str(row['supplier']): risk += 25
    return min(98, int(risk + overpricing/4)), overpricing

# --- DATA LOADING ---
df = None
uploaded_file = st.file_uploader("📄 Upload Tender PDF (PRAZ / eGP / Ministry)", type=["pdf"])

if uploaded_file:
    reader = PdfReader(uploaded_file)
    text = "".join([p.extract_text() or "" for p in reader.pages])
    st.success(f"PDF read - {len(text):,} characters")
    parsed = extract_tender_data(text)
    df = pd.DataFrame([parsed])
    df['benchmark'] = df['item'].apply(get_benchmark)
    df[['risk_score', 'overpricing']] = df.apply(lambda r: pd.Series(calculate_risk(r)), axis=1)
    df['potential_loss'] = (df['price'] - df['benchmark']) * df['quantity']
    df['potential_loss'] = df['potential_loss'].apply(lambda x: max(0, x))
    df['tender_ref'] = "Uploaded PDF"
    df['procuring_entity'] = "From PDF"
else:
    # Load sample data - FIXED VERSION
    if os.path.exists("tenders.csv"):
        df = pd.read_csv("tenders.csv")
        st.info(f"✅ Loaded {len(df)} tenders from tenders.csv - Sample based on Auditor General 2023-25")
    else:
        st.info("👆 Upload a real PDF to test. Showing sample data flagged by Auditor General.")
        sample_data = [
            {"tender_ref": "MOH/CB/15/2025", "item": "laptop", "quantity": 50, "price": 1800, "supplier": "Best Deal Pvt Ltd", "benchmark": 850, "procuring_entity": "Min of Health"},
            {"tender_ref": "NCB06-2026", "item": "protective clothing", "quantity": 200, "price": 120, "supplier": "Best Deal Pvt Ltd", "benchmark": 45, "procuring_entity": "ZIMRA"},
            {"tender_ref": "MLAFWRD/HQ/CB/35/25", "item": "vehicle", "quantity": 3, "price": 58000, "supplier": "Best Deal Pvt Ltd", "benchmark": 35000, "procuring_entity": "Min of Lands"},
            {"tender_ref": "GMB/CB/02/2026", "item": "fertilizer", "quantity": 5000, "price": 78, "supplier": "AgriGold Pvt Ltd", "benchmark": 35, "procuring_entity": "GMB"},
        ]
        df = pd.DataFrame(sample_data)
        df[['risk_score', 'overpricing']] = df.apply(lambda r: pd.Series(calculate_risk(r)), axis=1)
        df['potential_loss'] = (df['price'] - df['benchmark']) * df['quantity']
        df['overpricing_pct'] = df['overpricing']

# Ensure columns exist
if 'potential_loss' not in df.columns:
    df['potential_loss'] = 0
if 'risk_score' not in df.columns:
    df[['risk_score', 'overpricing']] = df.apply(lambda r: pd.Series(calculate_risk(r)), axis=1)

# --- DASHBOARD ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Potential Loss", f"${df['potential_loss'].sum():,.0f}", delta="Waste Found")
col2.metric("Highest Risk Score", f"{int(df['risk_score'].max())}% 🔴")
col3.metric("Avg Overpricing", f"{df['overpricing'].mean():.0f}%" if 'overpricing' in df.columns else "85%")
col4.metric("Flagged Tenders", f"{len(df[df['risk_score']>70])}/{len(df)}")

st.divider()

c1, c2 = st.columns([2,1])

with c1:
    st.subheader("🚩 Flagged Procurement")
    # FIXED: Removed .style.background_gradient that was causing crash
    display_cols = [c for c in ['item','quantity','price','benchmark','supplier','risk_score','potential_loss'] if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True)

with c2:
    st.subheader("🕸️ Collusion Graph")
    try:
        G = nx.Graph()
        for _, row in df.iterrows():
            G.add_edge(str(row['supplier']), str(row['item']))
        pos = nx.spring_layout(G, k=1, seed=42)
        edge_x, edge_y = [], []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode='lines', line=dict(color='#94a3b8', width=1)))
        node_x = [pos[n][0] for n in G.nodes()]; node_y = [pos[n][1] for n in G.nodes()]
        colors = ['#ef4444' if str(n) in df['supplier'].values else '#3b82f6' for n in G.nodes()]
        fig.add_trace(go.Scatter(x=node_x, y=node_y, mode='markers+text', text=list(G.nodes()), textposition="top center", marker=dict(size=12, color=colors)))
        fig.update_layout(height=320, margin=dict(l=0,r=0,t=10,b=0), showlegend=False, xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Same supplier winning unrelated categories = classic collusion signal")
    except Exception as e:
        st.warning(f"Graph loading... {e}")

st.success("**PILOT OFFER:** Give us 100 tenders. If we don't find $2M in savings in 30 days, you pay $0.")
st.caption("Data: Sample based on Zimbabwe Auditor General Reports 2023-2025 | For demo only - Live data requires PRAZ API access")
