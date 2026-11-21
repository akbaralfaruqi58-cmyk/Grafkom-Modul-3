# Hasil WebGL Lab 3

- Resolusi: 512 × 512
- PSNR NumPy vs WebGL: 16.75 dB
- SSIM global: 0.4131
- Mean absolute difference: 23.391
- Maximum absolute difference: 206
- WebGL mean frame: 0.2675 ms
- Perkiraan FPS: 3738.32

Residual visual perlu dibaca bersama citra selisih: tepi (raster coverage/anti-aliasing), filter mipmap, normal, serta perbedaan model shading dapat menimbulkan residual; pergeseran besar di bagian dalam objek biasanya menandakan kamera, transformasi, atau UV belum cocok.
