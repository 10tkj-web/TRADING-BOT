import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from groq import Groq

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="AI Trading Asisten", page_icon="🤖", layout="wide")
st.title("🤖 AI Trading Assistant (v7.0 - Final)")
st.write("Analisis Teknikal Multi-Indikator + Konsultasi AI Bahasa Manusia")

# --- KONFIGURASI API GROQ ---
# GANTI TEKS DI BAWAH INI DENGAN API KEY GROQ KAMU
API_KEY_GROQ = ""

try:
    client = Groq(api_key=API_KEY_GROQ)
except Exception as e:
    st.error(f"Gagal inisialisasi AI: {e}")

# --- SIDEBAR PENGATURAN ---
st.sidebar.header("⚙️ Pengaturan")

# Kamus Aset
daftar_aset = {
    "Crypto": ["BTC-USD", "ETH-USD", "SOL-USD"],
    "Forex": ["EURUSD=X", "GBPUSD=X", "XAUUSD=X (Emas USD)"],
    "Komoditas": ["GC=F (Emas Futures)", "CL=F (Minyak WTI)", "NG=F (Gas Alam)"],
    "Saham US": ["AAPL", "TSLA", "MSFT", "NVDA"],
    "Saham Indo": ["BBCA.JK", "BBRI.JK", "TLKM.JK", "GOTO.JK"],
    "Indeks": ["^JKSE (IHSG)", "^GSPC (S&P 500)"]
}

kategori = st.sidebar.selectbox("Pilih Kategori Aset:", list(daftar_aset.keys()))
pilihan_aset = st.sidebar.selectbox(f"Pilih Aset {kategori}:", daftar_aset[kategori])
ticker = pilihan_aset.split(" ")[0]

gaya_trading = st.sidebar.selectbox(
    "Pilih Gaya Trading:", 
    ["Swing Trade (Harian)", "Day Trade (1 Jam)", "Scalping (5 Menit)"]
)

# Atur Periode
if "Day Trade" in gaya_trading:
    interval, periode = "1h", "1mo"
elif "Swing" in gaya_trading:
    interval, periode = "1d", "6mo"
else:
    interval, periode = "5m", "5d"

