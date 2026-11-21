# Modul 3 — Lab 1: Model Tugu Pahlawan, Transformasi, dan Refleksi

**Objek:** Monumen Tugu Pahlawan dan Museum 10 November, Surabaya  
**Sumber model:** OBJ, MTL, texture PNG, dan GLB yang disediakan untuk praktikum.  
**Status lisensi aset:** informasi lisensi tidak tercantum pada file yang diterima; periksa dan tuliskan lisensi dari sumber asal sebelum memublikasikan repository.

## 1. Toolchain

Isi bagian ini setelah menjalankan proyek di laptop. Jangan menyalin versi dari komputer lain.

| Komponen | Versi / informasi |
|---|---|
| Sistem operasi | `____________________________` |
| Python | hasil `python --version` |
| NumPy | hasil `python -c "import numpy; print(numpy.__version__)"` |
| Node.js | hasil `node --version` |
| Browser | nama dan versi browser yang digunakan |
| Three.js | r160.0 (diimpor dari CDN dalam `web/index.html`) |
| Tanggal pengujian | `____________________________` |

## 2. Model bangunan pilihan

Model yang digunakan adalah Monumen Tugu Pahlawan dan Museum 10 November. File OBJ yang disediakan memiliki **5.637 vertex, 5.637 koordinat UV, 5.637 normal, dan 4.227 face segitiga**. OBJ juga memuat 52 object section, 52 pernyataan `usemtl`, dan 15 nama material berbeda. Seluruh face menggunakan referensi UV; hal ini diverifikasi melalui loader dan pengujian Lab 1. Jumlah 4.227 segitiga sudah melewati syarat minimal 200 segitiga pada modul.

### Penyesuaian koordinat model

Dari bounding box OBJ sumber, rentang koordinat terpanjang berada pada sumbu Z (sekitar 1,680 satuan), sementara rentang Y hanya sekitar 0,425 satuan. Karena itu, model sumber diperlakukan sebagai model Z-up. `prepare_tugu.py` mengubah basis sumbu menjadi Y-up dengan pemetaan `(x, y, z) → (x, z, -y)`, kemudian memusatkan footprint pada X/Z, meletakkan alas pada Y=0, dan menormalkan tinggi model menjadi 2 satuan dunia.

Ukuran hasil normalisasi:

| Sumbu | Minimum | Maksimum | Rentang |
|---|---:|---:|---:|
| X | -0,790906 | 0,790906 | 1,581812 |
| Y | 0,000000 | 2,000000 | 2,000000 |
| Z | -0,253088 | 0,253088 | 0,506177 |

File sumber mentah disimpan di `data/source/`. File yang digunakan oleh pipeline adalah `data/mymodel.obj`, `data/mymodel.mtl`, serta texture PNG di folder `data/`. Data UV asli tidak dihapus atau diubah. Rentang UV sumber berada di luar 0–1 pada beberapa material, sehingga viewer memakai `RepeatWrapping` agar tekstur berulang sesuai nilai UV tersebut.

## 3. Konvensi transformasi

Kode mengikuti konvensi yang dipatok starter Modul 3:

- vektor kolom dan pre-multiplication: `p' = M @ p`;
- komposisi dibaca dari kanan ke kiri;
- sistem right-handed dan kamera menghadap sumbu `-Z`;
- NDC OpenGL berada pada rentang `[-1, 1]`;
- viewport membalik sumbu Y untuk koordinat layar.

Model matrix yang dipakai untuk penelusuran:

\[
M = T(0.15,0,-0.10)\,R_y(35^\circ)\,S(1,1,1)
\]

\[
M = \begin{bmatrix}
0.819152 & 0 & 0.573576 & 0.15\\
0 & 1 & 0 & 0\\
-0.573576 & 0 & 0.819152 & -0.10\\
0 & 0 & 0 & 1
\end{bmatrix}
\]

Kolom-kolom M menunjukkan bahwa sumbu +X model mengarah ke `(0.819152, 0, -0.573576)` di world; +Y tetap `(0,1,0)`; +Z mengarah ke `(0.573576,0,0.819152)`; dan origin berpindah ke `(0.15,0,-0.10)`. Determinan bagian rotasi/skala model adalah positif (`det(M₃×₃)=1`), jadi transformasi ini tidak membalik orientasi.

Matriks view dibangun dari kamera di `(3.2, 2.5, 4.0)` yang melihat target `(0, 0.9, 0)`. Nilai matriks dan penelusuran kolom V serta V@M dicetak oleh `lab1_analysis.py` pada `out/lab1_vertex_trace.txt`.

## 4. Telusuran satu vertex melalui enam coordinate space

