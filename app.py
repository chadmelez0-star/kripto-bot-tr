import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from binance.client import Client
from datetime import datetime
import time

# 1. SAYFA YAPILANDIRMASI
st.set_page_config(page_title="NEON RED | Global Terminal", layout="wide")

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

# 2. SECRETS VE GLOBAL BAĞLANTI
# Not: Binance Global anahtarlarını Streamlit Secrets kısmına yazmalısın.
API_KEY = st.secrets.get("BINANCE_API_KEY")
API_SECRET = st.secrets.get("BINANCE_SECRET_KEY")

@st.cache_resource
def get_global_client():
    if not API_KEY or not API_SECRET:
        return None
    try:
        # Global bağlantıda ekstra API_URL tanımlamaya gerek yoktur, varsayılanı kullanır.
        c = Client(API_KEY, API_SECRET)
        c.get_server_time() # Bağlantı testi
        return c
    except:
        return None

client = get_global_client()

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
st.sidebar.markdown("<h1 style='color: #ff0000; text-align:center;'>NEON RED GLOBAL</h1>", unsafe_allow_html=True)

if client:
    st.sidebar.success("✅ GLOBAL API AKTİF")
else:
    st.sidebar.error("❌ API ANAHTARLARI EKSİK")
    st.sidebar.info("Lütfen Streamlit panelinden Secrets ayarlarını yapın.")

coin = st.sidebar.selectbox("İşlem Çifti", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT"], index=0)
usdt_butce = st.sidebar.number_input("İşlem Bütçesi (USDT)", value=20.0, min_value=11.0, step=1.0)
mod = st.sidebar.radio("Çalışma Modu", ["📊 SİMÜLASYON", "💸 GERÇEK İŞLEM"])
aktif = st.sidebar.toggle("SİSTEMİ DEVREYE AL")

# 5. ANA PANEL
st.title(f"⚡ {coin} GLOBAL TERMİNAL")
c1, c2, c3, c4 = st.columns(4)

if 'gecmis' not in st.session_state: st.session_state.gecmis = []

if aktif:
    if not client:
        st.error("Bağlantı kurulamadı. Lütfen anahtarları kontrol edin.")
    else:
        df = fetch_data(coin)
        if df is not None:
            son_fiyat = df['close'].iloc[-1]
            son_rsi = df['RSI'].iloc[-1]
            alt_bant = df['Lower'].iloc[-1]
            ust_bant = df['Upper'].iloc[-1]

            # Metrikler
            c1.metric("GÜNCEL FİYAT", f"${son_fiyat:,.2f}")
            c2.metric("RSI (14)", f"{son_rsi:.1f}")
            c3.metric("BANT DURUMU", "DİP" if son_fiyat < alt_bant else "ZİRVE" if son_fiyat > ust_bant else "NORMAL")
            
            try:
                bakiye = client.get_asset_balance(asset='USDT')['free']
                c4.metric("USDT BAKİYE", f"${float(bakiye):,.2f}")
            except:
                c4.metric("BAKİYE", "Okunamadı")

            # GRAFİK
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Fiyat'))
            fig.add_trace(go.Scatter(x=df['time'], y=df['Upper'], line=dict(color='rgba(255,0,0,0.3)', width=1), name='Üst Bant'))
            fig.add_trace(go.Scatter(x=df['time'], y=df['Lower'], line=dict(color='rgba(0,255,0,0.3)', width=1), name='Alt Bant'))
            fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,b=0,t=0), paper_bgcolor="black", plot_bgcolor="black")
            st.plotly_chart(fig, use_container_width=True)

            # KARAR MEKANİZMASI
            karar = "BEKLE"
            if son_rsi < 32 and son_fiyat < alt_bant: karar = "AL"
            elif son_rsi > 68 or son_fiyat > ust_bant: karar = "SAT"

            zaman = datetime.now().strftime("%H:%M:%S")
            if karar == "AL":
                miktar = round(usdt_butce / son_fiyat, 5) # Adet hassasiyeti
                msg = f"🟢 [{zaman}] ALIM SİNYALİ: {son_fiyat} $ | Adet: {miktar}"
                if mod == "💸 GERÇEK İŞLEM":
                    try:
                        client.order_market_buy(symbol=coin, quantity=miktar)
                        msg += " | ✅ EMİR TAMAM"
                    except Exception as e: msg += f" | ❌ HATA: {e}"
                st.session_state.gecmis.append(msg)
                
            elif karar == "SAT":
                try:
                    asset = coin.replace("USDT", "")
                    eldeki = float(client.get_asset_balance(asset=asset)['free'])
                    if eldeki > 0 and (eldeki * son_fiyat) > 10: # Min 10 USDT kuralı
                        msg = f"🔴 [{zaman}] SATIŞ SİNYALİ: {son_fiyat} $"
                        if mod == "💸 GERÇEK İŞLEM":
                            client.order_market_sell(symbol=coin, quantity=eldeki)
                            msg += " | ✅ SATILDI"
                        st.session_state.gecmis.append(msg)
                except: pass

            st.markdown("### 📋 İŞLEM GÜNLÜĞÜ")
            st.code("\n".join(st.session_state.gecmis[-8:]))
        else:
            st.warning("⚠️ Veri çekilemiyor. Binance Global bağlantısını kontrol edin.")
            
    time.sleep(15)
    st.rerun()
else:
    st.info("Sistem standby modunda. Başlatmak için sol paneli kullanın.")
