# Dashboard Bandarmologi IDX

Membaca jejak akumulasi dan distribusi saham Bursa Efek Indonesia dari pola
harga dan volume harian.

## Menjalankan

```bash
pip install -r requirements.txt
streamlit run app.py
```

Browser akan terbuka di `http://localhost:8501`.

## Isi

| Berkas | Fungsi |
|---|---|
| `app.py` | Tampilan dashboard: analisa satu saham dan screening watchlist |
| `bandar_core.py` | Mesin perhitungan indikator, skor, fase, dan profil volume |

## Cara skor dibaca

Skor 0-100. Di atas 58 condong akumulasi, di bawah 43 condong distribusi.
Tujuh komponen menyusunnya:

| Komponen | Bobot | Yang diukur |
|---|---|---|
| Aliran dana (CMF 20h) | 20% | Uang masuk atau keluar selama 20 hari |
| Arah OBV (20h) | 18% | Volume terakumulasi searah harga |
| Akumulasi A/D (20h) | 15% | Posisi penutupan dibobot volume |
| Harga vs VWAP 20h | 12% | Harga di atas atau di bawah rata-rata tertimbang |
| Hari akumulasi vs distribusi | 15% | Selisih hari ramai yang tutup kuat vs tutup lemah |
| Jejak lot besar (60h) | 12% | Arah hari bervolume dua kali lipat rata-rata |
| Ekspansi volume searah harga | 8% | Volume membesar saat harga naik |

## Fase pasar

Kerangka Wyckoff: akumulasi, markup, distribusi, markdown. Ambang trennya
dinormalisasi terhadap volatilitas masing-masing saham, sehingga saham
bergejolak tinggi tidak otomatis dianggap sedang tren.

## Batasan

Data broker summary tidak tersedia di sumber gratis, jadi program ini tidak
tahu broker mana yang membeli atau menjual, dan tidak melihat aliran dana
asing. Yang dibaca adalah sidik jari perilakunya di harga dan volume.
Harga dari Yahoo Finance tertunda sekitar 15 menit.

Alat bantu riset, bukan rekomendasi jual beli.

## Deploy ke Streamlit Community Cloud (gratis, paling mudah)

1. Push folder ini ke repo GitHub (bisa privat).
2. Buka share.streamlit.io, login dengan akun GitHub, klik New app.
3. Pilih repo dan branch-nya, isi Main file path dengan `app.py`, lalu Deploy.
4. Streamlit Cloud otomatis membaca `requirements.txt` dan
   `.streamlit/config.toml` yang sudah disiapkan di repo ini. Tidak perlu
   secret/API key karena data diambil langsung dari Yahoo Finance publik.
5. Setelah build selesai (1-3 menit), aplikasi punya URL publik
   `https://<nama-app>.streamlit.app` yang bisa dibuka dari mana saja.

## Deploy dengan Docker (self-host / Railway / Render / Fly.io / VPS)

Repo ini sudah menyertakan `Dockerfile`. Build dan jalankan lokal:

```bash
docker build -t bandarmologi-idx .
docker run -p 8501:8501 bandarmologi-idx
```

Untuk platform seperti Railway/Render/Fly.io, cukup hubungkan repo - mereka
mendeteksi `Dockerfile` secara otomatis dan menyuntikkan `$PORT` saat
runtime (sudah ditangani lewat `CMD` di Dockerfile).

Untuk VPS biasa (mis. via `systemd` atau `tmux`), jalankan langsung:

```bash
pip install -r requirements.txt
streamlit run app.py --server.port 80 --server.address 0.0.0.0
```

## Status pengujian

Sudah diverifikasi di lingkungan terpisah (2026-09-05):

- Semua dependency di `requirements.txt` terinstal bersih di Python 3.11.
- `bandar_core.py` diuji dengan data OHLCV sintetis - indikator (CMF, OBV,
  A/D, VWAP, MFI, ATR), skor bandarmologi, deteksi fase Wyckoff, volume
  profile, dan ringkasan screening semuanya menghasilkan angka yang wajar
  tanpa error.
- `streamlit run app.py` berhasil start tanpa exception dan menyajikan
  halaman dengan benar (dicek lewat request HTTP langsung ke server-nya).
- Pengambilan data live dari Yahoo Finance tidak bisa diuji dari lingkungan
  sandbox tersebut karena domain Yahoo Finance diblokir oleh kebijakan
  jaringan sandbox tersebut (bukan masalah pada kode). Saat dijalankan di
  komputer sendiri atau di-deploy ke Streamlit Cloud/VPS dengan akses
  internet normal, pengambilan data seharusnya berjalan seperti biasa -
  disarankan untuk mengetes sekali secara langsung setelah deploy untuk
  memastikan.

