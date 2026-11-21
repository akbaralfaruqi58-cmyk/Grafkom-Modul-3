# Modul 3 — Praktikum Grafika Komputer
## Lab 1–3: Monumen Tugu Pahlawan dan Museum 10 November

Proyek ini melanjutkan **kode starter asli `Module3_Code(2).zip`** dan hasil Lab 1 yang sudah disesuaikan dengan model Tugu Pahlawan. Lab 2 menambahkan pipeline 3D from-scratch berbasis NumPy, renderer rasterisasi dengan z-buffer, ray tracer pinhole, diagnosis tiga scene bermasalah, demonstrasi UV perspective-correct, serta mipmap empat level.

> **Model tugas:** Tugu Pahlawan dan Museum 10 November. Model OBJ memiliki 5.637 vertex, 5.637 UV, 5.637 normal, dan 4.227 face segitiga. File MTL mendefinisikan 15 material; 10 material memiliki texture map PNG.

## Isi proyek

- `data/mymodel.obj`, `data/mymodel.mtl`, `data/*.png` — model Tugu Pahlawan yang sudah dinormalisasi, material, dan texture.
- `data/source/` — file OBJ, MTL, GLB, dan texture sumber.
- `prepare_tugu.py` — konversi Z-up ke Y-up, pemusatan X/Z, alas Y=0, tinggi 2 satuan; indeks face dan UV dipertahankan.
- `lab1_analysis.py`, `docs/Lab1_Analisis.md` — statistik model, matriks Model/View, dan telusuran satu vertex.
- `transforms.py` — transformasi 4×4, perspektif, lookAt, viewport.
- `objio.py`, `material_io.py` — loader OBJ/MTL minimal; mempertahankan UV dan assignment material per face.
- `raster3d.py` — clipping near-plane, perspective divide, viewport, barycentric rasterisation, z-buffer float64, interpolasi UV perspective-correct, bilinear sampling, Lambert lighting, pemilihan mip level, dan opsi eksperimen hard shadow.
- `raytrace.py` — ray pinhole, Möller–Trumbore, nearest hit, material/texture dan shading yang sama dengan rasterizer; opsi eksperimen hard shadow.
- `broken_scene.py` — diagnosis inside-out, z-fighting, dan stretched; menyimpan render rusak, hasil perbaikan, citra depth dan laporan JSON.
- `uv_demo.py` — render UV screen-linear yang salah dibanding UV perspective-correct.
- `mipmap_demo.py` — membangun piramida mip empat level dengan box filtering pada linear light dan render sebelum/sesudah.
- `metrics.py`, `compare.py` — PSNR, SSIM global sederhana, mean/max absolute difference.
- `tests.py` — pengujian E1–E5, clipping, Tugu OBJ/MTL, mipmap, frame referensi, raster-vs-raytrace, hard-shadow ray test, dan bundle aset web.
- `run_lab2.py` — menjalankan seluruh pengujian dan eksperimen Lab 2 dalam satu perintah.
- `ref/tugu_raster_reference.ppm` — frame acuan Tugu yang dibekukan untuk memeriksa reproduksibilitas render.
- `docs/evidence/` — gambar bukti yang mudah dibuka dari Windows/GitHub.
- `out/` — keluaran mentah PPM, histogram, JSON, dan log dari pengujian.
- `web/` — viewer Three.js/WebGL Lab 3, aset statis `web/assets/`, OrbitControls, shadow map, ekspor PPM 512×512, dan benchmark browser.
- `sync_web_assets.py` — menyalin OBJ, MTL, dan diffuse PNG ke direktori static web agar aman untuk `npx serve web`/GitHub Pages.
- `lab3_benchmark.py`, `lab3_capture.py`, `run_lab3.py` — benchmark Python dan pembentukan reference frame 512×512.
- `collect_lab3_results.py` — menggabungkan PPM/benchmark hasil unduhan browser ke metrik PSNR/SSIM dan laporan Markdown.
- `.github/workflows/deploy-pages.yml` — publikasi folder `web/` ke GitHub Pages setelah Pages Source disetel ke GitHub Actions.

## Toolchain

- Python 3.10 atau lebih baru (disarankan 3.11/3.12).
- NumPy 1.24 atau lebih baru.
- Pillow 10 atau lebih baru untuk membaca texture PNG dari MTL.
- Node.js + browser diperlukan untuk viewer Three.js di Lab 3; halaman viewer memakai Three.js r160 dari CDN, sedangkan model dan texture dibundel lokal.

## Persiapan Windows

Buka PowerShell di folder `Module3`:

