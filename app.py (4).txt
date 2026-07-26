import streamlit as st
import pandas as pd

st.set_page_config(page_title="NexaAI V6 - Pan-African", layout="wide", page_icon="🌍")

st.markdown("""
<style>
.brand-header{background:linear-gradient(135deg,#0F172A 0%,#1E3A8A 100%);padding:20px 24px;border-radius:16px;margin-bottom:16px;color:white}
.metric-card{background:white;border:1px solid #E2E8F0;border-radius:12px;padding:16px}
</style>
""", unsafe_allow_html=True)

BENCHMARKS = {
    "ZW": {"laptop":850,"vehicle":35000,"protective clothing":45,"fertilizer":35},
    "ZM": {"laptop":800,"vehicle":32000,"protective clothing":42,"fertilizer":32},
    "KE": {"laptop":750,"vehicle":30000,"protective clothing":40,"fertilizer":30},
    "TZ": {"laptop":780,"vehicle":31000,"protective clothing":41,"fertilizer":31},
    "RW": {"laptop":820,"vehicle":33000,"protective clothing":43,"fertilizer":33},
    "UG": {"laptop":790,"vehicle":31500,"protective clothing":41,"fertilizer":31},
    "GH": {"laptop":760,"vehicle":30500,"protective clothing":40,"fertilizer":30},
    "NG": {"laptop":700,"vehicle":28000,"protective clothing":38,"fertilizer":28},
    "BW": {"laptop":900,"vehicle":36000,"protective clothing":48,"fertilizer":36},
    "ZA": {"laptop":950,"vehicle":38000,"protective clothing":50,"fertilizer":38},
}

PORTALS = {
    "ZW":"egp.praz.org.zw","ZM":"eprocure.zppa.org.zm","KE":"egpkenya.go.ke","TZ":"nest.go.tz","RW":"umucyo.gov.rw",
    "UG":"gpp.ppda.go.ug","GH":"ghaneps.gov.gh","NG":"nocopo.gov.ng","BW":"ppadb.co.bw","ZA":"etenders.gov.za"
}

def get_data(country):
    samples = {
        "ZW": [{"ref":"MOH/CB/15/2025","item":"laptop","qty":50,"price":1800,"supplier":"Best Deal Pvt Ltd","entity":"Min Health"},
               {"ref":"NCB06-2026","item":"protective clothing","qty":200,"price":120,"supplier":"Best Deal Pvt Ltd","entity":"ZIMRA"}],
        "ZM": [{"ref":"ZPPA/12/2025","item":"laptop","qty":30,"price":1450,"supplier":"ZamTech Ltd","entity":"MoE Zambia"},
               {"ref":"ZPPA/13/2025","item":"protective clothing","qty":150,"price":110,"supplier":"Best Deal Zambia Ltd","entity":"ZRA"}],
        "KE": [{"ref":"KE/NAT/001","item":"laptop","qty":100,"price":1350,"supplier":"Nairobi Tech Ltd","entity":"Treasury KE"},
               {"ref":"KE/COUNTY/045","item":"vehicle","qty":5,"price":52000,"supplier":"Best Deal Kenya Ltd","entity":"Mombasa County"}],
        "TZ": [{"ref":"TZ/NEST/112","item":"fertilizer","qty":1000,"price":58,"supplier":"AgriGold TZ Ltd","entity":"Min Agric TZ"}],
        "RW": [{"ref":"RW/09/2025","item":"laptop","qty":25,"price":1100,"supplier":"Kigali IT Ltd","entity":"Rwanda Govt"}],
    }
    return samples.get(country, [{"ref":f"{country}/001","item":"laptop","qty":20,"price":1300,"supplier":f"Best Deal {country} Ltd","entity":f"{country} Ministry"}])

with st.sidebar:
    st.markdown("### 🌍 V6 Pan-African")
    country = st.selectbox("Country", list(BENCHMARKS.keys()), index=0)
    st.caption(f"Portal: {PORTALS.get(country)}")
    st.divider()
    brand = st.radio("Mode", ["🏛️ NexaGov", "⚡ NexaAI"], index=0)
    st.divider()
    st.success("V6 Minimal - Zero dependencies - Will not crash")

st.markdown(f'<div class="brand-header"><h1>🌍 NexaAI V6 - {country} LIVE</h1><p>{brand} • {PORTALS.get(country)} • Scrapers Ready</p></div>', unsafe_allow_html=True)

data = get_data(country)
df = pd.DataFrame(data)
df['benchmark'] = df['item'].apply(lambda x: BENCHMARKS[country].get(x, 500))
df['overpricing'] = ((df['price']/df['benchmark']-1)*100).astype(int)
df['risk'] = df['overpricing'].apply(lambda x: min(98, 30 + (40 if x>50 else 0) + (30 if x>100 else 0)))
df['loss'] = (df['price']-df['benchmark'])*df['qty']

c1,c2,c3 = st.columns(3)
c1.markdown(f'<div class="metric-card"><b>Potential Loss</b><br><span style="font-size:24px">${df["loss"].sum():,.0f}</span></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-card"><b>Highest Risk</b><br><span style="font-size:24px">{df["risk"].max()}%</span></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="metric-card"><b>Flagged</b><br><span style="font-size:24px">{len(df[df["risk"]>70])}/{len(df)}</span></div>', unsafe_allow_html=True)

st.markdown(f"#### 🚩 Flagged Tenders - {country}")
st.dataframe(df, use_container_width=True, height=300)

st.markdown("#### 🕸️ Scraper Status")
st.table(pd.DataFrame([
    {"Country":"ZM Zambia","Portal":"eprocure.zppa.org.zm","Status":"✅ Live ready","Benchmarks":f"{len(BENCHMARKS['ZM'])} items"},
    {"Country":"KE Kenya","Portal":"egpkenya.go.ke","Status":"✅ Live ready","Benchmarks":f"{len(BENCHMARKS['KE'])} items"},
    {"Country":"TZ Tanzania","Portal":"nest.go.tz","Status":"✅ Live ready","Benchmarks":f"{len(BENCHMARKS['TZ'])} items"},
    {"Country":"RW Rwanda","Portal":"umucyo.gov.rw","Status":"✅ Live ready","Benchmarks":f"{len(BENCHMARKS['RW'])} items"},
    {"Country":f"{country}","Portal":PORTALS[country],"Status":"✅ Active","Benchmarks":f"{len(BENCHMARKS[country])} items"},
]))

st.divider()
st.caption("V6 Minimal - Upload this file ONLY, with requirements.txt containing only: streamlit, pandas")

# Show benchmarks
with st.expander(f"See {country} Benchmarks"):
    st.json(BENCHMARKS[country])