Vertex nyata yang dipilih adalah vertex OBJ nomor **5213** (indeks 1-based), salah satu vertex pada titik tertinggi model.

| Tahap | Nilai hasil |
|---|---|
| Object | `(0.348566, 2.000000, 0.250113, 1)` |
| World = M × Object | `(0.578988, 2.000000, -0.095049, 1)` |
| View = V × World | `(0.511490, 0.964267, -4.764210, 1)` |
| Clip = P × View | `(1.234846, 2.327945, 4.582904, 4.764210)` |
| NDC = Clip.xyz / Clip.w | `(0.259192, 0.488632, 0.961944)` |
| Screen, viewport 512×512 | `(322.353196, 130.910218)` pixel; NDC depth `0.961944` |
| Depth yang dipetakan ke [0,1] | `0.980972` |

### Perhitungan dua langkah pertama

Ambil `p = (0.348566, 2.000000, 0.250113, 1)`. Dengan `cos 35° = 0.819152` dan `sin 35° = 0.573576`, model matrix memberikan:

\[
x_w = 0.819152(0.348566)+0.573576(0.250113)+0.15 = 0.578988
\]

\[
y_w = 1(2.000000)=2.000000
\]

\[
z_w = -0.573576(0.348566)+0.819152(0.250113)-0.10=-0.095049
\]

Jadi `M p = (0.578988, 2.000000, -0.095049, 1)`. Mengalikan hasil tersebut dengan view matrix kamera menghasilkan `(0.511490, 0.964267, -4.764210, 1)`. Perhitungan selanjutnya dilakukan oleh `lab1_analysis.py`, mengikuti urutan V, P, perspective divide, dan viewport.

## 5. Membaca pipeline pada Three.js

Perbedaan yang terlihat dibanding `transforms.py` adalah level abstraksinya. Pada kode NumPy, matriks M, V, P, perspective divide, dan viewport dipanggil secara eksplisit sehingga setiap nilai intermediate dapat dicetak dan diaudit. Di Three.js, objek ditambahkan ke scene, kamera menyediakan proyeksi, lalu `WebGLRenderer` mengirim pekerjaan rendering ke WebGL 2; clipping, rasterisasi, depth test, dan interpolasi dikerjakan oleh pipeline GPU. Untuk file OBJ ber-material, alur Three.js juga memisahkan pembacaan geometri melalui `OBJLoader` dan pembacaan material/texture melalui `MTLLoader`.

Rujukan yang dibaca:

1. Three.js, **WebGLRenderer** — dokumentasi API menyatakan renderer menggunakan WebGL 2, mempunyai coordinate-system WebGL, serta pilihan output color space: <https://threejs.org/docs/pages/WebGLRenderer.html>.
2. Three.js Manual, **Loading a .OBJ File** — menjelaskan pemuatan OBJ, pencocokan material berdasarkan nama, dan penggunaan MTLLoader sebelum OBJLoader: <https://threejs.org/manual/pages/load-obj.html>.

## 6. Refleksi insiden: presisi depth dan handedness

### 6.1 Presisi depth untuk near/far proyek ini

Kamera proyek menggunakan `near = 0.1` dan `far = 50`. Dengan pemetaan perspektif standar ke depth buffer `[0,1]`, depth pada jarak `z` (positif sebagai jarak dari kamera) adalah:

\[
d(z)=\frac{f}{f-n}\left(1-\frac{n}{z}\right)
\]

Pada jarak 1 satuan:

\[
d(1)=\frac{50}{50-0.1}(1-0.1)=0.901804
\]

Artinya sekitar **90,18% rentang nilai depth** sudah terpakai antara near plane 0,1 dan jarak 1 satuan. Rentang jarak yang tersisa dari 1 sampai 50 hanya menempati sekitar 9,82% nilai depth. Ini adalah pemetaan non-linear yang berasal dari suku `1/z`; objek yang jauh mendapat resolusi depth jauh lebih sedikit, sehingga dua permukaan berdekatan dapat memiliki nilai depth yang sama atau hampir sama dan menimbulkan z-fighting.

Reverse-Z membalik pemetaan near menjadi 1 dan far menjadi 0, memakai depth buffer floating-point, serta mengganti uji depth menjadi `GREATER`/`GEQUAL` sesuai implementasinya. Distribusi floating-point yang lebih rapat dekat nol membantu mengimbangi non-linearitas `1/z`. Catatan penting: pembalikan nilai saja tidak memberi keuntungan yang sama pada depth buffer integer uniform; manfaat besar yang dibahas sumber berasal dari kombinasi reverse-Z dan floating-point depth.

Rujukan:

