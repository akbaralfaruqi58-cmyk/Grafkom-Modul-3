# Catatan Praktikum Modul 3 — Lab 3
## Renderer WebGL, rasterisation vs ray-trace, pengukuran, dan publikasi

**Objek:** Monumen Tugu Pahlawan dan Museum 10 November  
**Model:** `data/mymodel.obj` + `data/mymodel.mtl` + PNG diffuse texture  
**Web viewer:** `web/index.html` + `web/viewer.js` (Three.js r160)  
**Lingkup:** instruksi Lab 3 pada halaman 25–26 Modul 3.

## 1. Renderer real-time di browser

Viewer menggunakan Three.js dengan `WebGLRenderer`, `OBJLoader`, `MTLLoader`, dan `OrbitControls`. Model dimuat dari folder `web/assets/`, sehingga seluruh aset statis berada di dalam direktori yang diterbitkan oleh `npx serve web` atau GitHub Pages.

Konfigurasi yang dipatok untuk frame perbandingan:

| Parameter | Nilai |
|---|---|
| Resolusi drawing buffer | 512 × 512 |
| `setPixelRatio` | 1 |
| Kamera | PerspectiveCamera, FOV 45° |
| Eye | (3.4, 2.5, 4.2) |
| Target | (0, 0.8, 0) |
| Near / far | 0.1 / 50.0 |
| Model | `Ry(12°)` |
| Directional light direction | (0.4, 0.9, 0.6) |
| Ambient / directional intensity | 0.15 / 0.85 |
| Output color space | sRGB |
| Tone mapping | NoToneMapping |

Material MTL yang dibaca oleh `MTLLoader` dikonversi menjadi `MeshLambertMaterial` dan memakai `flatShading` untuk mendekati shading Lambert per-face pada renderer NumPy. Diffuse maps ditandai sebagai sRGB. Filter tekstur WebGL memakai linear magnification dan trilinear mipmap minification. Model dapat di-orbit, di-zoom, ditampilkan wireframe, serta diekspor menjadi PPM 512×512.

Tombol **Bayangan** mengaktifkan shadow map directional-light Three.js dan lantai penerima bayangan. Lantai dan grid dimatikan pada mode referensi sehingga frame ekspor default tetap berisi model dan latar hitam, seperti frame NumPy.

## 2. Prediksi sebelum pengukuran

Prediksi awal: pada resolusi dan model yang sama, rasterizer diperkirakan lebih cepat daripada ray tracer sederhana. Rasterizer mengunjungi triangle lalu menguji pixel pada bounding box-nya; ray tracer sederhana menguji ray pixel terhadap ribuan triangle. Tanpa BVH atau akselerasi khusus, biaya ray tracing meningkat tajam saat resolusi dan jumlah segitiga bertambah.

Untuk kualitas visual, pipeline ini tidak memberi ray tracer keunggulan refleksi otomatis: ray tracer yang ada baru memakai primary pinhole ray dan Möller–Trumbore dengan satu directional light Lambert. Ia belum melakukan secondary reflection, global illumination, atau recursive ray bounce. Three.js memiliki shadow-map GPU pada tombol Bayangan. Karena fitur refleksi belum dibuat pada kedua implementasi, kualitas reflection tidak diklaim telah diukur.

## 3. Pengukuran frame-time Python

Skrip `lab3_benchmark.py` mengukur pemanggilan fungsi render setelah satu warm-up. Model dan texture sudah dimuat sebelum timer dimulai. Resolusi dan konfigurasi kamera sama, bayangan dimatikan, dan pengukuran menggunakan median dari tiga pengulangan.

**Hasil lingkungan saat penyiapan artefak** (bukan hasil laptop mahasiswa):

| Renderer | Median frame time | Perkiraan FPS |
|---|---:|---:|
| NumPy rasterizer, 128×128 | 758.6046 ms | 1.32 |
| NumPy ray tracer, 128×128 | 2,585.3003 ms | 0.39 |

Rasio waktu ray tracer/rasterizer adalah **3.408×** pada lingkungan pengukuran tersebut. Angka ini tidak boleh dianggap sebagai benchmark laptop. Jalankan `python lab3_benchmark.py --size 128 --repeats 3` pada laptop untuk merekam hasil perangkat sendiri ke `out/lab3_python_benchmark.json`.

Skrip `lab3_capture.py` juga menghasilkan frame NumPy referensi 512×512 (`out/tugu_raster_512.ppm`) dengan kamera dan model transform yang sama dengan viewer. Render 512×512 pada lingkungan penyiapan memerlukan 917.93 ms untuk rasterizer saja; ini bukan angka WebGL.

