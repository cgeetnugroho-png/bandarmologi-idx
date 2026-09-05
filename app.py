"""
Dashboard Bandarmologi IDX — jejak akumulasi & distribusi dari harga dan volume.

Jalankan:  streamlit run app.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots

import bandar_core as bc

# ------------------------------------------------------------------ tampilan

INK = "#0B1016"
PANEL = "#141B24"
BORDER = "#243040"
TEXT = "#DDE4EC"
MUTED = "#74849A"
ACC = "#35A67C"      # akumulasi
DIST = "#C6455C"     # distribusi
MARK = "#E0A028"     # VWAP, POC, penanda

st.set_page_config(page_title="Bandarmologi IDX", page_icon="▣", layout="wide")

st.markdown(
    f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
      html, body, [class*="css"] {{ font-family: 'Archivo', system-ui, sans-serif; }}
      .stApp {{ background: {INK}; color: {TEXT}; font-feature-settings: "tnum" 1; }}
      section[data-testid="stSidebar"] {{ background: {PANEL}; border-right: 1px solid {BORDER}; }}
      h1 {{ font-size: 1.55rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: .1rem; }}
      h2 {{ font-size: 1.05rem; font-weight: 600; letter-spacing: -0.01em;
            margin: 1.6rem 0 .5rem; padding-bottom: .35rem; border-bottom: 1px solid {BORDER}; }}
      h3 {{ font-size: .95rem; font-weight: 600; }}
      .lede {{ color: {MUTED}; font-size: .9rem; max-width: 68ch; line-height: 1.55; }}
      .verdict {{ font-size: 2.2rem; font-weight: 700; letter-spacing: -0.03em; line-height: 1.1; }}
      .verdict-sub {{ color: {MUTED}; font-size: .85rem; margin-top: .2rem; }}
      .rail {{ position: relative; height: 10px; border-radius: 5px; margin: 1.1rem 0 .4rem;
               background: linear-gradient(90deg, {DIST} 0%, #3A4655 50%, {ACC} 100%); }}
      .pin {{ position: absolute; top: -6px; width: 3px; height: 22px; background: {TEXT};
              border-radius: 2px; box-shadow: 0 0 0 3px {INK}; }}
      .rail-legend {{ display: flex; justify-content: space-between;
                      color: {MUTED}; font-size: .72rem; }}
      .note {{ background: {PANEL}; border: 1px solid {BORDER}; border-left: 3px solid {MARK};
               border-radius: 4px; padding: .75rem .9rem; font-size: .87rem;
               color: {TEXT}; line-height: 1.5; }}
      div[data-testid="stMetricValue"] {{ font-size: 1.3rem; font-weight: 600; }}
      div[data-testid="stMetricLabel"] {{ color: {MUTED}; font-size: .78rem; }}
      .stTabs [data-baseweb="tab"] {{ font-weight: 500; }}
      footer, #MainMenu {{ visibility: hidden; }}
    </style>
    """,
    unsafe_allow_html=True,
)

PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Archivo, sans-serif", color=MUTED, size=11),
    margin=dict(l=8, r=8, t=28, b=8),
    hovermode="x unified",
    xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
    yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
    legend=dict(orientation="h", y=1.06, x=0, bgcolor="rgba(0,0,0,0)"),
)

WATCHLISTS = {
    "Bank & keuangan": ["BBCA", "BBRI", "BMRI", "BBNI", "BRIS", "ARTO", "BBTN", "BTPS"],
    "Konsumer": ["UNVR", "ICBP", "INDF", "MYOR", "AMRT", "CPIN", "JPFA", "KLBF"],
    "Energi & tambang": ["ADRO", "PTBA", "ITMG", "MDKA", "ANTM", "INCO", "MEDC", "PGAS"],
    "Teknologi & telko": ["GOTO", "TLKM", "EXCL", "TOWR", "ISAT", "MTEL", "BUKA", "EMTK"],
    "Industri & lain": ["ASII", "UNTR", "SMGR", "INKP", "BRPT", "TPIA", "AKRA", "INTP"],
}


# ------------------------------------------------------------------ data

@st.cache_data(ttl=900, show_spinner=False)
def load_prices(ticker: str, period: str) -> pd.DataFrame:
    """Ambil OHLCV harian. Dikembalikan kosong bila kode tidak dikenali."""
    try:
        df = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=False)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    cols = ["Open", "High", "Low", "Close", "Volume"]
    if not set(cols).issubset(df.columns):
        return pd.DataFrame()
    df = df[cols].dropna()
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_localize(None)
    return df


