# Modul 3 — Praktikum Grafika Komputer
## Transformasi 3D, Proyeksi, Texture, dan Real-Time Rendering

**Objek 3D:** Monumen Tugu Pahlawan dan Museum 10 November, Surabaya  
**Repository:** [Grafkom-Modul-3](https://github.com/akbaralfaruqi58-cmyk/Grafkom-Modul-3)  
**Branch kerja:** `master`  
**Cakupan:** Lab 1, Lab 2, Lab 3, serta persiapan Tugas Analisis A1–A6.

Proyek ini dikembangkan dari **kode starter asli `Module3_Code(2).zip`**. Model candi pada contoh modul diganti dengan model Tugu Pahlawan. Implementasi Lab 1–2 menggunakan Python dan NumPy, sedangkan Lab 3 menambahkan viewer real-time Three.js/WebGL di browser.

---

## 1. Ringkasan model

Model OBJ hasil normalisasi memiliki karakteristik berikut.

| Data | Hasil |
|---|---:|
| Vertex | 5.637 |
| Koordinat UV (`vt`) | 5.637 |
| Normal (`vn`) | 5.637 |
| Face segitiga | 4.227 |
| Object pada OBJ | 52 |
| Material unik pada MTL | 15 |
| Material dengan diffuse texture PNG | 10 |
| Ukuran bounding box (X, Y, Z) | 1,581812 × 2,000000 × 0,506177 |

`prepare_tugu.py` mengubah orientasi model dari Z-up ke Y-up, memusatkan model pada sumbu X/Z, dan menempatkan alas pada Y=0 dengan tinggi 2 satuan. Indeks face, UV, normal, serta assignment material dipertahankan. UV yang berada di luar rentang 0–1 ditangani dengan repeat wrapping pada viewer.

### Struktur utama

- `data/source/` — aset sumber OBJ, MTL, GLB, dan texture.
- `data/mymodel.obj`, `data/mymodel.mtl`, `data/*.png` — model hasil normalisasi dan texture.
- `prepare_tugu.py` — persiapan model untuk Lab 1.
- `make_model.py` — membangun ulang model dan menyalin aset yang diperlukan ke `web/assets/`.
- `transforms.py`, `worked_example.py`, `lab1_analysis.py` — transformasi dan analisis Lab 1.
- `objio.py`, `material_io.py` — loader OBJ/MTL.
- `raster3d.py`, `raytrace.py`, `broken_scene.py` — renderer NumPy, ray tracer, dan diagnosis scene Lab 2.
- `uv_demo.py`, `mipmap_demo.py` — eksperimen UV dan mipmap.
- `tests.py` — pengujian otomatis E1–E5 dan integrasi model.
- `run_lab2.py`, `run_lab3.py` — rangkaian eksperimen Lab 2 dan persiapan sisi Python Lab 3.
- `lab3_benchmark.py`, `lab3_capture.py`, `collect_lab3_results.py` — benchmark, ekspor frame acuan NumPy, dan pengumpulan hasil WebGL.
- `web/` — viewer Three.js/WebGL dan aset statis yang dapat di-hosting.
- `docs/` — analisis per lab dan gambar bukti.
- `out/` — keluaran eksperimen, PPM, JSON, dan log. Folder ini dibuat otomatis dan diabaikan Git.
- `.github/workflows/deploy-pages.yml` — workflow publikasi GitHub Pages untuk branch `main`.

---

## 2. Toolchain dan instalasi Windows

Lingkungan pengujian pada laptop yang tercatat di log:

- Windows 10, build 19045.
- Python 3.12.0.
- Node.js dan browser diperlukan untuk menjalankan viewer Three.js.
- NumPy dan Pillow dipasang melalui `requirements.txt`.

Buka PowerShell pada folder `Module3`:

```powershell
python --version
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Jika aktivasi virtual environment diblokir oleh kebijakan PowerShell, gunakan Command Prompt atau panggil `.venv\Scripts\python.exe` secara langsung.

### Reproduksi model dan pengujian

```powershell
python make_model.py
python tests.py
```

`make_model.py` menghasilkan `data/mymodel.obj` dan `data/mymodel.mtl`, lalu menyalin OBJ, MTL, dan diffuse texture ke `web/assets/`. Jalankan perintah ini setelah clone bersih atau ketika ingin membangun ulang aset dari folder `data/source/`.

---

## 3. Lab 1 — Model, transformasi, dan coordinate space

Lab 1 menggunakan model Tugu Pahlawan sebagai input sendiri. Konvensi transformasi yang dipakai adalah **vektor kolom** (`p' = M @ p`), sistem right-handed, kamera menghadap −Z, dan NDC OpenGL berada pada rentang [−1, 1]. Komposisi matriks dibaca dari kanan ke kiri.

Transformasi yang digunakan pada telusuran vertex:

- Skala: identitas.
- Rotasi Y: 35°.
- Translasi: (0,15; 0; −0,10).
- Matriks model: `M = T @ Ry @ S`.
- Kamera: eye = (3,2; 2,5; 4,0), target = (0; 0,9; 0).
- Proyeksi: FOV 45°, aspect 1, near 0,1, far 50.

Satu vertex OBJ (indeks 1-based **5213**) ditelusuri sebagai berikut.

| Coordinate space | Koordinat (x, y, z, w) |
|---|---|
| Object | (0,348566; 2,000000; 0,250113; 1) |
| World = M p | (0,578988; 2,000000; −0,095049; 1) |
| View = V (M p) | (0,511490; 0,964267; −4,764210; 1) |
| Clip = P (V M p) | (1,234846; 2,327945; 4,582904; 4,764210) |
| NDC = clip.xyz / clip.w | (0,259192; 0,488632; 0,961944) |
| Screen 512 × 512 | (322,353; 130,910; 0,961944) |

Nilai depth buffer setelah pemetaan NDC z dari [−1, 1] ke [0, 1] adalah **0,980972**. Untuk dua langkah pertama, hasil perkalian `M p` dihitung dengan tangan dan menghasilkan world position yang sama hingga enam desimal. Rincian matriks dan telusuran kolom M/V tersedia pada `docs/Lab1_Analisis.md` serta keluaran `out/lab1_vertex_trace.txt` setelah skrip dijalankan.

Perintah Lab 1:

```powershell
python prepare_tugu.py
python lab1_analysis.py
python tests.py
```

---

## 4. Lab 2 — Pipeline NumPy, z-buffer, texture, dan diagnosis bug

Lab 2 membangun pipeline 3D dari nol dengan NumPy: transformasi 4×4, clipping near-plane, perspective divide, viewport, rasterisasi barycentric, z-buffer, sampling bilinear, UV perspective-correct, Lambert lighting, dan mipmap. Ray tracer terpisah menggunakan pinhole ray dan algoritma Möller–Trumbore.

Jalankan seluruh eksperimen Lab 2:

```powershell
python run_lab2.py
```

Perintah terpisah untuk debugging:

```powershell
python tests.py
python raster3d.py --model data/mymodel.obj --w 128 --h 128 --out out/tugu_raster.ppm
python raytrace.py --model data/mymodel.obj --w 128 --h 128 --out out/tugu_raytrace.ppm
python compare.py out/tugu_raster.ppm out/tugu_raytrace.ppm --diff out/tugu_raster_ray_difference_x6.ppm --scale 6
python broken_scene.py --all
python uv_demo.py
python mipmap_demo.py
```

### Hasil Lab 2

- Contoh E1: titik (2, 3, 4) setelah translasi dan rotasi menjadi (3, 3, −3); perspective divide dengan focal distance 2 menghasilkan (2, 2). Urutan transformasi yang ditukar menghasilkan titik berbeda.
- Contoh E2: kamera digeser +1 pada sumbu X menghasilkan koordinat yang sama dengan model digeser −1 pada sumbu X.
- Contoh E3: near plane z=−1 dipetakan ke NDC z=−1 dan far plane z=−9 dipetakan ke NDC z=+1; titik z=−3 menghasilkan NDC z=0,5.
- Contoh E4: UV screen-linear menghasilkan `u=0,5`, sedangkan UV perspective-correct menghasilkan `u=0,1`.
- Contoh E5: interpolasi depth barycentric menghasilkan `0,625`.
- Frame rasterizer dan ray tracer pada resolusi 128×128: **PSNR = ∞ dB, SSIM = 1,000, mean difference = 0, dan max difference = 0** pada konfigurasi uji.
- Mipmap empat level menurunkan energi frekuensi tinggi dari **0,094763** menjadi **0,063216** (sekitar 33,3% lebih rendah pada pengukuran ini).

### Diagnosis tiga bug

| Kasus | Diagnosis dan perbaikan | Hasil terukur |
|---|---|---|
| Inside-out | Urutan face dibalik dan back-face culling menghilangkan face yang seharusnya terlihat. Winding model sumber tidak seragam; urutan face sumber dipulihkan dan culling dinonaktifkan untuk aset ini. | SSIM bad vs fixed 0,3972; fragment tertulis 657 menjadi 3.439. |
| Z-fighting | Near=0,001 dan depth 16-bit membuat dua permukaan dekat sulit dibedakan. Near dinaikkan menjadi 1,0 dan pipeline normal menggunakan depth float64. | Pixel berbeda dari referensi float: 2.852 (near 0,001/16-bit), 184 (near 1,0/16-bit), 0 (float64). SSIM akhir 1,000. |
| Stretched | Urutan perkalian matriks salah. Dengan vektor kolom, perbaikannya `M = T @ R @ S`: skala lokal, rotasi, lalu translasi. | SSIM bad vs fixed 0,3790; PSNR 14,23 dB. |

Gambar bukti berada di `docs/evidence/bug_diagnostics.png` dan `docs/evidence/zfight_depth_histogram.png`. Hasil PPM/JSON mentah dibuat pada `out/` saat eksperimen dijalankan.

---

## 5. Lab 3 — Real-time rendering Three.js/WebGL

Viewer pada `web/` memuat `mymodel.obj`, `mymodel.mtl`, dan 10 texture PNG dari `web/assets/`. Implementasi menggunakan Three.js r160, OBJLoader, MTLLoader, OrbitControls, directional light, sRGB output, dan shadow map. Model dan texture disimpan lokal; file JavaScript Three.js/loader diambil dari CDN sehingga browser memerlukan koneksi internet.

Viewer memiliki kontrol:

- **Reset kamera acuan** — mengembalikan kamera ke posisi referensi yang dipakai untuk perbandingan.
- **Wireframe** — menampilkan kerangka segitiga.
- **Grid** — menampilkan grid lantai.
- **Bayangan** — mengaktifkan shadow map dan lantai penerima bayangan.
- **Ekspor PPM 512 × 512** — mengunduh frame dengan ukuran tetap.
- **Ukur frame time** — mengukur waktu render WebGL dan mengunduh `webgl_benchmark.json`.

Persiapan Python Lab 3:

```powershell
python make_model.py
python tests.py
python run_lab3.py
```

Jalankan viewer dari root proyek:

```powershell
npx serve web
```

Buka URL lokal yang dicetak oleh `serve`. Alternatif jika paket `serve` tidak tersedia:

```powershell
python -m http.server 8000
```

Kemudian buka `http://localhost:8000/web/`.

### Hasil pengukuran Lab 3 dari laptop

**Benchmark renderer Python** diambil pada Windows 10 build 19045 dengan Python 3.12.0, model 4.227 segitiga, resolusi 128×128, tiga pengulangan setelah satu warm-up. Waktu pemuatan model dan texture tidak termasuk.

| Renderer | Median frame time | Perkiraan laju frame |
|---|---:|---:|
| NumPy rasterizer | 987,2623 ms | 1,01 FPS |
| NumPy ray tracer | 2.830,7557 ms | 0,35 FPS |

Ray tracer memerlukan **2,867×** waktu rasterizer pada pengukuran tersebut. Keduanya merupakan implementasi CPU sederhana; angka ini bukan benchmark GPU/WebGL.

**Perbandingan frame NumPy dan WebGL** dilakukan pada resolusi 512×512 setelah ekspor dari viewer dan pemanggilan `compare.py`.

| Metrik | Hasil |
|---|---:|
| PSNR NumPy vs WebGL | 16,75 dB |
| SSIM global | 0,4131 |
| Mean absolute difference | 23,391 |
| Maximum absolute difference | 206 |
| Mean frame WebGL terukur | 0,2675 ms |
| Perkiraan FPS dari mean frame | 3.738,32 |

PSNR 16,75 dB dan SSIM 0,4131 menunjukkan perbedaan global yang masih cukup besar; kedua frame **belum dapat dianggap cocok secara visual**. Periksa `docs/evidence/lab3_webgl_numpy_difference_x6.ppm` (dibuat setelah langkah compare) untuk melihat letak residual. Perbedaan dapat berasal dari raster coverage/anti-aliasing, filtering mipmap, normal, material, dan shading. Bila selisih tampak sebagai pergeseran luas di bagian dalam model, periksa kembali kamera, model transform, axis, dan UV. Nilai FPS merupakan kebalikan dari mean render time pada pengukuran viewer, bukan jaminan frame rate layar yang berkelanjutan.

**Hard-shadow demo NumPy** menghasilkan PSNR = ∞ dB dan SSIM = 1,000 antara rasterizer dan ray tracer pada pengujian tersebut. Implementasi shadow NumPy menggunakan pendekatan visibility per-face dari centroid triangle; Three.js menggunakan shadow map. Ray tracer saat ini belum memiliki secondary reflection atau global illumination, sehingga tidak diklaim menghasilkan refleksi yang lebih baik.

### Keputusan renderer

- **Viewer real-time:** Three.js/WebGL rasterisation dipilih karena berjalan di GPU dan mendukung orbit/zoom interaktif. Benchmark Python menunjukkan ray tracer CPU sederhana lebih lambat, sedangkan pengukuran WebGL browser berasal dari jalur rendering GPU yang berbeda.
- **Beauty shot:** implementasi ray tracer saat ini belum menyediakan pantulan sekunder, global illumination, atau soft shadow. Karena itu, untuk fitur yang benar-benar tersedia sekarang, WebGL dengan shadow map lebih siap dipakai. Ray/path tracing baru layak dipilih untuk beauty shot setelah fitur pencahayaan dan refleksi dikembangkan.
- Pilihan dapat berubah saat kebutuhan refleksi glossy/global illumination menjadi utama, tersedia GPU dengan RT core/BVH, mesh menjadi jauh lebih besar, atau target frame-time interaktif menjadi batas utama.

---

## 6. Hasil pengujian otomatis

Pengujian terakhir pada proyek Lab 3 melaporkan **14/14 checks passed**. Pemeriksaan mencakup E1–E5, bentuk pipeline dan viewport, render satu segitiga dengan z-buffer, near-plane clipping, struktur OBJ/UV/MTL Tugu, mipmap empat level, kesesuaian frame referensi, rasterizer vs ray tracer, hard-shadow ray test, serta validasi aset statis web.

Jalankan kembali kapan saja dengan:

```powershell
python tests.py
```

Untuk membuat ulang seluruh eksperimen Lab 2 dan persiapan Lab 3:

```powershell
python run_lab2.py
python run_lab3.py
```

Catatan: `run_lab3.py` menyiapkan hasil sisi Python dan baseline NumPy 512×512. Ekspor frame browser, benchmark WebGL, serta `collect_lab3_results.py` tetap dijalankan sesuai langkah Lab 3 di atas.

---

## 7. Publikasi GitHub Pages

Repository ini menggunakan branch **`main`**. Workflow `.github/workflows/deploy-pages.yml` telah dikonfigurasi untuk memicu deployment ketika ada push ke branch `main` yang mengubah file website/aset terkait, dan juga menyediakan pemicu manual (`workflow_dispatch`). Workflow menerbitkan isi folder `web/`.

Langkah publikasi:

1. Commit dan push perubahan ke `main`.
2. Pada repository GitHub, buka **Settings → Pages**.
3. Pada **Build and deployment → Source**, pilih **GitHub Actions**.
4. Buka tab **Actions** dan pastikan workflow deployment selesai dengan status sukses.
5. Setelah deployment berhasil, catat URL Pages yang diberikan GitHub pada bagian ini: **Belum dicatat**.

Repository: [https://github.com/akbaralfaruqi58-cmyk/Grafkom-Modul-3](https://github.com/akbaralfaruqi58-cmyk/Grafkom-Modul-3). URL GitHub Pages tidak dicantumkan sebelum deployment benar-benar berhasil.

---

## 8. Dokumentasi dan bukti

Catatan analisis:

- [Analisis Lab 1](docs/Lab1_Analisis.md)
- [Analisis Lab 2](docs/Lab2_Analisis.md)
- [Analisis Lab 3](docs/Lab3_Analisis.md)

Gambar bukti yang tersedia di repository:

- [Rasterizer vs ray tracer](docs/evidence/raster_vs_raytrace.png)
- [Diagnosis tiga bug](docs/evidence/bug_diagnostics.png)
- [Histogram depth z-fighting](docs/evidence/zfight_depth_histogram.png)
- [UV naif vs perspective-correct](docs/evidence/uv_perspective_demo.png)
- [Mipmap sebelum dan sesudah](docs/evidence/mipmap_comparison.png)
- [Crop hasil render Tugu Pahlawan](docs/evidence/tugu_pahlawan_raster_crop.png)
- [Baseline NumPy 512×512](docs/evidence/lab3_numpy_reference_512.png)
- [Perbandingan hard shadow](docs/evidence/lab3_hard_shadow_comparison.png)
- Citra selisih NumPy vs WebGL: `docs/evidence/lab3_webgl_numpy_difference_x6.ppm` — dibuat oleh langkah `compare.py` setelah frame WebGL diekspor.

---

## 9. Batasan dan status reproduksibilitas

- Texture PNG digunakan sebagai diffuse texture. Material alpha/transparency dan PBR penuh belum direproduksi seluruhnya pada renderer NumPy.
- OBJ sumber memiliki winding yang tidak sepenuhnya seragam; back-face culling dinonaktifkan untuk aset ini agar bagian model tidak hilang.
- Ray tracer merupakan implementasi referensi sederhana dengan biaya tinggi terhadap jumlah pixel dan segitiga; belum memakai BVH, secondary reflection, atau global illumination.
- Mipmap mengurangi energi frekuensi tinggi pada pengujian ini, tetapi kualitas visual tetap bergantung pada footprint texture dan sudut pandang.
- Viewer membutuhkan koneksi internet untuk mengambil library Three.js dari CDN.
- Pengujian `make_model.py` dan 14 checks sudah tercatat berhasil pada lingkungan Windows. Transkrip clone bersih penuh dan URL GitHub Pages belum tercatat pada log yang tersedia; keduanya perlu dilengkapi setelah clone/deploy dilakukan.

---

## 10. Checklist akhir Modul 3

- [x] Starter asli dipertahankan sebagai dasar proyek.
- [x] Lab 1: model Tugu, matriks M/V/P, telusuran kolom dan satu vertex.
- [x] Lab 2: pipeline NumPy, z-buffer, ray tracer, tiga diagnosis bug, UV perspective-correct, dan mipmap.
- [x] Lab 3: viewer Three.js/WebGL, OrbitControls, ekspor PPM, benchmark, serta perbandingan NumPy-WebGL.
- [x] Pengujian otomatis terakhir: 14/14 checks passed.
- [x] Naskah utama Tugas Analisis A1–A6 dan dokumen lampiran tabel/gambar telah disiapkan sebagai file Word terpisah.
- [ ] Jalankan reproduksi dari clone bersih dan simpan transkripnya.
- [ ] Deploy GitHub Pages dari branch `main` dan catat URL live.

