import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from binance.client import Client
from datetime import datetime
import time

# SAYFA AYARLARI (En başta olmalı)
st.set_page_config(page_title="NEON RED | Cloud Terminal", layout="wide")

# --- MODERN ARAYÜZ (CSS) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { background-color: #000000; color: #ffffff; }
    .stApp { background-color: #000000; }
    [data-testid="stMetric"] { background-color: #111111; border-left: 5px solid #ff0000; border-radius: 10px; padding: 15px !important; }
    </style>
    """, unsafe_allow_html=True)

# 1. SECRETS KONTROLÜ
API_KEY = st.secrets.get("BINANCE_API_KEY")
API_SECRET = st.secrets.get("BINANCE_SECRET_KEY")

# 2. BINANCE TR BAĞLANTI SİSTEMİ
def connect_to_binance():
    if not API_KEY or not API_SECRET:
        return None, "API Anahtarları (Secrets) bulunamadı!"
    
    # Denenecek Binance TR kapıları
    endpoints = [
        'https://api.trbinance.com/api',
        'https://www.trbinance.com/api',
        'https://api.binance.me/api'
    ]
    
    last_error = ""
    for url in endpoints:
        try:
            c = Client(API_KEY, API_SECRET)
            c.API_URL = url
            c.get_server_time(timeout=5) # Bağlantıyı test et
            return c, None
        except Exception as e:
            last_error = str(e)
            continue
    return None, last_error

client, error_msg = connect_to_binance()

# 3. YAN PANEL (KONTROL)
st.sidebar.title("NEON RED TR")
if client:
    st.sidebar.success("✅ Bağlantı Kuruldu")
else:
    st.sidebar.error("❌ Bağlantı Başarısız")
    st.sidebar.warning(f"Detay: {error_msg}")
    st.sidebar.info("Binance TR panelinden IP kısıtlamasını kaldırın!")

coin = st.sidebar.selectbox("Varlık", ["BTCTRY", "ETHTRY", "SOLTRY"], index=0)
aktif = st.sidebar.toggle("SİSTEMİ BAŞLAT")

# 4. ANA PANEL
st.title(f"🚀 {coin} İzleme Paneli")

if aktif:
    if not client:
        st.error("Bağlantı hatası nedeniyle başlatılamadı.")
    else:
        try:
            # Veri çekme testi
            bars = client.get_klines(symbol=coin, interval='15m', limit=50)
            df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
            st.success(f"Son Fiyat: {df['close'].iloc[-1]} TL")
            
            # Basit grafik
            fig = go.Figure(data=[go.Scatter(x=df['time'], y=df['close'], name='Fiyat')])
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Piyasa Verisi Hatası: {e}")
            st.info("Bu hata, Binance TR'nin bu sunucuyu engellediğini gösteriyor olabilir.")
    
    time.sleep(15)
    st.rerun()
else:
    st.write("Sistem şu an kapalı. Başlatmak için yandaki butona tıklayın.")
