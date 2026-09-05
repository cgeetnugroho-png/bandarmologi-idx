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
| `app.py` | Tampilan dashboard: analisa satu saham, screening watchlist, input & riwayat broker summary |
| `bandar_core.py` | Mesin perhitungan indikator, skor, fase, dan profil volume |
| `broker_store.py` | Baca/tulis data broker summary manual ke Google Sheets |

## Cara skor dibaca

Skor 0–100. Di atas 58 condong akumulasi, di bawah 43 condong distribusi.
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

Skor bandarmologi di atas murni dari pola harga & volume (tidak ada sumber
broker summary gratis untuk IDX per saham — lihat bagian "Broker summary
(manual)" di bawah untuk cara melengkapinya sendiri kalau Anda punya akses
ke Stockbit/RTI/IPOT). Harga dari Yahoo Finance tertunda sekitar 15 menit.

Alat bantu riset, bukan rekomendasi jual beli.

## Broker summary (manual)

Data top buyer/seller broker per saham **tidak tersedia gratis** dari sumber
resmi manapun untuk IDX:

- Halaman "Broker Summary" resmi di idx.co.id itu gratis, tapi hanya
  agregat per broker untuk **seluruh pasar** dalam satu hari — tidak bisa
  difilter per saham.
- Data per-saham (siapa net-buy/net-sell saham tertentu) hanya ada di
  platform berbayar: Stockbit Pro/Snips, RTI Business, IPOT, dsb.
- IDX Data Services adalah layanan data resmi berbayar untuk institusi/
  vendor data, bukan langganan API perorangan.

Karena itu, app ini menyediakan menu **Input broker summary** tempat Anda
menyalin sendiri angka yang Anda lihat di aplikasi Anda (mis. Stockbit) dan
menempelkannya ke tabel di dashboard. Datanya disimpan ke **Google Sheets
milik Anda sendiri** (bukan server ini) lewat service account, supaya bisa
dilihat trennya di menu **Riwayat broker summary**.

### Setup Broker Summary (sekali saja)

1. Buka [Google Cloud Console](https://console.cloud.google.com/), buat
   project baru (gratis, tidak perlu kartu kredit untuk ini).
2. Di project itu, aktifkan **Google Sheets API** dan **Google Drive API**
   (menu "APIs & Services" > "Enable APIs and Services").
3. Buat **Service Account** ("APIs & Services" > "Credentials" > "Create
   Credentials" > "Service Account"). Setelah dibuat, buka tab "Keys" pada
   service account itu, klik "Add Key" > "Create new key" > pilih **JSON**.
   Sebuah file JSON akan terunduh — ini kredensialnya, jangan dibagikan ke
   siapapun.
4. Buat Google Sheet baru (spreadsheet kosong biasa), lalu **Share** ke
   alamat email service account tadi (isinya seperti
   `nama@nama-project.iam.gserviceaccount.com`, ada di file JSON-nya)
   dengan akses **Editor**.
5. Salin **Spreadsheet ID** dari URL sheet-nya, yaitu bagian di antara
   `/d/` dan `/edit`:
   `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_DI_SINI/edit`.
6. Di Streamlit Community Cloud, buka app ini > menu titik tiga > **Settings**
   > **Secrets**, lalu isi dengan (nilai dari file JSON tadi):

   ```toml
   [gcp_service_account]
   type = "service_account"
   project_id = "isi-dari-json"
   private_key_id = "isi-dari-json"
   private_key = "-----BEGIN PRIVATE KEY-----\nisi-dari-json\n-----END PRIVATE KEY-----\n"
   client_email = "isi-dari-json"
   client_id = "isi-dari-json"
   token_uri = "https://oauth2.googleapis.com/token"

   [broker_sheet]
   spreadsheet_id = "SPREADSHEET_ID_DI_SINI"
   ```

7. Simpan — app akan restart otomatis. Menu **Input broker summary** dan
   **Riwayat broker summary** langsung aktif setelah itu.

Selama secrets belum diisi, kedua menu itu menampilkan peringatan dan tidak
mengganggu fitur lain (analisa harga/volume tetap jalan seperti biasa).

## Deploy ke Streamlit Community Cloud (gratis, paling mudah)

1. Push folder ini ke repo GitHub (bisa privat).
2. Buka [share.streamlit.io](https://share.streamlit.io), login dengan akun
   GitHub, klik **New app**.
3. Pilih repo dan branch-nya, isi **Main file path** dengan `app.py`, lalu
   **Deploy**.
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

Untuk platform seperti Railway/Render/Fly.io, cukup hubungkan repo — mereka
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
- `bandar_core.py` diuji dengan data OHLCV sintetis — indikator (CMF, OBV,
  A/D, VWAP, MFI, ATR), skor bandarmologi, deteksi fase Wyckoff, volume
  profile, dan ringkasan screening semuanya menghasilkan angka yang wajar
  tanpa error.
- `streamlit run app.py` berhasil start tanpa exception dan menyajikan
  halaman dengan benar (dicek lewat request HTTP langsung ke server-nya).
- Pengambilan data live dari Yahoo Finance **tidak** bisa diuji dari
  lingkungan sandbox ini karena domain Yahoo Finance diblokir oleh
  kebijakan jaringan sandbox tersebut (bukan masalah pada kode). Saat
  dijalankan di komputer sendiri atau di-deploy ke Streamlit Cloud/VPS
  dengan akses internet normal, pengambilan data seharusnya berjalan
  seperti biasa — disarankan untuk mengetes sekali secara langsung setelah
  deploy untuk memastikan.