# --- FUNGSI INDIKATOR ---
def hitung_semua_indikator(data):
    data['MA_20'] = data['Close'].rolling(window=20).mean()
    data['MA_50'] = data['Close'].rolling(window=50).mean()
    
    delta = data['Close'].diff(1)
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))
    
    exp1 = data['Close'].ewm(span=12, adjust=False).mean()
    exp2 = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = exp1 - exp2
    data['Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
    
    data['BB_Middle'] = data['Close'].rolling(window=20).mean()
    std = data['Close'].rolling(window=20).std()
    data['BB_Upper'] = data['BB_Middle'] + (std * 2)
    data['BB_Lower'] = data['BB_Middle'] - (std * 2)
    return data

# --- LOGIKA UTAMA ---
if st.sidebar.button("Analisis Sekarang"):
    with st.spinner(f'Menganalisis {ticker}...'):
        try:
            # 1. Ambil Data
            data = yf.download(ticker, period=periode, interval=interval)
            data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
            
            if not data.empty and len(data) > 50:
                data = hitung_semua_indikator(data)
                
                # 2. Ambil Nilai Terakhir (Fix error Series)
                harga = float(data['Close'].iloc[-1].item())
                ma20 = float(data['MA_20'].iloc[-1].item())
                ma50 = float(data['MA_50'].iloc[-1].item())
                rsi = float(data['RSI'].iloc[-1].item())
                macd = float(data['MACD'].iloc[-1].item())
                signal = float(data['Signal'].iloc[-1].item())
                bb_upper = float(data['BB_Upper'].iloc[-1].item())
                bb_lower = float(data['BB_Lower'].iloc[-1].item())
                
                # 3. Tampilkan Grafik
                st.subheader(f"📊 Grafik {ticker} ({gaya_trading})")
                fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1, 1]})
                
                ax1.plot(data['Close'], label='Harga', color='white', linewidth=1.5)
                ax1.plot(data['MA_20'], label='MA 20', color='orange', linestyle='--')
                ax1.plot(data['MA_50'], label='MA 50', color='red', linestyle='--')
                ax1.fill_between(data.index, data['BB_Lower'], data['BB_Upper'], color='gray', alpha=0.2, label='Bollinger Bands')
                ax1.set_facecolor('#1e1e1e')
                ax1.legend()
                
                ax2.plot(data['RSI'], color='purple')
                ax2.axhline(70, color='red', linestyle='--')
                ax2.axhline(30, color='green', linestyle='--')
                ax2.set_facecolor('#1e1e1e')
                
                ax3.plot(data['MACD'], label='MACD', color='blue')
                ax3.plot(data['Signal'], label='Signal', color='red', linestyle='--')
                ax3.axhline(0, color='white', linewidth=0.5)
                ax3.set_facecolor('#1e1e1e')
                ax3.legend()
                
                plt.tight_layout()
                st.pyplot(fig)
                
                # 4. Metrik Data
                st.subheader("📌 Data Terkini")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Harga", f"{harga:,.2f}")
                c2.metric("RSI", f"{rsi:.1f}")
                c3.metric("MACD", f"{macd:.4f}")
                c4.metric("Tren", "BULLISH" if ma20 > ma50 else "BEARISH")
                
                # 5. Kesimpulan Rule-Based
                st.subheader("🤖 Kesimpulan Teknikal (Rule-Based)")
                skor_beli, skor_jual = 0, 0
                if rsi < 30: skor_beli += 2
                elif rsi > 70: skor_jual += 2
                if ma20 > ma50: skor_beli += 1
                else: skor_jual += 1
                if macd > signal: skor_beli += 1
                else: skor_jual += 1
                if harga < bb_lower: skor_beli += 1
                elif harga > bb_upper: skor_jual += 1
                
                narasi = f"Berdasarkan analisis pada timeframe **{gaya_trading}**, aset **{ticker}** saat ini diperdagangkan di harga **{harga:,.2f}**. "
                
                if skor_beli >= 3:
                    st.success("🟢 **REKOMENDASI: BELI (BUY / LONG)**")
                    narasi += f"Terdapat indikasi kuat bahwa harga sedang *oversold* (RSI: {rsi:.1f}) atau berada di area support bawah. **Saran:** Cari titik entry beli, pasang Stop Loss di bawah Bollinger Bands bawah ({bb_lower:,.2f})."
                elif skor_jual >= 3:
                    st.error("🔴 **REKOMENDASI: JUAL (SELL / SHORT)**")
                    narasi += f"Terdapat indikasi kuat bahwa harga sedang *overbought* (RSI: {rsi:.1f}) atau menyentuh resistance atas. **Saran:** Waspadai koreksi, pasang Take Profit di area ini ({bb_upper:,.2f})."
                else:
                    st.warning("🟡 **REKOMENDASI: TAHAN DULU (WAIT & SEE)**")
                    narasi += "Pasar sedang dalam fase konsolidasi atau belum ada sinyal yang searah dari indikator. **Saran:** Tunggu konfirmasi candlestick selanjutnya."
                
                st.write(narasi)

                # 6. FITUR CHAT AI (GROQ)
                st.markdown("---")
                st.subheader("💬 Konsultasi AI (Tanya Bebas)")
                st.write("Tanya apa aja soal strategi trading, modal, atau aset ini ke AI.")
                
                pertanyaan = st.text_input("Contoh: 'Saya punya uang 600rb, mending beli BBCA atau day trade pakai lev 21?'")
                
                if st.button("Tanya AI"):
                    if API_KEY_GROQ == "":
                        st.error("Kamu belum memasukkan API Key Groq di dalam kode!")
                    elif pertanyaan:
                        with st.spinner("AI sedang berpikir..."):
                            prompt = f"""
                            Kamu adalah seorang analis trading profesional dan penasihat keuangan yang bijak.
                            Data pasar saat ini untuk {ticker}:
                            - Harga Terakhir: {harga:,.2f}
                            - RSI: {rsi:.1f}
                            - MA 20: {ma20:,.2f}
                            - MA 50: {ma50:,.2f}
                            - MACD: {macd:.4f}
                            - Bollinger Bands: Upper {bb_upper:,.2f}, Lower {bb_lower:,.2f}
                            - Gaya Trading User: {gaya_trading}

                            User bertanya: "{pertanyaan}"

                            Jawablah pertanyaan user tersebut dengan bahasa manusia yang santai, jelas, dan mendidik. 
                            Gunakan data teknikal di atas sebagai referensi. 
                            Jika user menanyakan soal leverage tinggi (seperti x21), ingatkan tentang risiko likuidasi yang sangat tinggi.
                            Berikan saran yang realistis, bukan janji pasti untung.
                            """
                            
                            try:
                                chat_completion = client.chat.completions.create(
                                    messages=[{"role": "user", "content": prompt}],
                                    model="llama-3.3-70b-versatile",
                                )
                                st.success("🤖 **Jawaban AI:**")
                                st.write(chat_completion.choices[0].message.content)
                            except Exception as e:
                                st.error(f"Gagal memanggil AI: {e}")
                    else:
                        st.warning("Ketik pertanyaanmu dulu ya!")
            else:
                st.error("Data tidak cukup atau kode aset salah.")
        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")