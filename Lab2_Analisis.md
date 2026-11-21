# Catatan Hasil Praktikum Modul 3 — Lab 2
## Pipeline NumPy, z-buffer, texture, ray tracing, dan diagnosis scene

**Objek:** Monumen Tugu Pahlawan dan Museum 10 November  
**Aset:** `data/mymodel.obj` beserta MTL dan texture PNG  
**Lingkup:** Menyesuaikan instruksi Lab 2 pada halaman 24 Modul 3. Model candi contoh diganti dengan model Tugu Pahlawan yang sudah dipakai pada Lab 1.

## 1. Implementasi pipeline from-scratch

Pipeline menggunakan vektor kolom dan perkalian pre-multiply, dengan konvensi right-handed, kamera menghadap ke −Z, serta NDC OpenGL pada rentang [−1,1].

| Tahap | Implementasi | Kegunaan |
|---|---|---|
| Model | `M @ p` | Memindahkan vertex dari object ke world space. |
| View | `V @ p_world` | Menyatakan world relatif terhadap pose kamera. |
| Projection | `P @ p_view` | Mengubah koordinat kamera ke homogeneous clip space. |
| Near clipping | `z_clip + w_clip >= 0` | Memotong bagian di belakang near plane sebelum divide. |
| Perspective divide | `clip.xyz / clip.w` | Mendapatkan koordinat NDC. |
| Viewport | NDC → pixel | Mengubah x/y ke koordinat layar dan membalik sumbu Y. |
| Rasterisation | Edge/barycentric | Menguji coverage pixel dalam segitiga. |
| Z-buffer | Menyimpan NDC z terkecil | Memilih fragment terdekat pada setiap pixel. |
| Texture | UV perspective-correct | Menghindari texture yang tampak berenang pada perspektif. |

File inti: `transforms.py`, `raster3d.py`, `objio.py`, `material_io.py`, `raytrace.py`.

## 2. Reproduksi Contoh E1–E5

Pengujian otomatis mencetak status pass/fail. Nilai numeriknya juga diperiksa langsung oleh fungsi tes.

| Contoh | Hasil numerik | Makna |
|---|---|---|
| E1 | `(2,3,4,1)` → translasi `(1,0,−1)` → `(3,3,3,1)` → rotasi Y 90° → `(3,3,−3,1)` → divide d=2 → `(2,2)` | Urutan transformasi mengubah hasil. |
| E2 | Kamera bergerak +1 pada X menghasilkan titik view `(4,0,0,1)`; model bergerak −1 pada X menghasilkan `(4,0,0,1)` | Dualitas kamera-vs-model. |
| E3 | near z=−1 → NDC z=−1; far z=−9 → NDC z=+1; z=−3 → NDC z=0.5 | Pemetaan perspektif non-linear. |
| E4 | UV naif `0.5`; UV perspective-correct `0.1` | UV harus menginterpolasi u/w dan 1/w, lalu dibagi. |
| E5 | `0.25×0.20 + 0.25×0.50 + 0.50×0.90 = 0.625` | Depth diinterpolasi dengan bobot barycentric. |

`uv_demo.py` menghasilkan tiga render: `out/uv_naive_linear.ppm`, `out/uv_perspective_correct.ppm`, dan `out/uv_linear_vs_correct_difference_x2.ppm`. Perbedaan pola pada dua render menunjukkan bahwa interpolasi UV linear pada screen space menghasilkan distorsi.

## 3. Rasterizer Tugu vs ray tracer

Rasterizer dan ray tracer memakai model, transformasi model, kamera, projection FOV, ukuran frame, material, UV, bilinear texture sampling, serta flat Lambert lighting yang sama.

| Pengukuran | Nilai |
|---|---:|
| Jumlah segitiga | 4.227 |
| Jumlah material | 15 |
| Material dengan texture PNG | 10 |
| Resolusi frame pembandingan | 128 × 128 |
| Pixel hit ray tracer | 1.417 dari 16.384 |
| PSNR raster vs ray tracer | ∞ dB |
| SSIM global raster vs ray tracer | 1.000 |
| Mean absolute difference | 0.0 |
| Maximum absolute difference | 0 |

