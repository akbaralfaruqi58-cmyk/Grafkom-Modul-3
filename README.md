# Modul 3 — Praktikum Grafika Komputer
## Lab 1: Monumen Tugu Pahlawan dan Museum 10 November

Proyek ini melanjutkan **kode starter asli `Module3_Code(2).zip`**. Struktur dan implementasi dasar Modul 3 dipertahankan; penyesuaian Lab 1 menambahkan model bangunan yang dipilih, konversi koordinat model, telusuran vertex, dan viewer Three.js.

## Isi proyek

- `data/mymodel.obj` — model Tugu Pahlawan siap dipakai oleh loader OBJ NumPy / Three.js.
- `data/mymodel.mtl` dan `data/*.png` — material dan texture sumber.
- `data/source/` — file OBJ, MTL, GLB sumber yang disimpan apa adanya.
- `prepare_tugu.py` — menyiapkan OBJ dari sumber: Z-up ke Y-up, pusat X/Z, alas Y=0, tinggi 2 satuan; topology dan UV dijaga.
- `lab1_analysis.py` — menghitung statistik model, membaca kolom M/V, menelusuri satu vertex melalui enam coordinate space, dan memeriksa determinan handedness.
- `docs/Lab1_Analisis.md` — catatan hasil, perhitungan, refleksi, dan daftar sumber.
- `web/` — viewer OBJ + MTL + texture menggunakan Three.js dan OrbitControls.
- File Python lainnya (`transforms.py`, `objio.py`, `raster3d.py`, `raytrace.py`, `broken_scene.py`, dan seterusnya) tetap dipertahankan sebagai fondasi Lab 2 dan Lab 3.

## Statistik aset

| Item | Jumlah / nilai |
|---|---:|
| Vertex | 5.637 |
| Koordinat UV | 5.637 |
| Normal | 5.637 |
| Face segitiga | 4.227 |
| Object section | 52 |
| Material unik | 15 |
| Ukuran setelah normalisasi | 1,581812 × 2,000000 × 0,506177 |

Syarat Lab 1 yaitu minimal 200 segitiga dan permukaan ber-UV terpenuhi. UV asli tidak dinormalisasi ke 0..1; viewer mengatur texture wrap ke `RepeatWrapping`.

## Persiapan Windows

Buka PowerShell di folder `Module3`.

```powershell
python --version
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Jika PowerShell memblokir aktivasi virtual environment, jalankan perintah Python memakai interpreter `.venv\Scripts\python.exe`, atau gunakan Command Prompt untuk aktivasi.

## Menjalankan Lab 1

```powershell
python prepare_tugu.py
python lab1_analysis.py
python tests.py
```

`prepare_tugu.py` membangun `data/mymodel.obj` dari `data/source/`. Jalankan lagi jika ingin membuat ulang model normalisasi dari file sumber. Jangan mengubah OBJ di `data/source/`.

`lab1_analysis.py` menulis hasil ke:

- `out/lab1_vertex_trace.txt`
- `out/lab1_model_info.json`

`tests.py` memeriksa E1–E5, bentuk pipeline, render segitiga, serta validasi aset Lab 1 (minimal 200 triangle, UV lengkap, tinggi model 2 unit, MTL tersedia). Pengujian referensi temple bawaan starter akan dilewati bila `data/pusaka_model.obj` belum dibuat; ini bukan pengujian kesamaan frame Tugu Pahlawan.

## Menjalankan viewer 3D di browser

Pastikan terminal masih berada pada folder `Module3`, lalu:

```powershell
python -m http.server 8000
```

Buka alamat berikut:

```text
http://localhost:8000/web/
```

Kontrol viewer:

- Drag mouse: orbit model.
- Scroll: zoom.
- `Reset kamera`: mengembalikan sudut kamera awal.
- `Tampilkan wireframe`: melihat struktur mesh.
- `Ekspor PPM 512 × 512`: menyimpan frame viewer untuk tahap Lab 3.

Three.js dimuat dari CDN, jadi browser memerlukan koneksi internet. Jangan membuka `web/index.html` langsung sebagai `file://`; jalankan server lokal agar OBJ dan texture dapat dimuat.

Alternatif server sesuai starter:

```powershell
npx serve .
```

Lalu buka `/web/` pada alamat lokal yang ditampilkan oleh `serve`.

## Toolchain yang harus dicatat

Catat hasil di `docs/Lab1_Analisis.md` setelah pengujian di laptop:

```powershell
python --version
python -c "import numpy; print(numpy.__version__)"
node --version
```

Tambahkan nama dan versi browser, tanggal pengujian, serta screenshot viewer ketika sudah berhasil dibuka di laptop. Jangan menganggap viewer sudah diverifikasi hanya dari pengujian kode di komputer lain.

## Kelanjutan Lab 2 dan Lab 3

- Lab 2 akan melanjutkan `transforms.py`, `objio.py`, `raster3d.py`, `raytrace.py`, `broken_scene.py`, `metrics.py`, dan `tests.py` untuk pipeline Tugu Pahlawan.
- Lab 3 akan melanjutkan `web/viewer.js` untuk pengukuran real-time dan pencocokan frame NumPy vs WebGL.
- Tugas Analisis A1–A6 dikerjakan setelah bukti dari seluruh lab tersedia.

## Lisensi dan sumber aset

Model, MTL, dan texture disertakan berdasarkan file yang diberikan pengguna. File unggahan tidak memuat keterangan lisensi atau atribusi sumber. Status tersebut harus diperiksa dan dicatat sebelum proyek dipublikasikan ke GitHub Pages atau repository publik.