```powershell
python --version
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Jika PowerShell memblokir aktivasi virtual environment, gunakan Command Prompt atau panggil `.venv\Scripts\python.exe` secara langsung.

## Menyiapkan model dan menjalankan Lab 1

```powershell
python prepare_tugu.py
python lab1_analysis.py
python tests.py
```

`prepare_tugu.py` membangun `data/mymodel.obj` dan `data/mymodel.mtl` dari `data/source/`. Geometry, normal, material assignment, dan UV disimpan; orientasi diubah dari Z-up ke Y-up. Jalankan kembali hanya bila ingin meregenerasi file hasil normalisasi dari sumber.

## Menjalankan Lab 2

Satu perintah untuk semua pengujian dan eksperimen:

```powershell
python run_lab2.py
```

Urutan internal:

1. Menjalankan `tests.py`.
2. Render Tugu Pahlawan dengan rasterizer NumPy pada 128×128.
3. Render model yang sama dengan ray tracer pada kamera/ukuran yang sama.
4. Membandingkan dua frame dengan PSNR, SSIM, dan citra selisih.
5. Membuat bukti bug inside-out, z-fighting, dan stretched.
6. Merender perbandingan UV naif vs perspective-correct.
7. Merender texture tanpa dan dengan mipmap.

Perintah terpisah (berguna saat debugging):

```powershell
python tests.py
python raster3d.py --model data/mymodel.obj --w 128 --h 128 --out out/tugu_raster.ppm
python raytrace.py --model data/mymodel.obj --w 128 --h 128 --out out/tugu_raytrace.ppm
python compare.py out/tugu_raster.ppm out/tugu_raytrace.ppm --diff out/tugu_raster_ray_difference_x6.ppm --scale 6
python broken_scene.py --all
python uv_demo.py
python mipmap_demo.py
```

## Hasil pengujian Lab 2 yang sudah dijalankan

- `tests.py`: **12/12 checks passed**.
- Rasterizer vs ray tracer Tugu (128×128): PSNR `inf` dB, SSIM `1.000`, mean absolute difference `0.0`, max difference `0`.
- UV Example E4: interpolasi naif `u=0.5`, perspective-correct `u=0.1`.
- Mipmap: high-frequency energy terukur turun dari `0.094763` menjadi `0.063216` (sekitar 33.3% lebih rendah untuk pengukuran gambar ini).
- Z-fighting: near `0.001` dengan depth 16-bit menghasilkan 2.852 pixel berbeda dari referensi float; near `1.0` dengan depth 16-bit turun menjadi 184 pixel; pipeline normal menggunakan buffer float64 sehingga hasil acuan float tidak terkuantisasi.

Angka dan pembahasan rinci: `docs/Lab2_Analisis.md`. Keluaran mentah dan log ada di `out/` setelah `python run_lab2.py`.

## Catatan interpretasi dan batasan

- Frame `ref/tugu_raster_reference.ppm` adalah baseline reproduksibilitas yang dibekukan dari renderer proyek ini. Validasi independen yang lebih penting adalah perbandingan rasterizer dengan ray tracer terpisah.
- Pipeline NumPy mengerjakan transformasi, clipping, rasterisasi, depth test, sampling, mipmap dan intersection. Pillow hanya dipakai untuk decode PNG; tidak dipakai untuk transformasi atau rendering.
- Renderer Lab 2 memakai flat-face Lambert lighting. Material alpha/transparency, PBR penuh, shadow map, reflection, dan tangent-space normal map belum diimplementasikan.
- OBJ Tugu dari sumber menunjukkan winding yang tidak sepenuhnya seragam. Karena itu, back-face culling tidak diaktifkan secara default; periksa/perbaiki winding sebelum mengaktifkannya.
- Ray tracer sederhana ini berkompleksitas O(jumlah pixel × jumlah segitiga), sehingga ditujukan sebagai referensi satu frame, bukan renderer real-time untuk mesh besar.
- File sumber yang diunggah tidak menyertakan keterangan lisensi/atribusi. Periksa lisensi aset sebelum repository atau viewer dipublikasikan secara publik.

## Menjalankan Lab 3

Siapkan model dan salin aset web (jalankan juga pada clone bersih):

```powershell
python make_model.py
python tests.py
```

Jalankan eksperimen Python untuk Lab 3:

```powershell
python run_lab3.py
```

Viewer browser:

```powershell
npx serve web
```

Buka URL yang ditampilkan. Klik **Reset kamera acuan**, pastikan Grid dan Bayangan mati, lalu **Ekspor PPM 512 × 512**. Pindahkan hasil unduhan `mymodel_three.ppm` ke `web/mymodel_three.ppm`. Klik **Ukur frame time** dan simpan `webgl_benchmark.json` ke `out/webgl_benchmark.json`.

Bandingkan:

```powershell
python compare.py out/tugu_raster_512.ppm web/mymodel_three.ppm --diff docs/evidence/lab3_webgl_numpy_difference_x6.ppm --scale 6
python collect_lab3_results.py --web-frame web/mymodel_three.ppm --web-benchmark out/webgl_benchmark.json
```

Laporan detail, tabel prediksi/pengukuran, batasan renderer, dan instruksi deploy ada di `docs/Lab3_Analisis.md`.

### Publikasi GitHub Pages

Workflow `.github/workflows/deploy-pages.yml` menerbitkan isi folder `web/` ke GitHub Pages pada push ke `m3-work`. Pada repository GitHub, atur **Settings → Pages → Build and deployment → Source = GitHub Actions**, lalu periksa tab **Actions**. Setelah deploy sukses, catat URL project site berbentuk `https://USERNAME.github.io/NAMA-REPOSITORY/` di laporan.

Jangan menghapus `data/source/`, `data/mymodel.obj`, `data/mymodel.mtl`, file PNG, atau `web/assets/` saat mengganti versi proyek.

### Gambar bukti Lab 2

- [Render Tugu: rasterizer vs ray tracer](docs/evidence/raster_vs_raytrace.png)
- [Diagnosis tiga bug: sebelum dan sesudah](docs/evidence/bug_diagnostics.png)
- [UV naif vs perspective-correct](docs/evidence/uv_perspective_demo.png)
- [Mipmap sebelum dan sesudah](docs/evidence/mipmap_comparison.png)
- [Histogram depth z-fighting](docs/evidence/zfight_depth_histogram.png)
- [Crop hasil render Tugu Pahlawan](docs/evidence/tugu_pahlawan_raster_crop.png)

### Gambar bukti Lab 3

- [Baseline NumPy 512×512](docs/evidence/lab3_numpy_reference_512.png)
- [Eksperimen hard shadow](docs/evidence/lab3_hard_shadow_comparison.png)
