import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from binance.client import Client
from datetime import datetime
import time

# 1. SAYFA YAPILANDIRMASI
st.set_page_config(page_title="NEON RED | Trading Terminal", layout="wide")

# --- PROFESYONEL TEMA (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #000000; color: #ffffff; }
    .stApp { background-color: #000000; }
    [data-testid="stMetric"] { background-color: #111111; border-left: 5px solid #ff0000; border-radius: 10px; padding: 20px !important; }
    section[data-testid="stSidebar"] { background-color: #050505 !important; border-right: 1px solid #333; }
    .stButton>button { background-color: #ff0000 !important; color: white !important; width: 100%; border-radius: 5px; height: 3em; font-weight: bold; border: none; }
    </style>
    """, unsafe_allow_html=True)

# 2. SECRETS VE BAĞLANTI
# Streamlit Secrets'tan anahtarları çekiyoruz
API_KEY = st.secrets.get("BINANCE_API_KEY")
API_SECRET = st.secrets.get("BINANCE_SECRET_KEY")

@st.cache_resource
def get_binance_client():
    if not API_KEY or not API_SECRET:
        return None
    try:
        c = Client(API_KEY, API_SECRET)
        c.API_URL = 'https://api.trbinance.com/api'
        c.get_server_time()
        return c
    except:
        return None

client = get_binance_client()

# 3. TEKNİK ANALİZ MOTORU
def calculate_indicators(df):
    # RSI
    delta = df['close'].diff()
    up = delta.clip(lower=0); down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=13, adjust=False).mean(); ema_down = down.ewm(com=13, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (ema_up / ema_down)))
    
    # Bollinger Bantları
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['STD'] = df['close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (df['STD'] * 2)
    df['Lower'] = df['MA20'] - (df['STD'] * 2)
    return df

def fetch_data(symbol):
    try:
        bars = client.get_klines(symbol=symbol.upper(), interval='15m', limit=100)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
        for col in ['open', 'high', 'low', 'close', 'vol']: df[col] = pd.to_numeric(df[col])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        return calculate_indicators(df)
    except:
        return None

# 4. YAN PANEL
st.sidebar.markdown("<h1 style='color: #ff0000;'>NEON RED TR</h1>", unsafe_allow_html=True)

if client:
    st.sidebar.success("✅ API BAĞLANTISI AKTİF")
else:
    st.sidebar.error("❌ API ANAHTARLARI OKUNAMADI")
    st.sidebar.info("Secrets kısmına BINANCE_API_KEY ve BINANCE_SECRET_KEY yazdığınızdan emin olun.")

coin = st.sidebar.selectbox("Varlık Seçimi", ["BTCTRY", "ETHTRY", "SOLTRY", "BNBTRY"], index=0)
try_butce = st.sidebar.number_input("İşlem Bütçesi (TRY)", value=250.0, min_value=100.0)
mod = st.sidebar.radio("Çalışma Modu", ["SİMÜLASYON", "GERÇEK İŞLEM"])
aktif = st.sidebar.toggle("SİSTEMİ DEVREYE AL")

# 5. ANA PANEL
st.title(f"⚡ {coin} SAVAŞ TERMİNALİ")
c1, c2, c3, c4 = st.columns(4)

if 'gecmis' not in st.session_state: st.session_state.gecmis = []

if aktif:
    if not client:
        st.error("API Bağlantısı olmadan sistem çalışamaz.")
    else:
        df = fetch_data(coin)
        if df is not None:
            son_fiyat = df['close'].iloc[-1]
            son_rsi = df['RSI'].iloc[-1]
            alt_bant = df['Lower'].iloc[-1]
            ust_bant = df['Upper'].iloc[-1]

            # Metrikler
            c1.metric("GÜNCEL FİYAT", f"₺{son_fiyat:,.2f}")
            c2.metric("RSI (14)", f"{son_rsi:.1f}")
            c3.metric("ALT BANT", f"{alt_bant:,.0f}")
            
            try:
                bakiye = client.get_asset_balance(asset='TRY')['free']
                c4.metric("TRY BAKİYE", f"₺{float(bakiye):,.2f}")
            except:
                c4.metric("BAKİYE", "Veri Yok")

            # GRAFİK
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Fiyat'))
            fig.add_trace(go.Scatter(x=df['time'], y=df['Upper'], line=dict(color='rgba(255,0,0,0.3)', width=1), name='Üst Bant'))
            fig.add_trace(go.Scatter(x=df['time'], y=df['Lower'], line=dict(color='rgba(0,255,0,0.3)', width=1), name='Alt Bant'))
            fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,b=0,t=0), paper_bgcolor="black", plot_bgcolor="black")
            st.plotly_chart(fig, use_container_width=True)

            # STRATEJİ KARARI
            karar = "BEKLE"
            if son_rsi < 32 and son_fiyat < alt_bant: karar = "AL"
            elif son_rsi > 68 or son_fiyat > ust_bant: karar = "SAT"

            zaman = datetime.now().strftime("%H:%M:%S")
            if karar == "AL":
                miktar = round(try_butce / son_fiyat, 6)
                msg = f"🟢 [{zaman}] ALIM SİNYALİ: {son_fiyat} TL | Adet: {miktar}"
                if mod == "GERÇEK İŞLEM":
                    try:
                        client.order_market_buy(symbol=coin, quantity=miktar)
                        msg += " | ✅ EMİR TAMAM"
                    except Exception as e: msg += f" | ❌ HATA: {e}"
                st.session_state.gecmis.append(msg)
            elif karar == "SAT":
                try:
                    asset = coin.replace("TRY", "")
                    eldeki = float(client.get_asset_balance(asset=asset)['free'])
                    if eldeki > 0 and (eldeki * son_fiyat) > 100:
                        msg = f"🔴 [{zaman}] SATIŞ SİNYALİ: {son_fiyat} TL"
                        if mod == "GERÇEK İŞLEM":
                            client.order_market_sell(symbol=coin, quantity=eldeki)
                            msg += " | ✅ SATILDI"
                        st.session_state.gecmis.append(msg)
                except: pass

            st.markdown("### 📋 SİSTEM GÜNLÜĞÜ")
            st.code("\n".join(st.session_state.gecmis[-8:]))
        else:
            st.warning("⚠️ Veri çekilemiyor. Binance TR bu sunucu lokasyonunu (US/EU) engelliyor olabilir.")
            
    time.sleep(15)
    st.rerun()
else:
    st.info("Sistem standby modunda. Başlatmak için sol paneli kullanın.")
