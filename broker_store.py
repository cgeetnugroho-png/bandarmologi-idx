"""
broker_store.py — Penyimpanan data broker summary manual ke Google Sheets.

Data broker summary per-saham (top buyer/seller broker) tidak tersedia gratis
dari sumber resmi manapun untuk IDX — hanya lewat platform berbayar (Stockbit
Pro, RTI Business, IPOT, dsb). Modul ini TIDAK mengambil data itu secara
otomatis (scraping akun berbayar orang lain melanggar ToS platform tsb).
Sebagai gantinya, pengguna menyalin sendiri angka yang mereka lihat di
aplikasi mereka dan menempelkannya ke dashboard; modul ini yang menyimpannya
supaya bisa dilihat trennya dari waktu ke waktu.

Penyimpanan pakai Google Sheets (gratis, milik pengguna sendiri) lewat
service account. Lihat README bagian "Setup Broker Summary" untuk cara
konfigurasinya.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
WORKSHEET_NAME = "broker_summary"
COLUMNS = ["Tanggal", "Kode", "Broker", "Sisi", "Lot", "Nilai", "AvgHarga"]


def is_configured() -> bool:
    """True bila secrets Google Sheets sudah diisi (lihat README)."""
    try:
        return "gcp_service_account" in st.secrets and "broker_sheet" in st.secrets
    except Exception:
        return False


@st.cache_resource(show_spinner=False)
def _client():
    import gspread
    from google.oauth2.service_account import Credentials

    info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def _worksheet():
    import gspread

    gc = _client()
    spreadsheet_id = st.secrets["broker_sheet"]["spreadsheet_id"]
    sh = gc.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=WORKSHEET_NAME, rows=2000, cols=len(COLUMNS))
        ws.append_row(COLUMNS)
    return ws


def load_all() -> pd.DataFrame:
    """Ambil seluruh riwayat broker summary yang tersimpan."""
    ws = _worksheet()
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame(columns=COLUMNS)
    df = pd.DataFrame(records)
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = None
    return df[COLUMNS]


def save_for(ticker: str, tanggal_str: str, rows: pd.DataFrame) -> int:
    """Ganti baris (ticker, tanggal) yang lama dengan `rows` yang baru.

    Mengembalikan jumlah baris yang tersimpan untuk kombinasi itu.
    """
    ws = _worksheet()
    existing = load_all()
    keep = existing[~((existing["Kode"] == ticker) & (existing["Tanggal"] == tanggal_str))]

    new_rows = rows.copy()
    new_rows["Kode"] = ticker
    new_rows["Tanggal"] = tanggal_str
    new_rows = new_rows[COLUMNS]

    combined = pd.concat([keep, new_rows], ignore_index=True)

    ws.clear()
    ws.append_row(COLUMNS)
    if not combined.empty:
        ws.append_rows(combined.astype(str).values.tolist())

    return len(new_rows)