### Benchmark WebGL

Di viewer, klik **Ukur frame time**. Kode menjalankan 20 frame warm-up, lalu mengukur 120 pemanggilan `renderer.render()` dengan `performance.now()` dan `gl.finish()` sebelum/sesudah rangkaian. File `webgl_benchmark.json` akan diunduh otomatis. Nilai tersebut adalah wall-time submit + penyelesaian GPU secara sinkron pada browser/GPU yang menjalankan pengujian; bandingkan hanya dengan catatan metode ini, bukan dengan FPS teoretis browser lain.

Simpan file hasil unduhan sebagai `out/webgl_benchmark.json` agar dapat digabungkan dengan hasil perbandingan.

## 4. Rasterisation vs ray tracing

### Baseline NumPy

`lab3_capture.py` menghasilkan `out/tugu_raster_512.ppm`. Frame tersebut adalah baseline yang harus dibandingkan dengan `web/mymodel_three.ppm` dari tombol ekspor viewer.

1. Jalankan viewer dan klik **Reset kamera acuan**.
2. Pastikan Grid dan Bayangan mati serta kamera tidak digeser.
3. Klik **Ekspor PPM 512 × 512**.
4. Pindahkan file yang diunduh ke `web/mymodel_three.ppm`.
5. Jalankan:

```powershell
python compare.py out/tugu_raster_512.ppm web/mymodel_three.ppm --diff docs/evidence/lab3_webgl_numpy_difference_x6.ppm --scale 6
```

PSNR, SSIM global, mean/max absolute difference, dan citra selisih akan dihasilkan. Jangan mengharapkan byte-identical: raster coverage/anti-aliasing, mipmap/texture filtering, interpolasi normal, serta detail model shading WebGL dapat menghasilkan residual tepi atau material. Pergeseran luas di bagian dalam objek lebih mengarah pada kamera, model transform, UV, atau axis convention yang tidak cocok.

Untuk menyimpan hasil browser dan membuat ringkasan Markdown setelah benchmark WebGL, simpan JSON unduhan sebagai `out/webgl_benchmark.json`, kemudian jalankan:

```powershell
python collect_lab3_results.py --web-frame web/mymodel_three.ppm --web-benchmark out/webgl_benchmark.json
```

Hasilnya ditulis ke `out/lab3_browser_results.json` dan `docs/Lab3_WebGL_Hasil.md`.

### Hard shadow

Kedua renderer NumPy sekarang mempunyai opsi `hard_shadows=True` / `--hard-shadows`. Untuk menjaga biaya tetap terkendali, metode NumPy memeriksa visibility sinar directional-light dari centroid setiap triangle dan memberi satu faktor terang/gelap untuk satu face penuh. Ini adalah hard-shadow flat-face approximation, bukan shadow map per-fragment.

Perbandingan hasil metode tersebut:

- `out/tugu_no_shadow_96.ppm`
- `out/tugu_hard_shadow_raster_96.ppm`
- `out/tugu_hard_shadow_ray_96.ppm`
- `docs/evidence/lab3_hard_shadow_comparison.png`

Rasterizer dan ray tracer menggunakan visibility per-face yang sama; hasil dua frame shadow pada pengujian ini identik (PSNR ∞ dB, SSIM 1.000). Pada resolusi demo 96×96, shadow approximation mengubah 23 pixel dibanding gambar tanpa shadow; ini demonstrasi algoritme, bukan bukti kualitas shadow-map produksi. Karena shadow visibility konstan per-face, batas bayangan mengikuti batas triangle dan dapat tampak kasar. Viewer Three.js juga menyediakan shadow map directional-light yang lebih sesuai untuk real-time rendering.

## 5. Keputusan renderer

- **Viewer real-time: Three.js/WebGL rasterisation.** Model dapat di-orbit dan di-zoom dalam browser. Pipeline fixed-function GPU menangani pemrosesan vertex, rasterisasi, texture filtering, dan depth test; rasterisasi adalah pilihan praktis untuk interaksi real-time.
- **Beauty shot: ray tracing hanya menjadi pilihan setelah dikembangkan lebih lanjut.** Secara prinsip secondary rays dapat menangani pantulan dan global illumination, tetapi kode ray tracer modul saat ini belum memiliki fitur tersebut. Untuk hasil yang benar-benar dihasilkan oleh implementasi saat ini, WebGL dengan shadow-map lebih lengkap daripada ray tracer primary-ray ini. Karena itu keputusan beauty-shot saat ini bersifat target pengembangan, bukan klaim kualitas yang telah terukur.

