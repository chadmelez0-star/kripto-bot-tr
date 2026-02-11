import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from binance.client import Client
from datetime import datetime
import time

# 1. GÜVENLİK (STREAMLIT SECRETS)
# Paneldeki Settings > Secrets kısmına yazmış olman gerekir.
try:
    API_KEY = st.secrets["BINANCE_API_KEY"]
    API_SECRET = st.secrets["BINANCE_SECRET_KEY"]
except Exception:
    st.error("❌ HATA: API Anahtarları bulunamadı! Lütfen Streamlit panelinden Secrets ayarlarını yapın.")
    st.stop() # Anahtarlar yoksa uygulamayı durdur

# SAYFA AYARLARI
st.set_page_config(page_title="NEON RED TR", layout="wide")

# --- MODERN SİYAH & KIRMIZI TEMA ---
st.markdown("""
    <style>
    html, body, [class*="css"] { background-color: #000000; color: #ffffff; font-family: 'Inter', sans-serif; }
    .stApp { background-color: #000000; }
    [data-testid="stMetric"] { background-color: #111111; border-left: 5px solid #ff0000; border-radius: 10px; padding: 15px !important; }
    section[data-testid="stSidebar"] { background-color: #050505 !important; border-right: 1px solid #333; }
    .stButton>button { background-color: #ff0000 !important; color: white !important; width: 100%; border:none; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2. BINANCE TR BAĞLANTISI
@st.cache_resource # Bağlantıyı bir kez kur ve sakla
def get_client():
    try:
        c = Client(API_KEY, API_SECRET)
        c.API_URL = 'https://api.trbinance.com/api'
        c.get_server_time() # Test
        return c
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None

client = get_client()

# 3. VERİ VE ANALİZ
def get_data(symbol):
    try:
        bars = client.get_klines(symbol=symbol.upper(), interval=Client.KLINE_INTERVAL_15MINUTE, limit=100)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
        for col in ['open', 'high', 'low', 'close']: df[col] = pd.to_numeric(df[col])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        
        # RSI ve Bollinger
        delta = df['close'].diff()
        up = delta.clip(lower=0); down = -1 * delta.clip(upper=0)
        ema_up = up.ewm(com=13).mean(); ema_down = down.ewm(com=13).mean()
        df['RSI'] = 100 - (100 / (1 + (ema_up / ema_down)))
        df['MA20'] = df['close'].rolling(20).mean()
        df['Lower'] = df['MA20'] - (df['close'].rolling(20).std() * 2)
        df['Upper'] = df['MA20'] + (df['close'].rolling(20).std() * 2)
        return df
    except: return None

# 4. YAN PANEL
st.sidebar.title("NEON RED TR")
coin = st.sidebar.selectbox("Varlık Seçimi", ["BTCTRY", "ETHTRY", "SOLTRY"], index=0)
try_butce = st.sidebar.number_input("Bütçe (TRY)", value=250.0, min_value=100.0)
mod = st.sidebar.radio("Mod", ["SİMÜLASYON", "GERÇEK İŞLEM"])
aktif = st.sidebar.toggle("SİSTEMİ DEVREYE AL")

# 5. ANA PANEL
st.title(f"🚀 {coin} Terminali")
c1, c2, c3, c4 = st.columns(4)

if 'logs' not in st.session_state: st.session_state.logs = []

if aktif and client:
    df = get_data(coin)
    if df is not None:
        fiyat = df['close'].iloc[-1]; rsi = df['RSI'].iloc[-1]
        alt = df['Lower'].iloc[-1]; ust = df['Upper'].iloc[-1]

        c1.metric("FİYAT", f"{fiyat:,.2f} TL")
        c2.metric("RSI", f"{rsi:.1f}")
        c3.metric("BANT", "ALT" if fiyat < alt else "ÜST" if fiyat > ust else "NORMAL")
        
        try:
            bakiye = client.get_asset_balance(asset='TRY')['free']
            c4.metric("BAKİYE", f"{float(bakiye):,.2f} TL")
        except: c4.metric("BAKİYE", "0.00 TL")

        # Grafik
        fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        fig.add_trace(go.Scatter(x=df['time'], y=df['Lower'], line=dict(color='green', width=1), name='Alt Bant'))
        fig.add_trace(go.Scatter(x=df['time'], y=df['Upper'], line=dict(color='red', width=1), name='Üst Bant'))
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)

        # Karar
        zaman = datetime.now().strftime("%H:%M")
        if rsi < 32 and fiyat < alt:
            msg = f"🟢 [{zaman}] ALIM SİNYALİ: {fiyat} TL"
            if mod == "GERÇEK İŞLEM":
                try:
                    client.order_market_buy(symbol=coin, quantity=round(try_butce/fiyat, 5))
                    msg += " | EMİR OK"
                except Exception as e: msg += f" | HATA: {e}"
            st.session_state.logs.append(msg)
        elif rsi > 68 or fiyat > ust:
            # Satış mantığı... (Eldeki bakiyeyi kontrol et ve sat)
            st.session_state.logs.append(f"🔴 [{zaman}] SATIŞ SİNYALİ: {fiyat} TL")

        st.code("\n".join(st.session_state.logs[-5:]))
    
    time.sleep(15)
    st.rerun()
else:
    st.info("Sistem Beklemede...")
