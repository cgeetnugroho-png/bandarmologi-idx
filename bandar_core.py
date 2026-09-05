"""
bandar_core.py — Mesin analisa bandarmologi berbasis harga & volume (IDX).

Tanpa broker summary, jejak pemain besar diperkirakan dari hubungan antara
volume, posisi penutupan dalam rentang harian, dan arah tren (kerangka Wyckoff
+ money flow). Semua fungsi murni pandas/numpy agar mudah diuji.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- konstanta

BIG_VOLUME_MULT = 2.0      # volume >= 2x rata-rata 20 hari = jejak lot besar
ACTIVE_VOLUME_MULT = 1.2   # ambang hari "ramai"
CLOSE_HIGH = 0.60          # tutup di 60% atas rentang = tekanan beli
CLOSE_LOW = 0.40           # tutup di 40% bawah rentang = tekanan jual

SCORE_WEIGHTS = {
    "Aliran dana (CMF 20h)": 0.20,
    "Arah OBV (20h)": 0.18,
    "Akumulasi A/D (20h)": 0.15,
    "Harga vs VWAP 20h": 0.12,
    "Hari akumulasi vs distribusi": 0.15,
    "Jejak lot besar (60h)": 0.12,
    "Ekspansi volume searah harga": 0.08,
}


# ---------------------------------------------------------------- utilitas

def normalize_ticker(raw: str) -> str:
    """BBCA -> BBCA.JK. Kode yang sudah lengkap dibiarkan."""
    t = str(raw).strip().upper()
    if not t:
        return ""
    return t if "." in t else f"{t}.JK"


def display_ticker(ticker: str) -> str:
    return ticker.replace(".JK", "")


def _scale(value: float, low: float, high: float) -> float:
    """Petakan nilai ke 0-100 secara linear, dipotong di ujung."""
    if value is None or not np.isfinite(value):
        return 50.0
    if high == low:
        return 50.0
    pct = (value - low) / (high - low)
    return float(np.clip(pct, 0.0, 1.0) * 100.0)


# ---------------------------------------------------------------- indikator

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Tambahkan seluruh kolom turunan. Input butuh Open/High/Low/Close/Volume."""
    d = df.copy()
    d = d[~d.index.duplicated(keep="last")].sort_index()
    d = d[d["Volume"] > 0]

    rng = (d["High"] - d["Low"]).replace(0, np.nan)
    d["TP"] = (d["High"] + d["Low"] + d["Close"]) / 3.0

    # Posisi penutupan dalam rentang harian: 1 = tutup di high, 0 = di low.
    d["CloseLoc"] = ((d["Close"] - d["Low"]) / rng).fillna(0.5)

    # Money Flow Multiplier & Volume (Chaikin)
    d["MFM"] = (((d["Close"] - d["Low"]) - (d["High"] - d["Close"])) / rng).fillna(0.0)
    d["MFV"] = d["MFM"] * d["Volume"]
    d["AD"] = d["MFV"].cumsum()
    d["CMF20"] = (
        d["MFV"].rolling(20).sum() / d["Volume"].rolling(20).sum().replace(0, np.nan)
    )

    # On Balance Volume
    direction = np.sign(d["Close"].diff()).fillna(0.0)
    d["OBV"] = (direction * d["Volume"]).cumsum()

    # Volume relatif
    d["VolMA20"] = d["Volume"].rolling(20).mean()
    d["VolRatio"] = d["Volume"] / d["VolMA20"].replace(0, np.nan)

    # VWAP bergulir dan VWAP terjangkar dari awal periode
    pv = d["TP"] * d["Volume"]
    d["VWAP20"] = pv.rolling(20).sum() / d["Volume"].rolling(20).sum().replace(0, np.nan)
    d["AVWAP"] = pv.cumsum() / d["Volume"].cumsum().replace(0, np.nan)

    for n in (20, 50, 200):
        d[f"SMA{n}"] = d["Close"].rolling(n).mean()

    # Money Flow Index 14
    tp_diff = d["TP"].diff()
    raw_mf = d["TP"] * d["Volume"]
    pos_mf = raw_mf.where(tp_diff > 0, 0.0).rolling(14).sum()
    neg_mf = raw_mf.where(tp_diff < 0, 0.0).rolling(14).sum()
    ratio = pos_mf / neg_mf.replace(0, np.nan)
    d["MFI14"] = 100 - (100 / (1 + ratio))

    # Average True Range 14
    prev_close = d["Close"].shift(1)
    tr = pd.concat(
        [
            d["High"] - d["Low"],
            (d["High"] - prev_close).abs(),
            (d["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    d["ATR14"] = tr.rolling(14).mean()

    # Effort vs result: volume besar tapi rentang sempit = serapan (absorpsi)
    d["SpreadRatio"] = (d["High"] - d["Low"]) / d["ATR14"].replace(0, np.nan)
    d["Absorption"] = (d["VolRatio"] >= BIG_VOLUME_MULT) & (d["SpreadRatio"] <= 0.7)

    # Penandaan hari
    active = d["VolRatio"] >= ACTIVE_VOLUME_MULT
    d["AccDay"] = (active & (d["CloseLoc"] >= CLOSE_HIGH)).astype(int)
    d["DistDay"] = (active & (d["CloseLoc"] <= CLOSE_LOW)).astype(int)
    d["BigVol"] = d["VolRatio"] >= BIG_VOLUME_MULT

    # Perkiraan nilai transaksi harian (rupiah)
    d["TurnoverIDR"] = d["Close"] * d["Volume"]

    return d


# ---------------------------------------------------------------- skor

def score_components(d: pd.DataFrame) -> dict[str, float]:
    """Pecahan skor 0-100 per komponen. >50 condong akumulasi."""
    if len(d) < 25:
        return {k: 50.0 for k in SCORE_WEIGHTS}

    last = d.iloc[-1]
    vol20 = float(d["Volume"].tail(20).sum()) or 1.0
    comp: dict[str, float] = {}

    comp["Aliran dana (CMF 20h)"] = _scale(last.get("CMF20", np.nan), -0.25, 0.25)

    obv_chg = (d["OBV"].iloc[-1] - d["OBV"].iloc[-21]) / vol20
    comp["Arah OBV (20h)"] = _scale(obv_chg, -0.60, 0.60)

    ad_chg = (d["AD"].iloc[-1] - d["AD"].iloc[-21]) / vol20
    comp["Akumulasi A/D (20h)"] = _scale(ad_chg, -0.40, 0.40)

    vwap = last.get("VWAP20", np.nan)
    gap = (last["Close"] - vwap) / vwap if np.isfinite(vwap) and vwap else np.nan
    comp["Harga vs VWAP 20h"] = _scale(gap, -0.05, 0.05)

    net_days = (d["AccDay"].tail(20).sum() - d["DistDay"].tail(20).sum()) / 20.0
    comp["Hari akumulasi vs distribusi"] = _scale(net_days, -0.40, 0.40)

    window = d.tail(60)
    big = window[window["BigVol"]]
    big_bias = float((big["CloseLoc"] - 0.5).mean() * 2) if len(big) else 0.0
    comp["Jejak lot besar (60h)"] = _scale(big_bias, -0.60, 0.60)

    v5 = float(d["Volume"].tail(5).mean())
    v20 = float(d["Volume"].tail(20).mean()) or 1.0
    price_up = d["Close"].iloc[-1] > d["Close"].iloc[-6] if len(d) > 6 else True
    expansion = (v5 / v20 - 1.0) * (1.0 if price_up else -1.0)
    comp["Ekspansi volume searah harga"] = _scale(expansion, -0.50, 0.50)

    return comp


def bandar_score(d: pd.DataFrame) -> float:
    comp = score_components(d)
    total = sum(comp[k] * w for k, w in SCORE_WEIGHTS.items())
    return round(total, 1)


def score_label(score: float) -> str:
    if score >= 70:
        return "Akumulasi kuat"
    if score >= 58:
        return "Akumulasi"
    if score >= 43:
        return "Netral"
    if score >= 30:
        return "Distribusi"
    return "Distribusi kuat"


# ---------------------------------------------------------------- fase pasar

def detect_phase(d: pd.DataFrame, lookback: int = 40) -> tuple[str, str]:
    """Perkiraan fase Wyckoff. Mengembalikan (nama fase, penjelasan singkat)."""
    if len(d) < lookback + 5:
        return "Data kurang", "Butuh minimal 45 hari perdagangan."

    w = d.tail(lookback)
    y = w["Close"].to_numpy(dtype=float)
    x = np.arange(len(y), dtype=float)
    slope = np.polyfit(x, y, 1)[0]
    move = slope * len(y) / y.mean()           # perubahan relatif sepanjang jendela

    # Bandingkan pergerakan dengan derau normalnya sendiri, supaya saham
    # bergejolak tinggi tidak otomatis dianggap sedang tren.
    daily_vol = float(w["Close"].pct_change().std())
    noise = daily_vol * np.sqrt(len(y)) if np.isfinite(daily_vol) and daily_vol > 0 else 0.02
    trend = move / noise                       # satuan: simpangan baku
    band = float(w["Close"].std() / w["Close"].mean())
    cmf = float(d["CMF20"].iloc[-1]) if np.isfinite(d["CMF20"].iloc[-1]) else 0.0
    net_days = int(w["AccDay"].sum() - w["DistDay"].sum())
    sideways = abs(trend) < 1.0

    if sideways and (cmf > 0.03 or net_days > 2):
        return (
            "Akumulasi",
            "Harga bergerak mendatar sementara aliran dana tetap masuk — "
            "pola khas barang diserap pelan-pelan.",
        )
    if sideways and (cmf < -0.03 or net_days < -2):
        return (
            "Distribusi",
            "Harga mendatar di area atas tapi dana keluar — barang dilepas "
            "tanpa menjatuhkan harga terlalu cepat.",
        )
    if trend >= 1.0 and cmf >= -0.02:
        return ("Markup", "Tren naik dengan aliran dana mendukung.")
    if trend >= 1.0 and cmf < -0.02:
        return (
            "Markup melemah",
            "Harga masih naik tapi aliran dana berbalik negatif — divergensi.",
        )
    if trend <= -1.0 and cmf <= 0.02:
        return ("Markdown", "Tren turun dengan tekanan jual dominan.")
    if trend <= -1.0 and cmf > 0.02:
        return (
            "Markdown melemah",
            "Harga turun tapi ada serapan di bawah — kemungkinan awal akumulasi.",
        )
    return ("Netral", f"Volatilitas {band:.1%}, belum ada arah dominan.")


# ---------------------------------------------------------------- profil volume

def volume_profile(d: pd.DataFrame, bins: int = 24, lookback: int = 120) -> pd.DataFrame:
    """Distribusi volume per level harga. POC = level dengan volume terbesar."""
    w = d.tail(lookback)
    if w.empty:
        return pd.DataFrame(columns=["low", "high", "mid", "volume", "share"])

    lo, hi = float(w["Low"].min()), float(w["High"].max())
    if hi <= lo:
        return pd.DataFrame(columns=["low", "high", "mid", "volume", "share"])

    edges = np.linspace(lo, hi, bins + 1)
    idx = np.clip(np.digitize(w["TP"].to_numpy(), edges) - 1, 0, bins - 1)
    vol = np.zeros(bins)
    np.add.at(vol, idx, w["Volume"].to_numpy(dtype=float))

    out = pd.DataFrame(
        {
            "low": edges[:-1],
            "high": edges[1:],
            "mid": (edges[:-1] + edges[1:]) / 2,
            "volume": vol,
        }
    )
    total = out["volume"].sum() or 1.0
    out["share"] = out["volume"] / total
    return out


def value_area(vp: pd.DataFrame, coverage: float = 0.70) -> dict:
    """POC dan batas value area yang menampung `coverage` dari total volume."""
    if vp.empty:
        return {}
    order = vp.sort_values("volume", ascending=False)
    poc = float(order.iloc[0]["mid"])
    picked, acc = [], 0.0
    for _, row in order.iterrows():
        picked.append(row)
        acc += row["share"]
        if acc >= coverage:
            break
    sel = pd.DataFrame(picked)
    return {"poc": poc, "va_low": float(sel["low"].min()), "va_high": float(sel["high"].max())}


# ---------------------------------------------------------------- ringkasan

def summarize(d: pd.DataFrame, ticker: str) -> dict:
    """Satu baris ringkasan untuk tabel screening."""
    last = d.iloc[-1]
    prev = d["Close"].iloc[-2] if len(d) > 1 else last["Close"]
    phase, _ = detect_phase(d)
    score = bandar_score(d)

    def _f(key, default=np.nan):
        val = last.get(key, default)
        return float(val) if np.isfinite(val) else np.nan

    chg_20d = np.nan
    if len(d) > 21:
        chg_20d = (last["Close"] / d["Close"].iloc[-21] - 1) * 100

    return {
        "Kode": display_ticker(ticker),
        "Harga": float(last["Close"]),
        "% Hari": (last["Close"] / prev - 1) * 100 if prev else np.nan,
        "% 20 Hari": chg_20d,
        "Skor": score,
        "Sinyal": score_label(score),
        "Fase": phase,
        "CMF 20h": _f("CMF20"),
        "MFI 14": _f("MFI14"),
        "Volume vs Rata-rata": _f("VolRatio"),
        "Hari Akumulasi (20h)": int(d["AccDay"].tail(20).sum()),
        "Hari Distribusi (20h)": int(d["DistDay"].tail(20).sum()),
        "Nilai Transaksi (Rp M)": float(d["TurnoverIDR"].tail(20).mean()) / 1e9,
    }


def recent_footprints(d: pd.DataFrame, limit: int = 12) -> pd.DataFrame:
    """Hari-hari dengan volume luar biasa beserta tafsirannya."""
    w = d[d["BigVol"]].tail(limit).copy()
    if w.empty:
        return pd.DataFrame(columns=["Tanggal", "Harga", "Volume vs Rata-rata", "Tutup di", "Tafsiran"])

    def _read(row):
        if row["Absorption"]:
            return "Serapan — volume besar, rentang sempit"
        if row["CloseLoc"] >= CLOSE_HIGH:
            return "Pembelian agresif"
        if row["CloseLoc"] <= CLOSE_LOW:
            return "Pelepasan barang"
        return "Tarik-menarik, belum jelas"

    return pd.DataFrame(
        {
            "Tanggal": w.index.strftime("%d %b %Y"),
            "Harga": w["Close"].round(0).astype(int),
            "Volume vs Rata-rata": w["VolRatio"].round(1),
            "Tutup di": (w["CloseLoc"] * 100).round(0).astype(int).astype(str) + "% rentang",
            "Tafsiran": w.apply(_read, axis=1),
        }
    ).iloc[::-1]