- Nathan Reed, **Depth Precision Visualized**, 3 Juli 2015: <https://www.reedbeta.com/blog/depth-precision-visualized/>.
- Outerra, **Maximizing Depth Buffer Range and Precision**, 28 November 2012: <https://outerra.blogspot.com/2012/11/maximizing-depth-buffer-range-and.html>.

### 6.2 Empat konvensi OpenGL dan Direct3D

| Konvensi | OpenGL (konvensi umum pada modul) | Direct3D / DirectXMath historis |
|---|---|---|
| Handedness | Umumnya right-handed | Secara historis left-handed; DirectXMath menyediakan varian LH dan RH |
| Tata-letak dan operasi matriks | Column-major; vektor kolom, `M × p` dalam konvensi starter ini | DirectXMath: row-major, vektor baris, `p × M` |
| Rentang NDC Z | `[-1, +1]` | `[0, +1]` |
| Origin texture / texel | Konvensi koordinat texture bawah-kiri | Konvensi texel Direct3D atas-kiri |

Tabel tersebut adalah ringkasan konvensi umum, bukan larangan API yang mutlak. Microsoft menyatakan DirectXMath mendukung fungsi left-handed maupun right-handed; Direct3D modern tidak mewajibkan satu handedness. Pada HLSL, packing matriks shader juga dapat menggunakan column-major secara default. Karena itu, saat porting, operasi vektor, transpose, handedness, dan pemetaan depth harus dinyatakan eksplisit, tidak disimpulkan hanya dari nama API.

Rujukan:

- Khronos OpenGL Wiki, **Coordinate Transformations**: <https://wikis.khronos.org/opengl/Coordinate_Transformations>.
- Microsoft Learn, **Getting started (DirectXMath), Matrix convention**: <https://learn.microsoft.com/en-us/windows/win32/dxmath/pg-xnamath-getting-started>.
- Microsoft Learn, **Coordinate Systems (Direct3D 10)**: <https://learn.microsoft.com/en-us/windows/win32/direct3d10/d3d10-graphics-programming-guide-resources-coordinates>.

### 6.3 Scene uji untuk mengungkap bug

- **Presisi depth:** dua quad besar yang hampir coplanar ditempatkan jauh dari kamera. Geser salah satunya sedikit demi sedikit dan simpan citra depth; perubahan pola kedipan atau urutan permukaan menunjukkan z-fighting.
- **Handedness / urutan matriks:** gunakan model asimetris yang memiliki tulisan menghadap satu arah, panah +X, dan warna berbeda pada tiga sumbu. Render dari dua sisi dan periksa apakah tulisan tercermin atau muka depan menghilang akibat winding terbalik.

### 6.4 Satu pemeriksaan otomatis untuk handedness

Tambahkan pemeriksaan determinan pada bagian 3×3 dari model matrix dan view rotation. Untuk transformasi yang seharusnya hanya berisi rotasi dan skala positif, nilai determinan harus positif. Jika negatif, ada refleksi sumbu/handedness yang tidak disengaja. Proyek ini menjalankan pemeriksaan tersebut di `lab1_analysis.py`; hasil `det(M₃×₃)` dan `det(V₃×₃)` ditulis ke transkrip. Untuk validasi tambahan pada scene produksi, pemeriksaan determinan sebaiknya dipadukan dengan uji segitiga asimetris dan arah normal.

## 7. Cara menjalankan dan bukti

Jalankan dari folder `Module3`:

```powershell
python -m pip install -r requirements.txt
python prepare_tugu.py
python lab1_analysis.py
python tests.py
python -m http.server 8000
```

Buka `http://localhost:8000/web/` untuk melihat model, orbit kamera, toggle wireframe, dan ekspor PPM 512×512. Server dijalankan dari folder `Module3` supaya path `../data/` dapat ditemukan. Viewer mengunduh Three.js dari CDN, sehingga koneksi internet diperlukan.

Bukti hasil otomatis:

- `out/lab1_vertex_trace.txt` — matriks, kolom, dan angka setiap coordinate space;
- `out/lab1_model_info.json` — angka terstruktur untuk telusuran vertex;
- `out/lab1_vertex_trace_console.txt` — transkrip eksekusi tersimpan;
- `tests.py` — validasi transformasi E1–E5 dan syarat model Tugu Pahlawan.

**Pemeriksaan laptop yang masih harus dilakukan:** buka viewer di browser laptop, orbit model, aktifkan wireframe, dan catat versi browser serta tanggal pengujiannya pada tabel Toolchain. Hasil browser tidak boleh ditandai terverifikasi sebelum benar-benar dijalankan di laptop.