def analyze(ticker: str, period: str):
    raw = load_prices(ticker, period)
    if raw.empty or len(raw) < 30:
        return None
    return bc.add_indicators(raw)


# ------------------------------------------------------------------ komponen

def verdict_panel(d: pd.DataFrame, ticker: str) -> None:
    score = bc.bandar_score(d)
    label = bc.score_label(score)
    phase, note = bc.detect_phase(d)
    color = ACC if score >= 58 else DIST if score <= 43 else MARK

    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown(
            f"""
            <div class="verdict" style="color:{color}">{label}</div>
            <div class="verdict-sub">Skor {score} dari 100 &nbsp;·&nbsp; fase {phase.lower()}</div>
            <div class="rail"><div class="pin" style="left:calc({score}% - 1.5px)"></div></div>
            <div class="rail-legend"><span>Distribusi</span><span>Netral</span><span>Akumulasi</span></div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(f'<div class="note">{note}</div>', unsafe_allow_html=True)


def headline_metrics(d: pd.DataFrame) -> None:
    last = d.iloc[-1]
    prev = d["Close"].iloc[-2]
    chg = (last["Close"] / prev - 1) * 100
    turnover = d["TurnoverIDR"].tail(20).mean() / 1e9

    c = st.columns(5)
    c[0].metric("Harga penutupan", f"Rp {last['Close']:,.0f}", f"{chg:+.2f}%")
    c[1].metric("Volume vs rata-rata", f"{last['VolRatio']:.2f}x")
    c[2].metric("Aliran dana CMF", f"{last['CMF20']:+.3f}")
    c[3].metric("MFI 14 hari", f"{last['MFI14']:.0f}")
    c[4].metric("Transaksi harian", f"Rp {turnover:,.1f} M")


def price_chart(d: pd.DataFrame, ticker: str) -> go.Figure:
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04,
        row_heights=[0.56, 0.22, 0.22],
        subplot_titles=("", "Volume — hijau saat tutup di atas rentang", "Aliran dana (CMF 20 hari)"),
    )

    fig.add_trace(
        go.Candlestick(
            x=d.index, open=d["Open"], high=d["High"], low=d["Low"], close=d["Close"],
            name=bc.display_ticker(ticker),
            increasing=dict(line=dict(color=ACC, width=1), fillcolor=ACC),
            decreasing=dict(line=dict(color=DIST, width=1), fillcolor=DIST),
        ), row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=d.index, y=d["VWAP20"], name="VWAP 20 hari",
                   line=dict(color=MARK, width=1.6)), row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=d.index, y=d["SMA50"], name="Rata-rata 50 hari",
                   line=dict(color=MUTED, width=1, dash="dot")), row=1, col=1,
    )

    vol_color = np.where(d["AccDay"] == 1, ACC, np.where(d["DistDay"] == 1, DIST, "#39465A"))
    fig.add_trace(
        go.Bar(x=d.index, y=d["Volume"], marker_color=vol_color,
               name="Volume", showlegend=False), row=2, col=1,
    )
    fig.add_trace(
        go.Scatter(x=d.index, y=d["VolMA20"], name="Volume rata-rata",
                   line=dict(color=MARK, width=1), showlegend=False), row=2, col=1,
    )

    cmf = d["CMF20"]
    fig.add_trace(
        go.Bar(x=d.index, y=cmf, name="CMF",
               marker_color=np.where(cmf >= 0, ACC, DIST), showlegend=False), row=3, col=1,
    )

    # Tandai hari dengan volume luar biasa
    big = d[d["BigVol"]]
    if not big.empty:
        fig.add_trace(
            go.Scatter(
                x=big.index, y=big["High"] * 1.02, mode="markers", name="Jejak lot besar",
                marker=dict(symbol="triangle-down", size=7, color=MARK),
                hovertemplate="Volume %{customdata:.1f}x rata-rata<extra></extra>",
                customdata=big["VolRatio"],
            ), row=1, col=1,
        )

    fig.update_layout(**PLOT_LAYOUT, height=640, xaxis_rangeslider_visible=False, bargap=0.1)
    fig.update_xaxes(gridcolor=BORDER, showgrid=False)
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    for ann in fig.layout.annotations:
        ann.font.size = 11
        ann.font.color = MUTED
        ann.x = 0
        ann.xanchor = "left"
    return fig


def profile_chart(d: pd.DataFrame, lookback: int) -> tuple[go.Figure, dict]:
    vp = bc.volume_profile(d, bins=26, lookback=lookback)
    va = bc.value_area(vp)
    price = float(d["Close"].iloc[-1])

    inside = (vp["mid"] >= va.get("va_low", 0)) & (vp["mid"] <= va.get("va_high", 0))
    colors = np.where(np.isclose(vp["mid"], va.get("poc", -1)), MARK,
                      np.where(inside, "#3E5C7A", "#26313F"))

    fig = go.Figure(
        go.Bar(x=vp["volume"], y=vp["mid"], orientation="h", marker_color=colors,
               hovertemplate="Rp %{y:,.0f}<br>%{customdata:.1%} dari volume<extra></extra>",
               customdata=vp["share"])
    )
    fig.add_hline(y=price, line=dict(color=TEXT, width=1.4, dash="dash"),
                  annotation_text=f"Harga kini Rp {price:,.0f}",
                  annotation_position="top right",
                  annotation_font=dict(color=TEXT, size=11))
    fig.update_layout(**PLOT_LAYOUT, height=460, showlegend=False,
                      title=dict(text="", font=dict(size=11)))
    fig.update_xaxes(title="Volume terkumpul", showgrid=False)
    fig.update_yaxes(title="Level harga (Rp)", gridcolor=BORDER)
    return fig, va


def breakdown_chart(d: pd.DataFrame) -> go.Figure:
    comp = bc.score_components(d)
    names = list(comp)[::-1]
    vals = [comp[n] for n in names]
    colors = [ACC if v >= 58 else DIST if v <= 43 else "#4A5A6E" for v in vals]

    fig = go.Figure(
        go.Bar(x=vals, y=names, orientation="h", marker_color=colors,
               text=[f"{v:.0f}" for v in vals], textposition="outside",
               textfont=dict(color=MUTED, size=11), hoverinfo="skip")
    )
    fig.add_vline(x=50, line=dict(color=MUTED, width=1, dash="dot"))
    fig.update_layout(**PLOT_LAYOUT, height=300, showlegend=False)
    fig.update_xaxes(range=[0, 112], showgrid=False, showticklabels=False)
    fig.update_yaxes(showgrid=False)
    return fig


# ------------------------------------------------------------------ halaman

def page_single(period: str, profile_lookback: int) -> None:
    code = st.session_state.get("single_code", "BBCA")
    ticker = bc.normalize_ticker(code)

    with st.spinner(f"Mengambil data {bc.display_ticker(ticker)}…"):
        d = analyze(ticker, period)

    if d is None:
        st.error(
            f"Data untuk **{bc.display_ticker(ticker)}** tidak ditemukan atau terlalu pendek. "
            "Periksa kembali kode sahamnya, lalu coba lagi."
        )
        return

    st.markdown(f"# {bc.display_ticker(ticker)}")
    st.markdown(
        f'<div class="lede">Rekaman {len(d)} hari bursa hingga '
        f'{d.index[-1]:%d %B %Y}.</div>', unsafe_allow_html=True,
    )
    st.write("")
    verdict_panel(d, ticker)
    st.write("")
    headline_metrics(d)

    st.markdown("## Pergerakan harga dan jejak volume")
    st.plotly_chart(price_chart(d, ticker), width="stretch")

    left, right = st.columns([1, 1], gap="large")
    with left:
        st.markdown("## Di harga berapa barang menumpuk")
        fig, va = profile_chart(d, profile_lookback)
        st.plotly_chart(fig, width="stretch")
        if va:
            st.markdown(
                f'<div class="note">Volume terpadat di <b>Rp {va["poc"]:,.0f}</b>. '
                f'Sekitar 70% transaksi {profile_lookback} hari terakhir terjadi antara '
                f'Rp {va["va_low"]:,.0f} dan Rp {va["va_high"]:,.0f} — rentang ini sering '
                f'berperan sebagai penahan saat harga kembali ke sana.</div>',
                unsafe_allow_html=True,
            )
    with right:
        st.markdown("## Penyusun skor")
        st.plotly_chart(breakdown_chart(d), width="stretch")
        st.markdown(
            '<div class="note">Setiap komponen dinilai 0–100. Di atas 50 berarti '
            'komponen itu condong ke akumulasi, di bawah 50 ke distribusi.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("## Hari-hari dengan volume luar biasa")
    fp = bc.recent_footprints(d)
    if fp.empty:
        st.info("Belum ada hari dengan volume dua kali lipat rata-rata pada periode ini.")
    else:
        st.dataframe(fp, width="stretch", hide_index=True)


def page_screening(period: str) -> None:
    st.markdown("# Screening watchlist")
    st.markdown(
        '<div class="lede">Urutkan sekumpulan saham berdasarkan kecondongan '
        'akumulasi. Skor tinggi berarti jejak harga–volume mengarah ke '
        'penyerapan barang, bukan pelepasan.</div>',
        unsafe_allow_html=True,
    )
    st.write("")

    preset = st.selectbox("Daftar siap pakai", ["(isi sendiri)"] + list(WATCHLISTS))
    default = ", ".join(WATCHLISTS[preset]) if preset in WATCHLISTS else "BBCA, BBRI, TLKM, ASII, ANTM"
    raw = st.text_area("Kode saham, pisahkan dengan koma", value=default, height=90)

    if not st.button("Jalankan screening", type="primary"):
        return

    tickers = [bc.normalize_ticker(t) for t in raw.replace("\n", ",").split(",") if t.strip()]
    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        st.warning("Masukkan minimal satu kode saham.")
        return

    rows, failed = [], []
    bar = st.progress(0.0, text="Mengambil data…")
    for i, tk in enumerate(tickers, start=1):
        bar.progress(i / len(tickers), text=f"Menganalisa {bc.display_ticker(tk)} ({i}/{len(tickers)})")
        d = analyze(tk, period)
        if d is None:
            failed.append(bc.display_ticker(tk))
            continue
        rows.append(bc.summarize(d, tk))
    bar.empty()

    if not rows:
        st.error("Tidak ada data yang berhasil diambil. Periksa kode saham atau koneksi internet.")
        return

    table = pd.DataFrame(rows).sort_values("Skor", ascending=False).reset_index(drop=True)

    top = table.iloc[0]
    bottom = table.iloc[-1]
    c = st.columns(3)
    c[0].metric("Skor tertinggi", top["Kode"], f"{top['Skor']:.0f} — {top['Sinyal']}")
    c[1].metric("Skor terendah", bottom["Kode"], f"{bottom['Skor']:.0f} — {bottom['Sinyal']}")
    c[2].metric("Rata-rata watchlist", f"{table['Skor'].mean():.0f}")

    st.markdown("## Peringkat")
    st.dataframe(
        table,
        width="stretch",
        hide_index=True,
        column_config={
            "Skor": st.column_config.ProgressColumn(
                "Skor", min_value=0, max_value=100, format="%.0f"),
            "Harga": st.column_config.NumberColumn("Harga", format="Rp %d"),
            "% Hari": st.column_config.NumberColumn("% Hari", format="%.2f%%"),
            "% 20 Hari": st.column_config.NumberColumn("% 20 Hari", format="%.1f%%"),
            "CMF 20h": st.column_config.NumberColumn("CMF 20h", format="%.3f"),
            "MFI 14": st.column_config.NumberColumn("MFI 14", format="%.0f"),
            "Volume vs Rata-rata": st.column_config.NumberColumn(
                "Volume vs Rata-rata", format="%.2fx"),
            "Nilai Transaksi (Rp M)": st.column_config.NumberColumn(
                "Transaksi (Rp M)", format="%.1f"),
        },
    )

    st.download_button(
        "Unduh hasil sebagai CSV",
        table.to_csv(index=False).encode("utf-8"),
        file_name="screening_bandarmologi.csv",
        mime="text/csv",
    )

    if failed:
        st.caption(f"Tidak terambil: {', '.join(failed)}")


# ------------------------------------------------------------------ kerangka

with st.sidebar:
    st.markdown("### Bandarmologi IDX")
    mode = st.radio("Tampilan", ["Analisa satu saham", "Screening watchlist"], label_visibility="collapsed")
    st.divider()

    if mode == "Analisa satu saham":
        st.text_input("Kode saham", value="BBCA", key="single_code",
                      help="Cukup tulis kodenya, misal BBRI. Akhiran .JK ditambahkan otomatis.")

    period = st.select_slider(
        "Rentang data",
        options=["6mo", "1y", "2y", "5y"],
        value="1y",
        format_func=lambda p: {"6mo": "6 bulan", "1y": "1 tahun", "2y": "2 tahun", "5y": "5 tahun"}[p],
    )
    profile_lookback = st.slider("Profil volume — jumlah hari", 60, 250, 120, step=10)

    st.divider()
    st.caption(
        "Data harga dari Yahoo Finance, tertunda sekitar 15 menit. "
        "Tanpa broker summary, analisa ini membaca jejak pemain besar dari pola "
        "harga dan volume, bukan dari identitas broker."
    )

if mode == "Analisa satu saham":
    page_single(period, profile_lookback)
else:
    page_screening(period)

st.divider()
st.caption(
    "Alat bantu riset, bukan rekomendasi jual beli. Pola akumulasi tidak menjamin "
    "harga naik, dan semua keputusan investasi beserta risikonya ada pada Anda."
)

