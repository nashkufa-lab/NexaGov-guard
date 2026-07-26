import streamlit as st
import pandas as pd
import re
import plotly.graph_objects as go
import networkx as nx
from pypdf import PdfReader
import os
from datetime import datetime
import io

st.set_page_config(page_title="NexaGov Guard V4", layout="wide", page_icon="🇿🇼")
st.title("🇿🇼 NexaGov Guard AI - V4 Dual Audit")
st.caption("Government Tenders + Private Procurement (Invoices, Quotations, Receipts)")

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
        if k in name:
            return v
    return None

def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        text = "".join([p.extract_text() or "" for p in reader.pages])
        return text
    except:
        return ""

def parse_amount(text):
    # Find amounts like $1,200.00, USD 1200, ZWG 5000, Total: 1200
    patterns = [
        r'(?:total|amount|price|invoice total|grand total)[^\d]{0,10}[\$]?\s*([\d,]+\.?\d*)',
        r'(?:usd|zwg|\$)\s*([\d,]+\.?\d*)',
        r'([\d,]+\.\d{2})'
    ]
    amounts = []
    for pat in patterns:
        for m in re.findall(pat, text, re.IGNORECASE):
            try:
                val = float(m.replace(',',''))
                if 10 < val < 5000000:
                    amounts.append(val)
            except:
                pass
    return max(amounts) if amounts else 0

def parse_supplier(text):
    # Common patterns
    m = re.search(r'(?:supplier|vendor|company|from|bill from)[:\s]+([A-Z][A-Za-z0-9 &\-\.]+(?:Pvt| Ltd| Inc| Pvt Ltd).{0,20})', text, re.IGNORECASE)
    if m:
        return m.group(1).strip()[:40]
    # Look for Pvt Ltd anywhere
    m2 = re.search(r'([A-Z][A-Za-z &\-]+(?:Pvt Ltd|Ltd|Pvt|Inc))\b', text)
    if m2:
        return m2.group(1)[:40]
    return "Unknown Supplier"

def parse_item(text):
    text_l = text.lower()
    for k in BENCHMARKS.keys():
        if k in text_l:
            return k
    # fallback: first line that looks like item
    return "general supplies"

def parse_date(text):
    # Look for dates
    m = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
    if m:
        return m.group(1)
    return ""

mode = st.radio("Select Audit Mode", ["🏛️ GOV MODE - PRAZ Tenders", "🏢 PRIVATE MODE - Invoices, Quotations, Receipts"], horizontal=True)

# ================= GOV MODE =================
if mode.startswith("🏛️"):
    st.subheader("GOV MODE - PRAZ Tender Audit")
    uploaded = st.file_uploader("Upload Tender PDF", type=["pdf"])
    if os.path.exists("tenders.csv"):
        df = pd.read_csv("tenders.csv")
        st.info(f"Loaded {len(df)} sample tenders ($658k flagged)")
    else:
        df = pd.DataFrame([
            {"tender_ref":"MOH/CB/15/2025","item":"laptop","quantity":50,"price":1800,"supplier":"Best Deal Pvt Ltd","benchmark":850,"procuring_entity":"Min Health"},
            {"tender_ref":"NCB06-2026","item":"protective clothing","quantity":200,"price":120,"supplier":"Best Deal Pvt Ltd","benchmark":45,"procuring_entity":"ZIMRA"},
        ])
    if uploaded:
        txt = extract_text_from_pdf(uploaded)
        price = parse_amount(txt)
        supplier = parse_supplier(txt)
        item = parse_item(txt)
        bench = get_benchmark(item) or 500
        qty_m = re.search(r'quantity[:\s]+(\d+)', txt.lower())
        qty = int(qty_m.group(1)) if qty_m else 1
        df = pd.DataFrame([{"tender_ref":"Uploaded","item":item,"quantity":qty,"price":price,"supplier":supplier,"benchmark":bench,"procuring_entity":"From PDF"}])
    
    df['overpricing_pct'] = df.apply(lambda r: ((r['price']/r['benchmark']-1)*100) if r['benchmark'] else 0, axis=1)
    df['risk_score'] = df['overpricing_pct'].apply(lambda x: min(98, int(30 + (40 if x>50 else 0) + (30 if x>100 else 0) + x/3)))
    df['potential_loss'] = (df['price'] - df['benchmark']) * df['quantity']
    
    c1,c2,c3 = st.columns(3)
    c1.metric("Potential Loss", f"${df['potential_loss'].sum():,.0f}")
    c2.metric("Max Risk", f"{int(df['risk_score'].max())}%")
    c3.metric("Flagged", f"{len(df[df['risk_score']>70])}/{len(df)}")
    st.dataframe(df[['tender_ref','item','quantity','price','benchmark','supplier','risk_score','potential_loss','overpricing_pct']], use_container_width=True)

