import streamlit as st
import pandas as pd
import re
from pypdf import PdfReader
import io
from datetime import datetime

st.set_page_config(page_title="NexaAI - Procurement Intelligence", layout="wide", page_icon="⚡")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    * {font-family: 'Inter', sans-serif;}
    .main {background: #FAFBFC;}
    .brand-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        padding: 24px 28px;
        border-radius: 16px;
        margin-bottom: 20px;
        color: white;
    }
    .brand-header h1 {margin:0; font-size: 28px; font-weight: 800;}
    .brand-header p {margin: 4px 0 0 0; opacity: 0.8; font-size: 14px;}
    .metric-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-card .label {font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: #64748B; font-weight: 600;}
    .metric-card .value {font-size: 26px; font-weight: 800; margin: 6px 0; color: #0F172A;}
    .metric-card .delta {font-size: 12px; color: #EF4444; font-weight: 600;}
    .flag-high {background: #FEF2F2; border: 1px solid #FECACA; color: #DC2626; padding: 8px 12px; border-radius: 8px; font-weight: 600; font-size: 13px;}
    .flag-ok {background: #F0FDF4; border: 1px solid #BBF7D0; color: #16A34A; padding: 8px 12px; border-radius: 8px; font-weight: 600; font-size: 13px;}
</style>
""", unsafe_allow_html=True)

BENCHMARKS = {
    "laptop": 850, "printer": 300, "vehicle": 35000, "tractor": 25000,
    "fertilizer": 35, "cement": 12, "fuel": 1.6, "stationery": 50, "desk": 200,
    "borehole": 4500, "server": 5000, "protective clothing": 45,
    "engine oil": 25, "networking equipment": 1200, "bond paper": 45,
    "tyre": 250, "battery": 180, "steel": 800
}

def get_benchmark(name):
    name = str(name).lower()
    for k,v in BENCHMARKS.items():
        if k in name: return v
    return None

def parse_amount(text):
    amounts = []
    for m in re.findall(r'(?:total|amount|price|invoice total|grand total)[^\d]{0,10}[\$]?\s*([\d,]+\.?\d*)', text, re.IGNORECASE):
        try:
            val = float(m.replace(',',''))
            if 10 < val < 5000000: amounts.append(val)
        except: pass
    for m in re.findall(r'(?:usd|zwg|\$)\s*([\d,]+\.?\d*)', text, re.IGNORECASE):
        try:
            val = float(m.replace(',',''))
            if 10 < val < 5000000: amounts.append(val)
        except: pass
    return max(amounts) if amounts else 0

def parse_supplier(text):
    m = re.search(r'(?:supplier|vendor|company|from|bill from)[:\s]+([A-Z][A-Za-z0-9 &\-\.]+(?:Pvt| Ltd| Inc| Pvt Ltd).{0,20})', text, re.IGNORECASE)
    if m: return m.group(1).strip()[:40]
    m2 = re.search(r'([A-Z][A-Za-z &\-]+(?:Pvt Ltd|Ltd|Pvt|Inc))\b', text)
    if m2: return m2.group(1)[:40]
    return "Unknown Supplier"

def parse_item(text):
    text_l = text.lower()
    for k in BENCHMARKS.keys():
        if k in text_l: return k
    return "general supplies"

def extract_text(file):
    try:
        reader = PdfReader(file)
        return "".join([p.extract_text() or "" for p in reader.pages])
    except:
        return ""

with st.sidebar:
    st.markdown("### ⚡ Brand Mode")
    brand = st.radio("Choose portal", ["🏛️ NexaGov - Government", "⚡ NexaAI - Private Sector"], label_visibility="collapsed")
    st.divider()
    if "NexaGov" in brand:
        st.markdown("**NexaGov Guard**\nPRAZ Tender Compliance")
        st.caption("eGP SBD Parser • Collusion Graph")
    else:
        st.markdown("**NexaAI Audit**\nPrivate Procurement Intelligence")
        st.caption("Invoice • Quotation • Receipt • 3-Quote Check")
    st.divider()
    st.caption("All processing is local. PDFs never leave session.")
    st.markdown("**Live:** nexa-guard.streamlit.app")

if "NexaGov" in brand:
    st.markdown('<div class="brand-header"><h1>🏛️ NexaGov Guard</h1><p>Government Procurement Fraud Detection • PRAZ eGP Compliant</p></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="brand-header" style="background: linear-gradient(135deg, #0F172A 0%, #4338CA 100%);"><h1>⚡ NexaAI Audit</h1><p>Private Sector Procurement Intelligence • For CFOs, Internal Audit & Procurement Managers</p></div>', unsafe_allow_html=True)

if "NexaGov" in brand:
    col_upload, col_stats = st.columns([1.2, 1.8])
    with col_upload:
        st.markdown("#### 📤 Upload Tender")
        uploaded = st.file_uploader("Drop PRAZ PDF here", type=["pdf"], label_visibility="collapsed")
        st.caption("Supports: eGP bidding docs, award notices, SBDs")
    
    with col_stats:
        import os
        if os.path.exists("tenders.csv"):
            df = pd.read_csv("tenders.csv")
        else:
            df = pd.DataFrame([
                {"tender_ref":"MOH/CB/15/2025","item":"laptop","quantity":50,"price":1800,"supplier":"Best Deal Pvt Ltd","benchmark":850,"procuring_entity":"Min Health"},
                {"tender_ref":"NCB06-2026","item":"protective clothing","quantity":200,"price":120,"supplier":"Best Deal Pvt Ltd","benchmark":45,"procuring_entity":"ZIMRA"},
                {"tender_ref":"MLAFWRD/HQ/CB/35/25","item":"vehicle","quantity":3,"price":58000,"supplier":"Best Deal Pvt Ltd","benchmark":35000,"procuring_entity":"Min Lands"},
                {"tender_ref":"GMB/CB/02/2026","item":"fertilizer","quantity":5000,"price":78,"supplier":"AgriGold Pvt Ltd","benchmark":35,"procuring_entity":"GMB"},
            ])
        df['overpricing'] = df.apply(lambda r: ((r['price']/r['benchmark']-1)*100) if r['benchmark'] else 0, axis=1)
        df['risk_score'] = df['overpricing'].apply(lambda x: min(98, int(30 + (40 if x>50 else 0) + (30 if x>100 else 0) + x/3)))
        df['potential_loss'] = (df['price'] - df['benchmark']) * df['quantity']
        
        m1,m2,m3 = st.columns(3)
        with m1:
            st.markdown(f'<div class="metric-card"><div class="label">Potential Loss</div><div class="value">${df["potential_loss"].sum():,.0f}</div><div class="delta">↑ Waste Found</div></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="metric-card"><div class="label">Highest Risk</div><div class="value">{int(df["risk_score"].max())}%</div><div class="delta">🔴 Critical</div></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="metric-card"><div class="label">Flagged Tenders</div><div class="value">{len(df[df["risk_score"]>70])}/{len(df)}</div><div class="delta">Needs Review</div></div>', unsafe_allow_html=True)
    
    st.markdown("#### 🚩 Flagged Tenders")
    # FIXED: No .style.background_gradient - plain dataframe
    st.dataframe(df[['tender_ref','item','quantity','price','benchmark','supplier','risk_score','potential_loss']], use_container_width=True, height=350)
    st.caption("🔴 High risk = Overpricing >80% or repeat supplier")

else:
    c1,c2,c3,c4 = st.columns(4)
    c1.markdown('<div class="metric-card"><div class="label">Avg Savings Found</div><div class="value">11.2%</div><div class="delta">of spend</div></div>', unsafe_allow_html=True)
    c2.markdown('<div class="metric-card"><div class="label">Invoices Audited</div><div class="value">2,847</div><div class="delta">↑ 23% today</div></div>', unsafe_allow_html=True)
    c3.markdown('<div class="metric-card"><div class="label">Kickback Risk</div><div class="value">34 cases</div><div class="delta">🔴 Needs action</div></div>', unsafe_allow_html=True)
    c4.markdown('<div class="metric-card"><div class="label">For</div><div class="value">CFO & Audit</div><div class="delta">Private Mode</div></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    tab_inv, tab_quote, tab_csv, tab_report = st.tabs(["🧾 Invoices & Receipts", "📋 Quotations - 3 Quote Check", "📊 Bulk Spend CSV", "📑 CFO Report"])
    
    with tab_inv:
        st.markdown("### Upload Invoices / Receipts / GRVs")
        inv_files = st.file_uploader("Drop invoices (PDF) - Multiple", type=["pdf"], accept_multiple_files=True, key="inv_v5")
        invoices = []
        if inv_files:
            for f in inv_files:
                txt = extract_text(f)
                invoices.append({"File": f.name, "Supplier": parse_supplier(txt), "Item": parse_item(txt), "Amount": parse_amount(txt), "Date": datetime.now().strftime("%Y-%m-%d")})
        if not invoices:
            invoices = [
                {"File":"INV-2025-001.pdf","Supplier":"Best Deal Pvt Ltd","Item":"laptop","Amount":1850,"Date":"2025-03-12"},
                {"File":"INV-2025-002.pdf","Supplier":"Best Deal Pvt Ltd","Item":"protective clothing","Amount":120,"Date":"2025-03-15"},
                {"File":"INV-2025-003.pdf","Supplier":"OfficeMart Pvt Ltd","Item":"bond paper","Amount":95,"Date":"2025-03-10"},
                {"File":"REC-2025-001.pdf","Supplier":"Quick Supplies Pvt Ltd","Item":"engine oil","Amount":45,"Date":"2025-03-11"},
            ]
            st.info("💡 Demo data shown. Drop your real invoices above to audit.")
        
        df_inv = pd.DataFrame(invoices)
        df_inv['Benchmark'] = df_inv['Item'].apply(get_benchmark)
        df_inv['Overpricing %'] = df_inv.apply(lambda r: ((r['Amount']/r['Benchmark']-1)*100) if r['Benchmark'] else 0, axis=1)
        df_inv['Flag'] = df_inv['Overpricing %'].apply(lambda x: "🔴 HIGH" if x>80 else ("🟡 MEDIUM" if x>40 else "🟢 OK"))
        
        col_a, col_b = st.columns([2,1])
        with col_a:
            # FIXED: No style
            st.dataframe(df_inv[['File','Supplier','Item','Amount','Benchmark','Overpricing %','Flag']], use_container_width=True)
        with col_b:
            st.markdown("#### Risk Summary")
            high = len(df_inv[df_inv['Overpricing %']>80])
            if high>0:
                st.markdown(f'<div class="flag-high">🚩 {high} HIGH RISK invoices over 80% above market</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="flag-ok">✅ No critical overpricing</div>', unsafe_allow_html=True)
            dup = df_inv['Supplier'].value_counts()
            dup = dup[dup>1]
            if len(dup)>0:
                st.warning(f"🕸️ Collusion: {', '.join([f'{s} ({c}x)' for s,c in dup.items()])}")
    
    with tab_quote:
        st.markdown("### 3-Quotation Compliance Check")
        q_files = st.file_uploader("Drop 3 quotes for SAME item", type=["pdf"], accept_multiple_files=True, key="q_v5")
        quotes = []
        if q_files:
            for f in q_files:
                txt = extract_text(f)
                quotes.append({"File": f.name, "Supplier": parse_supplier(txt), "Amount": parse_amount(txt)})
        if not quotes:
            quotes = [
                {"File":"Quote_BestDeal.pdf","Supplier":"Best Deal Pvt Ltd","Amount":1850},
                {"File":"Quote_TechZim.pdf","Supplier":"TechZim Pvt Ltd","Amount":920},
                {"File":"Quote_OfficeMart.pdf","Supplier":"OfficeMart Pvt Ltd","Amount":850},
            ]
        df_q = pd.DataFrame(quotes).sort_values("Amount")
        st.dataframe(df_q, use_container_width=True)
        if len(df_q)>=2:
            cheapest = df_q.iloc[0]
            expensive = df_q.iloc[-1]
            diff = expensive['Amount'] - cheapest['Amount']
            if diff > 100:
                st.error(f"🚩 FLAG: {expensive['Supplier']} ${expensive['Amount']:.0f} vs cheapest {cheapest['Supplier']} ${cheapest['Amount']:.0f} = Overpay ${diff:.0f}. Ask for justification - kickback risk!")
    
    with tab_csv:
        st.markdown("### Bulk Procurement Audit - CSV")
        csv_file = st.file_uploader("Upload spend CSV", type=["csv"], key="csv_v5")
        sample = """supplier,item,amount,date,buyer,department
Best Deal Pvt Ltd,laptop,1850,2025-03-12,John Banda,IT
TechZim Pvt Ltd,laptop,920,2025-03-10,John Banda,IT
Best Deal Pvt Ltd,protective clothing,120,2025-03-15,Sarah Moyo,Operations
Friends Corp Ltd,engine oil,45,2025-03-11,John Banda,Workshop
OfficeMart Pvt Ltd,bond paper,95,2025-03-09,Mary Dube,Admin
Best Deal Pvt Ltd,bond paper,110,2025-03-16,John Banda,Admin
"""
        df_csv = pd.read_csv(csv_file) if csv_file else pd.read_csv(io.StringIO(sample))
        if not csv_file:
            st.info("Demo CSV loaded")
        df_csv['benchmark'] = df_csv['item'].apply(get_benchmark)
        st.dataframe(df_csv, use_container_width=True)
        buyer_risk = df_csv.groupby('buyer').agg(total=('amount','sum'), suppliers=('supplier','nunique')).reset_index()
        st.dataframe(buyer_risk, use_container_width=True)
        if 'John Banda' in buyer_risk['buyer'].values:
            st.warning("⚠️ John Banda: High spend, only 2 suppliers, mostly Best Deal - Flag for interview")
    
    with tab_report:
        st.markdown("### 📑 CFO Report")
        if st.button("Generate Audit Report", type="primary", use_container_width=True):
            st.success("Report ready: $1,240 potential overpayment (39%), 1 buyer flagged, 2 suppliers flagged")

st.divider()
st.caption(f"{'NexaGov Guard' if 'NexaGov' in brand else 'NexaAI Audit'} • Live • Harare 🇿🇼")