Hasil ini berarti dua implementasi independen menghasilkan pixel identik pada konfigurasi pembandingan. `out/tugu_raster_ray_difference_x6.ppm` adalah citra selisih yang seluruh nilainya nol pada pengujian tersebut.

`ref/tugu_raster_reference.ppm` juga menyimpan satu frame acuan yang dibekukan. Tes mengulang render 128×128 dan memastikan PSNR lebih dari 60 dB terhadap acuan itu. Baseline tersebut menguji reproduksibilitas; pembandingan raster-vs-raytrace merupakan pemeriksaan silang independen.

## 4. Diagnosis dan perbaikan tiga bug

### 4.1 Inside-out / winding

**Bukti sebelum perbaikan:** scene sengaja membalik urutan vertex pada setiap face dan mengaktifkan back-face culling. Pada sudut kamera diagnosis, sebagian besar geometri tidak terlihat. Untuk model OBJ Tugu sumber, winding antarbagian tidak seluruhnya konsisten.

**Perbaikan:** mengembalikan urutan face dari OBJ sumber dan menonaktifkan back-face culling untuk aset ini. Pada mesh yang winding-nya konsisten, winding dapat diperbaiki dan culling diaktifkan.

**Hasil pengukuran:** SSIM gambar rusak terhadap gambar perbaikan `0.397`; PSNR `23.05 dB`. Fragment yang ditulis berubah dari `657` menjadi `3439` pada tampilan diagnosis.

Keluaran: `bug_inside-out_bad.ppm`, `bug_inside-out_fixed.ppm`, citra depth, dan `bug_inside-out_evidence.json`.

### 4.2 Z-fighting / presisi depth

**Bukti sebelum perbaikan:** dua quad hampir coplanar saling berpotongan pada kedalaman sekitar 9 unit. Near plane `0.001` dan depth buffer 16-bit membuat nilai depth sangat rapat sehingga permukaan saling berebut kode depth.

**Perbaikan:** dekatkan near plane ke volume scene (menjadi `1.0`) dan gunakan depth buffer float64 pada renderer normal. Renderer standar tidak melakukan kuantisasi 16-bit (`depth_bits=None`).

| Perbandingan dengan referensi float | Pixel yang berbeda | SSIM |
|---|---:|---:|
| near 0.001, depth 16-bit | 2.852 | 0.7647 |
| near 1.0, depth 16-bit | 184 | 0.9843 |
| near 1.0, depth float64 | 0 | 1.0000 |

Hasil antara (near=1 dengan depth 16-bit) membaik tetapi belum identik; residualnya menunjukkan keterbatasan kuantisasi 16-bit. Perbaikan akhir memakai float64, sesuai buffer default pada `raster3d.py`.

Keluaran: `bug_zfight_bad.ppm`, `bug_zfight_near1_16bit.ppm`, `bug_zfight_fixed.ppm`, `bug_zfight_depth_histogram.csv`, dan `bug_zfight_evidence.json`.

### 4.3 Stretched / urutan matriks

**Bukti sebelum perbaikan:** scene memakai susunan faktor skala, rotasi, dan translasi yang dibalik, dengan skala non-seragam. Akibatnya ukuran dan posisi objek berbeda dari transformasi yang dimaksud.

**Perbaikan:** gunakan urutan vektor kolom `M = T @ R @ S`, yaitu skala di object space, lalu rotasi, kemudian translasi world.

**Hasil pengukuran:** SSIM gambar salah terhadap hasil benar `0.379`; PSNR `14.23 dB`. Matriks buruk dan matriks perbaikan disimpan dalam JSON bukti.

Keluaran: `bug_stretched_bad.ppm`, `bug_stretched_fixed.ppm`, citra depth, dan `bug_stretched_evidence.json`.

## 5. Texture mapping dan mipmap

### 5.1 Perspective-correct UV

Pada edge lantai dengan kedalaman vertex `wL=1` dan `wR=9`, nilai u di tengah layar adalah:

- Screen-linear/naif: `u=0.5`.
- Perspective-correct: interpolate `u/w` dan `1/w`, kemudian bagi, sehingga `u=0.1`.

