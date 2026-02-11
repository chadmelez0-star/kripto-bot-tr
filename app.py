import streamlit as st

# SAYFA AYARLARI (HATA ALMAMAK İÇİN EN ÜSTTE OLMALI)
st.set_page_config(page_title="NEON RED TR", layout="wide")

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from binance.client import Client
from datetime import datetime
import time

# 1. GÜVENLİK (SECURE KEY OKUMA)
API_KEY = st.secrets.get("BINANCE_API_KEY")
API_SECRET = st.secrets.get("BINANCE_SECRET_KEY")

# 2. BINANCE TR BAĞLANTISI
@st.cache_resource
def get_client():
    if not API_KEY or not API_SECRET:
        return None
    try:
        c = Client(API_KEY, API_SECRET)
        # Bulut sunucuları için en stabil Binance TR adresi
        c.API_URL = 'https://api.trbinance.com/api'
        return c
    except:
        return None

client = get_client()

# --- ARAYÜZ (CSS) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { background-color: #000000; color: #ffffff; }
    .stApp { background-color: #000000; }
    [data-testid="stMetric"] { background-color: #111111; border-left: 5px solid #ff0000; border-radius: 10px; padding: 15px !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. YAN PANEL
st.sidebar.title("NEON RED TR")
if client:
    st.sidebar.success("✅ Bağlantı Hazır")
else:
    st.sidebar.error("❌ API Anahtarları Okunamadı!")
    st.sidebar.info("Lütfen Settings > Secrets kısmını kontrol edin.")

coin = st.sidebar.selectbox("Varlık Seçimi", ["BTCTRY", "ETHTRY", "SOLTRY"], index=0)
aktif = st.sidebar.toggle("SİSTEMİ DEVREYE AL")

# 4. ANA PANEL
st.title(f"🚀 {coin} Canlı İzleme")

if aktif:
    if not client:
        st.error("Bağlantı yok.")
    else:
        try:
            # Basit Veri Çekme
            bars = client.get_klines(symbol=coin, interval='15m', limit=100)
            df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
            fiyat = float(df['close'].iloc[-1])
            
            c1, c2 = st.columns(2)
            c1.metric("GÜNCEL FİYAT", f"{fiyat:,.2f} TL")
            
            # Grafik
            fig = go.Figure(data=[go.Scatter(x=pd.to_datetime(df['time'], unit='ms'), y=df['close'].astype(float), line=dict(color='red'))])
            fig.update_layout(template="plotly_dark", height=400)
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Veri çekme hatası: {e}")
            st.info("Binance TR, bulut sunucusunu (Amerika/Avrupa) engelliyor olabilir.")
    
    time.sleep(15)
    st.rerun()
else:
    st.write("Sistem standby modunda.")
