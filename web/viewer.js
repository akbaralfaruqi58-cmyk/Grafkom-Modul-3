/* Module 3 Lab 1 - textured Tugu Pahlawan model viewer.
 * The OBJ was normalized to Y-up by prepare_tugu.py. The visible model
 * transform matches lab1_analysis.py: M = T(0.15, 0, -0.10) * Ry(35deg).
 */
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { OBJLoader } from "three/addons/loaders/OBJLoader.js";
import { MTLLoader } from "three/addons/loaders/MTLLoader.js";

const W = 512;
const H = 512;
const canvas = document.getElementById("c");
const status = document.getElementById("status");

const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  preserveDrawingBuffer: true,
});
renderer.setPixelRatio(1);
renderer.setSize(W, H, false);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.setClearColor(0x111827, 1);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x111827);

const camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 50.0);
camera.position.set(3.2, 2.5, 4.0);

const controls = new OrbitControls(camera, canvas);
controls.target.set(0.0, 0.9, 0.0);
controls.enableDamping = true;
controls.dampingFactor = 0.06;
controls.update();

scene.add(new THREE.AmbientLight(0xffffff, 0.65));
const sun = new THREE.DirectionalLight(0xffffff, 1.8);
sun.position.set(3.5, 6.0, 4.0);
scene.add(sun);

const grid = new THREE.GridHelper(5, 20, 0x667085, 0x344054);
grid.position.y = 0;
scene.add(grid);

let model = null;
let wireframe = false;

async function loadTuguPahlawan() {
  const mtlLoader = new MTLLoader();
  mtlLoader.setPath("../data/");
  const materials = await mtlLoader.loadAsync("mymodel.mtl");
  materials.preload();

  // The supplied OBJ contains tiled UVs (including values outside 0..1).
  // RepeatWrapping is therefore intentional and preserves the source mapping.
  for (const material of Object.values(materials.materials)) {
    material.side = THREE.DoubleSide;
    if (material.map) {
      material.map.colorSpace = THREE.SRGBColorSpace;
      material.map.wrapS = THREE.RepeatWrapping;
      material.map.wrapT = THREE.RepeatWrapping;
      material.map.anisotropy = renderer.capabilities.getMaxAnisotropy();
      material.map.needsUpdate = true;
    }
  }

  const objLoader = new OBJLoader();
  objLoader.setMaterials(materials);
  objLoader.setPath("../data/");
  const obj = await objLoader.loadAsync("mymodel.obj");

  // Match the model matrix used in lab1_analysis.py.
  obj.rotation.y = THREE.MathUtils.degToRad(35.0);
  obj.position.set(0.15, 0.0, -0.10);
  scene.add(obj);
  model = obj;
  status.textContent = "Model berhasil dimuat: Tugu Pahlawan (OBJ + MTL + texture).";
}

loadTuguPahlawan().catch((error) => {
  console.error(error);
  status.textContent = `Gagal memuat model: ${error.message}. Jalankan server dari folder Module3 dan periksa koneksi internet untuk Three.js CDN.`;
});

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}
animate();

document.getElementById("wire").addEventListener("click", () => {
  if (!model) return;
  wireframe = !wireframe;
  model.traverse((child) => {
    if (!child.isMesh) return;
    const mats = Array.isArray(child.material) ? child.material : [child.material];
    for (const material of mats) material.wireframe = wireframe;
  });
});

document.getElementById("reset").addEventListener("click", () => {
  camera.position.set(3.2, 2.5, 4.0);
  controls.target.set(0.0, 0.9, 0.0);
  controls.update();
});

document.getElementById("export").addEventListener("click", () => {
  renderer.render(scene, camera);
  const gl = renderer.getContext();
  const pixels = new Uint8Array(W * H * 4);
  gl.readPixels(0, 0, W, H, gl.RGBA, gl.UNSIGNED_BYTE, pixels);

  // PPM is written top-to-bottom, while WebGL readPixels starts bottom-to-top.
  const body = new Uint8Array(W * H * 3);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const src = ((H - 1 - y) * W + x) * 4;
      const dst = (y * W + x) * 3;
      body[dst] = pixels[src];
      body[dst + 1] = pixels[src + 1];
      body[dst + 2] = pixels[src + 2];
    }
  }

  const header = new TextEncoder().encode(`P6\n${W} ${H}\n255\n`);
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([header, body]));
  link.download = "mymodel_three.ppm";
  link.click();
  const exportUrl = link.href;
  setTimeout(() => URL.revokeObjectURL(exportUrl), 1000);
});