Dua gambar hasil render disimpan oleh `uv_demo.py`; pola checker memperlihatkan perbedaan distribusi pola pada permukaan segitiga.

### 5.2 Mipmap empat level

Mipmap dibuat dengan box downscale 2×2. Sebelum rata-rata, texture sRGB didekode ke linear-light; hasil rata-rata disimpan pada level berikutnya. Setiap texture map dibuat hingga empat level atau sampai ukuran minimum tercapai.

| Pengukuran frekuensi tinggi | Energi |
|---|---:|
| Tanpa mipmap | 0.094763 |
| Dengan mipmap | 0.063216 |
| Perubahan | sekitar −33.3% |

Angka tersebut merupakan ukuran sederhana rata-rata selisih intensitas antar-pixel tetangga pada area objek, bukan metrik persepsi visual standar. Render sebelum/sesudah dan citra selisih diperiksa bersama nilai ini.

Keluaran: `mipmap_without.ppm`, `mipmap_with.ppm`, `mipmap_difference_x4.ppm`, dan `mipmap_metrics.json`.

## 6. Satu perbaikan yang diterapkan dari pitfall

Renderer raster standar menggunakan z-buffer `float64` dan tidak mengkuantisasi nilai depth. Eksperimen z-fighting menunjukkan 2.852 pixel berbeda pada konfigurasi near 0.001 + depth 16-bit, sedangkan render float64 pada near 1.0 cocok dengan referensi float. Konfigurasi near/far tetap harus dipilih mengikuti skala scene agar presisi depth lebih terdistribusi pada rentang yang dibutuhkan.

## 7. Pengujian dan reproduksibilitas

Menjalankan seluruh pengujian:

```powershell
python -m pip install -r requirements.txt
python prepare_tugu.py
python tests.py
python run_lab2.py
```

Status terakhir pada lingkungan pengembangan: **12/12 automated checks passed**; semua tahapan `run_lab2.py` berhasil dengan exit code 0. Log lengkap tersimpan pada `out/lab2_run_log.txt`.

## 8. Batasan implementasi

- Ray tracer adalah implementasi referensi sederhana O(pixel × triangle), bukan BVH atau renderer real-time.
- Shading memakai flat normal per triangle dan satu directional light Lambert; belum mencakup PBR, shadow map, reflection atau global illumination.
- Alpha blending/transparent material dari MTL belum dimodelkan penuh; texture PNG dibaca sebagai RGB.
- UV repeat-wrap diterapkan ketika sampling; mipmap memilih satu level berdasarkan estimasi footprint per triangle.
- Winding OBJ sumber tidak seluruhnya konsisten sehingga back-face culling dimatikan pada render normal.

## 9. Checklist artefak Lab 2

- [x] Transformasi 4×4 dan repro E1–E3.
- [x] Near clipping, perspective divide, viewport, rasterisasi barycentric dan z-buffer.
- [x] Sampling bilinear dan UV perspective-correct.
- [x] Renderer Tugu Pahlawan dan perbandingan PSNR/SSIM dengan ray tracer.
- [x] Diagnosis inside-out, z-fighting, dan stretched dengan render sebelum/sesudah.
- [x] Histogram depth untuk kasus z-fighting.
- [x] Demonstrasi UV naif vs perspective-correct.
- [x] Mipmap empat level, render sebelum/sesudah, dan angka frekuensi tinggi.
- [x] Perbaikan presisi depth float64 pada renderer normal.
- [x] Tes reproduksibilitas dari model Tugu Pahlawan.

## 10. Gambar bukti

| Bukti | File |
|---|---|
| Tugu Pahlawan: rasterizer dan ray tracer | `evidence/raster_vs_raytrace.png` |
| Tiga diagnosis bug sebelum/sesudah | `evidence/bug_diagnostics.png` |
| UV naif dibanding perspective-correct | `evidence/uv_perspective_demo.png` |
| Mipmap tanpa/dengan | `evidence/mipmap_comparison.png` |
| Histogram depth z-fighting | `evidence/zfight_depth_histogram.png` |
| Crop objek hasil render | `evidence/tugu_pahlawan_raster_crop.png` |