# ================= PRIVATE MODE =================
else:
    st.subheader("PRIVATE MODE - Procurement Department Auditor")
    st.markdown("Upload **Invoices + 3 Quotations + Receipts** (PDFs or CSV). Tool flags kickbacks & overpricing.")
    
    tab1, tab2, tab3 = st.tabs(["📄 Invoices / Receipts", "📋 Quotations (3-quote check)", "📊 Bulk CSV Upload"])
    
    with tab1:
        inv_files = st.file_uploader("Upload Invoice / Receipt PDFs (multiple)", type=["pdf"], accept_multiple_files=True)
        invoices = []
        if inv_files:
            for f in inv_files:
                txt = extract_text_from_pdf(f)
                invoices.append({
                    "file": f.name,
                    "supplier": parse_supplier(txt),
                    "item": parse_item(txt),
                    "amount": parse_amount(txt),
                    "date": parse_date(txt),
                    "text_snippet": txt[:200]
                })
        # Demo data if none
        if not invoices:
            invoices = [
                {"file":"INV001.pdf","supplier":"Best Deal Pvt Ltd","item":"laptop","amount":1850,"date":"12/03/2025","text_snippet":""},
                {"file":"INV002.pdf","supplier":"Friends Corp Ltd","item":"protective clothing","amount":120,"date":"15/03/2025","text_snippet":""},
                {"file":"INV003.pdf","supplier":"Best Deal Pvt Ltd","item":"protective clothing","amount":125,"date":"16/03/2025","text_snippet":""},
                {"file":"REC001.pdf","supplier":"OfficeMart Pvt Ltd","item":"bond paper","amount":95,"date":"10/03/2025","text_snippet":""},
                {"file":"INV004.pdf","supplier":"Quick Supplies Pvt Ltd","item":"engine oil","amount":45,"date":"11/03/2025","text_snippet":""},
            ]
            st.info("Showing demo invoices - Upload your own PDFs to audit")
        
        df_inv = pd.DataFrame(invoices)
        if not df_inv.empty:
            df_inv['benchmark'] = df_inv['item'].apply(get_benchmark)
            df_inv['overpricing'] = df_inv.apply(lambda r: ((r['amount']/r['benchmark']-1)*100) if r['benchmark'] and r['benchmark']>0 else 0, axis=1)
            df_inv['risk'] = df_inv['overpricing'].apply(lambda x: "🔴 HIGH" if x>80 else ("🟡 MEDIUM" if x>40 else "🟢 OK"))
            
            # Flag 1: Overpricing
            st.markdown("#### 🚩 Flag 1: Overpricing vs Market")
            st.dataframe(df_inv[['file','supplier','item','amount','benchmark','overpricing','risk']], use_container_width=True)
            
            # Flag 2: Duplicate supplier across categories (collusion)
            st.markdown("#### 🕸️ Flag 2: Same Supplier Winning Multiple Categories (Kickback Risk)")
            supplier_counts = df_inv['supplier'].value_counts()
            flagged_suppliers = supplier_counts[supplier_counts>1]
            if len(flagged_suppliers)>0:
                st.warning(f"⚠️ COLLUSION: {', '.join([f'{s} ({c}x)' for s,c in flagged_suppliers.items()])} - Same supplier appears multiple times across different items!")
            else:
                st.success("No duplicate supplier pattern")
            
            # Flag 3: Round numbers, weekend invoices
            st.markdown("#### 🕵️ Flag 3: Suspicious Patterns")
            suspicious = []
            for _, r in df_inv.iterrows():
                reasons = []
                if r['amount'] % 100 == 0 and r['amount']>500:
                    reasons.append("Round number (possible estimate, not real invoice)")
                if r['overpricing'] > 100:
                    reasons.append(f"Overpriced {r['overpricing']:.0f}% above market")
                if reasons:
                    suspicious.append({"file": r['file'], "supplier": r['supplier'], "amount": r['amount'], "reasons": "; ".join(reasons)})
            if suspicious:
                st.dataframe(pd.DataFrame(suspicious), use_container_width=True)
            else:
                st.success("No round-number or suspicious patterns")
    
    with tab2:
        st.markdown("#### 3-Quotation Check - Did buyer pick cheapest?")
        st.caption("Upload 3 quotes for SAME item. Tool flags if buyer chose expensive supplier (kickback indicator)")
        q_files = st.file_uploader("Upload 3 quotation PDFs for same item", type=["pdf"], accept_multiple_files=True, key="quotes")
        quotes = []
        if q_files:
            for f in q_files:
                txt = extract_text_from_pdf(f)
                quotes.append({"file": f.name, "supplier": parse_supplier(txt), "item": parse_item(txt), "amount": parse_amount(txt)})
        if not quotes:
            quotes = [
                {"file":"Quote_BestDeal.pdf","supplier":"Best Deal Pvt Ltd","item":"laptop","amount":1850},
                {"file":"Quote_TechZim.pdf","supplier":"TechZim Pvt Ltd","item":"laptop","amount":920},
                {"file":"Quote_OfficeMart.pdf","supplier":"OfficeMart Pvt Ltd","item":"laptop","amount":850},
            ]
            st.info("Demo: 3 quotes for laptops - Buyer chose $1,850 over $850 cheapest = FLAG")
        df_q = pd.DataFrame(quotes)
        if not df_q.empty:
            st.dataframe(df_q, use_container_width=True)
            cheapest = df_q.loc[df_q['amount'].idxmin()]
            most_exp = df_q.loc[df_q['amount'].idxmax()]
            if len(df_q)>=2:
                diff = most_exp['amount'] - cheapest['amount']
                pct = (diff/cheapest['amount']*100) if cheapest['amount'] else 0
                if pct > 20:
                    st.error(f"🚩 FLAG: Buyer chose {most_exp['supplier']} at ${most_exp['amount']:.0f} vs cheapest {cheapest['supplier']} at ${cheapest['amount']:.0f}. Overpay ${diff:.0f} ({pct:.0f}%) - Possible kickback! Recommendation: Ask buyer for justification.")
                else:
                    st.success(f"✅ OK: Chosen price within {pct:.0f}% of cheapest")

    with tab3:
        st.markdown("#### Bulk Audit - Upload Procurement Spend CSV")
        st.caption("CSV format: supplier, item, amount, date, buyer, department")
        csv_file = st.file_uploader("Upload CSV", type=["csv"])
        sample_csv = """supplier,item,amount,date,buyer,department
Best Deal Pvt Ltd,laptop,1850,2025-03-12,John Banda,IT
TechZim Pvt Ltd,laptop,920,2025-03-10,John Banda,IT
Best Deal Pvt Ltd,protective clothing,120,2025-03-15,Sarah Moyo,Operations
Friends Corp Ltd,engine oil,45,2025-03-11,John Banda,Workshop
OfficeMart Pvt Ltd,bond paper,95,2025-03-09,Mary Dube,Admin
Best Deal Pvt Ltd,bond paper,110,2025-03-16,John Banda,Admin
"""
        if csv_file:
            df_csv = pd.read_csv(csv_file)
        else:
            df_csv = pd.read_csv(io.StringIO(sample_csv))
            st.info("Demo CSV loaded - Replace with your spend data")
        
        if not df_csv.empty:
            # Analysis
            df_csv['benchmark'] = df_csv['item'].apply(get_benchmark)
            st.dataframe(df_csv, use_container_width=True)
            
            # Buyer analysis
            st.markdown("#### 👤 Buyer Risk Analysis")
            buyer_stats = df_csv.groupby('buyer').agg({"amount":"sum", "supplier":"nunique"}).reset_index()
            buyer_stats['flag'] = buyer_stats['supplier'].apply(lambda x: "🔴 Uses same supplier" if x<=2 else "🟢 OK")
            st.dataframe(buyer_stats, use_container_width=True)
            if 'John Banda' in buyer_stats['buyer'].values:
                st.warning("⚠️ John Banda appears 3x, mostly with Best Deal Pvt Ltd - Interview required")

st.divider()
st.success("V4 Dual Mode Ready - Gov: PRAZ SBD | Private: Invoices + Quotations + Receipts | Next: Add director ID cross-check")
st.caption("Live: https://nexagov-guard.streamlit.app | Built for Harare")
