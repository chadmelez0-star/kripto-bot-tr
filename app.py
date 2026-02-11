import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from binance.client import Client
from binance.exceptions import BinanceAPIException
import os
import time
from datetime import datetime

# 1. GÜVENLİK (STREAMLIT SECRETS)
# Not: Bulutta çalışırken .env yerine st.secrets kullanılır.
try:
    API_KEY = st.secrets["BINANCE_API_KEY"]
    API_SECRET = st.secrets["BINANCE_SECRET_KEY"]
except Exception:
    st.error("⚠️ API Anahtarları Streamlit Secrets kısmında bulunamadı!")
    API_KEY = None
    API_SECRET = None

# SAYFA AYARLARI
st.set_page_config(page_title="NEON RED | Cloud Terminal", layout="wide")

# --- MODERN ARAYÜZ (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700&display=swap');
    html, body, [class*="css"]  { font-family: 'Inter', sans-serif; background-color: #000000; color: #ffffff; }
    .stApp { background-color: #000000; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #111111 0%, #050505 100%);
        border-left: 5px solid #ff0000;
        border-radius: 10px;
        padding: 20px !important;
    }
    section[data-testid="stSidebar"] { background-color: #050505 !important; border-right: 1px solid #333; }
    .stButton>button { background-color: #ff0000 !important; color: white !important; width: 100%; border:none; height: 3em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2. BINANCE TR BULUT BAĞLANTI SİSTEMİ
def get_cloud_client():
    if not API_KEY or not API_SECRET:
        return None
    
    # Denenecek farklı endpointler (Bulut sunucusu için alternatifler)
    urls = [
        'https://api.trbinance.com/api',
        'https://www.trbinance.com/api'
    ]
    
    for url in urls:
        try:
            c = Client(API_KEY, API_SECRET)
            c.API_URL = url
            c.get_server_time(timeout=10)
            return c
        except Exception:
            continue
    return None

# Bağlantıyı oluştur
client = get_cloud_client()

# 3. TEKNİK ANALİZ
def get_indicators(df):
    delta = df['close'].diff()
    up = delta.clip(lower=0); down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=13, adjust=False).mean(); ema_down = down.ewm(com=13, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (ema_up / ema_down)))
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['STD'] = df['close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (df['STD'] * 2)
    df['Lower'] = df['MA20'] - (df['STD'] * 2)
    return df

def get_data(symbol):
    try:
        if client is None: return None
        bars = client.get_klines(symbol=symbol.upper(), interval=Client.KLINE_INTERVAL_15MINUTE, limit=100)
        if not bars: return None
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
        for col in ['open', 'high', 'low', 'close', 'vol']: df[col] = pd.to_numeric(df[col])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        return get_indicators(df)
    except: return None

# 4. YAN PANEL
st.sidebar.markdown("<h1 style='color: #ff0000; text-align:center;'>NEON RED CLOUD</h1>", unsafe_allow_html=True)

if client:
    st.sidebar.success("✅ Bulut Bağlantısı Başarılı")
else:
    st.sidebar.error("❌ Binance TR Erişilemiyor!")
    st.sidebar.info("Binance TR panelininden IP kısıtlamasını 'Unrestricted' yaptığınızdan emin olun.")

coin = st.sidebar.selectbox("Varlık Seçimi", ["BTCTRY", "ETHTRY", "SOLTRY", "BNBTRY"], index=0)
try_butce = st.sidebar.number_input("İşlem Başına Bütçe (TRY)", value=250.0, min_value=100.0)
mod = st.sidebar.radio("Çalışma Modu", ["📊 SİMÜLASYON", "💸 GERÇEK İŞLEM"])
aktif = st.sidebar.toggle("SİSTEMİ DEVREYE AL")

# 5. ANA PANEL
st.title(f"⚡ {coin} TERMİNALİ (7/24)")
c1, c2, c3, c4 = st.columns(4)

if 'gecmis' not in st.session_state: st.session_state.gecmis = []

if aktif:
    if client is None:
        st.error("Binance bağlantısı kurulamadı. Secrets veya IP ayarlarını kontrol edin.")
    else:
        df = get_data(coin)
        if df is not None and not df.empty:
            son_fiyat = df['close'].iloc[-1]
            son_rsi = df['RSI'].iloc[-1]
            alt_bant = df['Lower'].iloc[-1]
            ust_bant = df['Upper'].iloc[-1]

            c1.metric("GÜNCEL FİYAT", f"{son_fiyat:,.2f} TL")
            c2.metric("RSI (14)", f"{son_rsi:.1f}")
            c3.metric("ALT BANT", f"{alt_bant:,.2f}")
            
            try:
                bakiye = client.get_asset_balance(asset='TRY')['free']
                c4.metric("TRY BAKİYE", f"₺{float(bakiye):,.2f}")
            except: c4.metric("BAKİYE", "Okunamadı")

            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Fiyat'))
            fig.add_trace(go.Scatter(x=df['time'], y=df['Upper'], line=dict(color='rgba(255,0,0,0.2)'), name='Üst Bant'))
            fig.add_trace(go.Scatter(x=df['time'], y=df['Lower'], line=dict(color='rgba(0,255,0,0.2)'), name='Alt Bant'))
            fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,b=0,t=0), paper_bgcolor="black", plot_bgcolor="black")
            st.plotly_chart(fig, use_container_width=True)

            # Karar mekanizması aynı kalıyor...
            karar = "BEKLE"
            if son_rsi < 32 and son_fiyat < alt_bant: karar = "AL"
            elif son_rsi > 68 or son_fiyat > ust_bant: karar = "SAT"

            zaman = datetime.now().strftime("%H:%M:%S")
            if karar == "AL":
                miktar = round(try_butce / son_fiyat, 6)
                msg = f"🟢 [{zaman}] AL: {son_fiyat} TL | Adet: {miktar}"
                if mod == "💸 GERÇEK İŞLEM":
                    try:
                        client.order_market_buy(symbol=coin, quantity=miktar)
                        msg += " | ✅ TAMAM"
                    except Exception as e: msg += f" | ❌ HATA: {e}"
                st.session_state.gecmis.append(msg)
            elif karar == "SAT":
                try:
                    asset = coin.replace("TRY", "")
                    eldeki = float(client.get_asset_balance(asset=asset)['free'])
                    if eldeki > 0 and (eldeki * son_fiyat) > 100:
                        msg = f"🔴 [{zaman}] SAT: {son_fiyat} TL | Adet: {eldeki}"
                        if mod == "💸 GERÇEK İŞLEM":
                            client.order_market_sell(symbol=coin, quantity=eldeki)
                            msg += " | ✅ TAMAM"
                        st.session_state.gecmis.append(msg)
                except: pass

            st.code("\n".join(st.session_state.gecmis[-10:]))
        else:
            st.warning("Veri bekleniyor... Binance TR yurt dışı sunucularını engelliyor olabilir.")
            
    time.sleep(15) # Bulut için süreyi biraz artırmak daha stabil olur
    st.rerun()
else:
    st.info("Sistem standby modunda.")