Pilihan dapat berbalik pada kondisi konkret berikut:

1. Mesh menjadi sangat besar (misalnya ratusan ribu triangle) dan ray tracer tidak memakai BVH: biaya per-ray naik, sehingga rasterisasi GPU semakin menguntungkan. Dengan BVH/RT-core, perbandingan dapat berubah.
2. Kebutuhan refleksi glossy, pantulan multi-bounce, atau global illumination menjadi dominan: ray/path tracing dengan secondary rays dapat lebih sesuai daripada renderer raster dasar yang hanya memakai shadow map.
3. Target interaksi 60 FPS pada perangkat kelas bawah: rasterisasi biasanya lebih mudah memenuhi batas frame-time dibanding ray tracer CPU sederhana.
4. Render offline tanpa batas waktu ketat, dengan perangkat ray-tracing yang memadai: path tracing dapat dipilih untuk mengurangi kompromi visual pada refleksi dan pencahayaan tidak langsung.

## 6. Reproduksi bersih

Dari clone bersih di Windows PowerShell, jalankan:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python make_model.py
python tests.py
npx serve web
```

Buka URL yang dicetak oleh `serve` (umumnya `http://localhost:3000`). Alternatif tanpa paket `serve`: dari root proyek jalankan `python -m http.server 8000`, kemudian buka `http://localhost:8000/web/`.

`python make_model.py` menyiapkan OBJ Tugu dan menyalin OBJ, MTL, serta diffuse PNG ke `web/assets/`. Candi Pusaka3D dari starter asli tetap tersedia sebagai fallback melalui `python make_model.py --fallback-temple`.

## 7. Publikasi GitHub Pages

Workflow `.github/workflows/deploy-pages.yml` menerbitkan isi folder `web/` secara otomatis pada push ke branch `m3-work` (dan menyediakan `workflow_dispatch`). Sebelum deploy pertama:

1. Commit dan push Lab 3 ke branch default repo.
2. Buka **Repository → Settings → Pages**.
3. Pada **Build and deployment → Source**, pilih **GitHub Actions**.
4. Buka tab **Actions** dan periksa workflow deploy sampai berhasil.
5. URL project site umumnya `https://USERNAME.github.io/NAMA-REPOSITORY/`.

Workflow saat ini dipicu oleh branch kerja `m3-work`. Jika kamu memakai branch lain, ubah daftar branch pada workflow sebelum commit. GitHub mendokumentasikan alur custom workflow memakai checkout, upload artifact halaman, lalu deploy artifact. Referensi: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site dan https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages.

URL live belum dapat dicantumkan di laporan sampai workflow dijalankan pada repository GitHub mahasiswa. Jangan mengarang URL deployment.

## 8. Batasan

- Viewer mengambil Three.js r160 dari jsDelivr CDN, sehingga halaman perlu koneksi internet saat memuat modul Three.js; model, MTL, dan PNG dibundel lokal.
- Pengukuran Python pada dokumen ini berasal dari lingkungan penyiapan, bukan laptop mahasiswa. Hasil perangkat sendiri dibuat oleh `lab3_benchmark.py`.
- Frame WebGL belum dibandingkan sampai file PPM 512×512 diekspor dari browser; nilai PSNR/SSIM WebGL harus diisi dari `collect_lab3_results.py`, bukan ditebak.
- NumPy hard shadow merupakan centroid-per-triangle approximation. WebGL shadow map adalah implementasi real-time yang terpisah.
- Belum ada recursive reflection, global illumination, soft shadow, PBR penuh, atau BVH pada ray tracer.

## 9. Checklist Lab 3

- [x] Three.js/WebGL renderer dan OrbitControls.
- [x] OBJ + MTL + texture Tugu Pahlawan dibundel di dalam folder web.
- [x] Kamera dan transform default disejajarkan dengan NumPy.
- [x] Ukuran drawing buffer 512×512, pixel ratio 1, output sRGB.
- [x] Tombol ekspor PPM 512×512.
- [x] Tombol benchmark frame time WebGL.
- [x] Benchmark waktu Python rasterizer vs ray tracer.
- [x] Opsi hard shadow pada dua renderer NumPy dan shadow map pada WebGL.
- [x] Workflow GitHub Pages siap.
- [ ] Ekspor PPM WebGL dari browser dan isi metrik PSNR/SSIM.
- [ ] Deploy GitHub Pages dan catat URL live.
- [ ] Reproduksi penuh pada laptop/clone bersih dan catat baris `Verified`.
