/* Module 3 Lab 3 — Three.js real-time renderer for Tugu Pahlawan.
 * The default camera, model yaw, light vector and projection parameters are
 * intentionally aligned with raster3d.render() in the NumPy Lab 2 pipeline.
 */
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { OBJLoader } from "three/addons/loaders/OBJLoader.js";
import { MTLLoader } from "three/addons/loaders/MTLLoader.js";

const W = 512;
const H = 512;
const MODEL_YAW_DEG = 12.0;
const CAMERA = Object.freeze({ eye: [3.4, 2.5, 4.2], target: [0.0, 0.8, 0.0], fovy: 45, near: 0.1, far: 50 });
const LIGHT_DIR = new THREE.Vector3(0.4, 0.9, 0.6).normalize();

const canvas = document.getElementById("c");
const status = document.getElementById("status");
const $ = (id) => document.getElementById(id);

THREE.ColorManagement.enabled = true;
const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  alpha: false,
  preserveDrawingBuffer: true,
  powerPreference: "high-performance",
});
renderer.setPixelRatio(1);
renderer.setSize(W, H, false);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.NoToneMapping;
renderer.setClearColor(0x000000, 1);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x000000);
const camera = new THREE.PerspectiveCamera(CAMERA.fovy, W / H, CAMERA.near, CAMERA.far);
camera.position.fromArray(CAMERA.eye);

const controls = new OrbitControls(camera, canvas);
controls.target.fromArray(CAMERA.target);
controls.enableDamping = true;
controls.dampingFactor = 0.06;
controls.update();
controls.saveState(); // ensure Reset camera restores the matched NumPy target too

// Lambert weights mirror the NumPy baseline: ambient=0.15, direct=0.85.
scene.add(new THREE.AmbientLight(0xffffff, 0.15));
const sun = new THREE.DirectionalLight(0xffffff, 0.85);
sun.position.copy(LIGHT_DIR).multiplyScalar(5.0);
sun.target.position.set(0, 0, 0);
sun.castShadow = true;
sun.shadow.mapSize.set(1024, 1024);
sun.shadow.camera.left = -2.5;
sun.shadow.camera.right = 2.5;
sun.shadow.camera.top = 2.5;
sun.shadow.camera.bottom = -2.5;
sun.shadow.camera.near = 0.1;
sun.shadow.camera.far = 10;
sun.shadow.bias = -0.00025;
sun.shadow.normalBias = 0.015;
scene.add(sun, sun.target);

const grid = new THREE.GridHelper(5, 20, 0x667085, 0x344054);
grid.position.y = 0.001;
grid.visible = false;
scene.add(grid);

// Optional receiving floor is kept hidden in the reference frame so the
// NumPy/WebGL comparison contains the same model-only pixels/background.
const floorMaterial = new THREE.MeshLambertMaterial({ color: 0x3b4655, side: THREE.DoubleSide });
const floor = new THREE.Mesh(new THREE.PlaneGeometry(6, 6), floorMaterial);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -0.008;
floor.receiveShadow = true;
floor.visible = false;
scene.add(floor);

let model = null;
let wireframe = false;
let shadowMode = false;
let gridMode = false;
let lastBenchmark = null;

function makeLambertMaterial(source) {
  const material = new THREE.MeshLambertMaterial({
    name: source.name,
    color: source.color ? source.color.clone() : new THREE.Color(0xffffff),
    map: source.map || null,
    alphaMap: source.alphaMap || null,
    transparent: source.transparent || false,
    opacity: source.opacity ?? 1,
    side: THREE.DoubleSide,
    flatShading: true,
    wireframe: false,
  });
  if (material.map) {
    material.map.colorSpace = THREE.SRGBColorSpace;
    material.map.wrapS = THREE.RepeatWrapping;
    material.map.wrapT = THREE.RepeatWrapping;
    // Keep anisotropy at 1 for a closer comparison with NumPy bilinear sampling.
    material.map.anisotropy = 1;
    material.map.magFilter = THREE.LinearFilter;
    material.map.minFilter = THREE.LinearMipmapLinearFilter;
    material.map.generateMipmaps = true;
    material.map.needsUpdate = true;
  }
  return material;
}

async function loadTuguPahlawan() {
  const assetPath = "./assets/";
  const mtlLoader = new MTLLoader();
  mtlLoader.setPath(assetPath);
  mtlLoader.setResourcePath(assetPath);
  const materials = await mtlLoader.loadAsync("mymodel.mtl");
  materials.preload();

  // MTLLoader defaults to Phong; Lab 2 uses diffuse Lambert shading. Convert
  // materials while retaining their Kd colors and sRGB diffuse texture maps.
  for (const [name, source] of Object.entries(materials.materials)) {
    materials.materials[name] = makeLambertMaterial(source);
  }

  const objLoader = new OBJLoader();
  objLoader.setMaterials(materials);
  objLoader.setPath(assetPath);
  const obj = await objLoader.loadAsync("mymodel.obj");
  obj.rotation.y = THREE.MathUtils.degToRad(MODEL_YAW_DEG);
  obj.position.set(0, 0, 0);
  obj.traverse((child) => {
    if (!child.isMesh) return;
    child.castShadow = true;
    child.receiveShadow = true;
    child.frustumCulled = true;
    const materialsArray = Array.isArray(child.material) ? child.material : [child.material];
    for (const material of materialsArray) {
      material.side = THREE.DoubleSide;
      material.flatShading = true;
      material.needsUpdate = true;
    }
  });
  scene.add(obj);
  model = obj;

  let vertices = 0;
  let triangles = 0;
  const seenMaterials = new Set();
  obj.traverse((child) => {
    if (!child.isMesh) return;
    const geometry = child.geometry;
    vertices += geometry.attributes.position?.count || 0;
    const indexCount = geometry.index ? geometry.index.count : (geometry.attributes.position?.count || 0);
    triangles += Math.floor(indexCount / 3);
    for (const m of (Array.isArray(child.material) ? child.material : [child.material])) seenMaterials.add(m.name);
  });
  $("modelState").textContent = "Loaded";
  $("vertexCount").textContent = vertices.toLocaleString("id-ID");
  $("triangleCount").textContent = triangles.toLocaleString("id-ID");
  $("materialCount").textContent = seenMaterials.size.toString();
  status.textContent = "Model berhasil dimuat: Tugu Pahlawan (OBJ + MTL + 10 diffuse texture maps).";
  renderer.render(scene, camera);
  $("drawCalls").textContent = renderer.info.render.calls.toString();
}

function renderFrame() {
  controls.update();
  renderer.render(scene, camera);
  $("drawCalls").textContent = renderer.info.render.calls.toString();
}

loadTuguPahlawan().catch((error) => {
  console.error(error);
  $("modelState").textContent = "Error";
  status.textContent = `Gagal memuat model: ${error.message}. Pastikan server dijalankan dari folder proyek dan web/assets/ berisi OBJ, MTL, serta PNG.`;
});

function animate() {
  requestAnimationFrame(animate);
  renderFrame();
}
animate();

$("wire").addEventListener("click", () => {
  if (!model) return;
  wireframe = !wireframe;
  model.traverse((child) => {
    if (!child.isMesh) return;
    const list = Array.isArray(child.material) ? child.material : [child.material];
    for (const material of list) material.wireframe = wireframe;
  });
  renderFrame();
});

$("grid").addEventListener("click", () => {
  gridMode = !gridMode;
  grid.visible = gridMode;
  renderFrame();
});

$("shadows").addEventListener("click", () => {
  shadowMode = !shadowMode;
  floor.visible = shadowMode;
  renderer.shadowMap.enabled = shadowMode;
  renderFrame();
});

$("reset").addEventListener("click", () => {
  camera.position.fromArray(CAMERA.eye);
  camera.fov = CAMERA.fovy;
  camera.near = CAMERA.near;
  camera.far = CAMERA.far;
  camera.updateProjectionMatrix();
  controls.target.fromArray(CAMERA.target);
  controls.reset();
  controls.update();
  renderFrame();
});

$("export").addEventListener("click", () => {
  if (!model) return;
  // Export at fixed 512x512 and pixel ratio 1. The OrbitControls camera is
  // captured as currently displayed; reset first for the NumPy comparison.
  renderer.render(scene, camera);
  const gl = renderer.getContext();
  const pixels = new Uint8Array(W * H * 4);
  gl.readPixels(0, 0, W, H, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
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
  const objectUrl = URL.createObjectURL(new Blob([header, body], { type: "image/x-portable-pixmap" }));
  link.href = objectUrl;
  link.download = "mymodel_three.ppm";
  link.click();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1500);
  status.textContent = "Frame WebGL 512×512 diekspor sebagai mymodel_three.ppm.";
});

$("benchmark").addEventListener("click", async () => {
  if (!model) return;
  const button = $("benchmark");
  button.disabled = true;
  button.textContent = "Mengukur…";
  try {
    const gl = renderer.getContext();
    const warmup = 20;
    const samples = 120;
    for (let i = 0; i < warmup; i++) renderer.render(scene, camera);
    gl.finish();
    const start = performance.now();
    for (let i = 0; i < samples; i++) renderer.render(scene, camera);
    gl.finish();
    const elapsed = performance.now() - start;
    const meanMs = elapsed / samples;
    lastBenchmark = {
      renderer: "Three.js WebGL",
      threeRevision: THREE.REVISION,
      width: W,
      height: H,
      pixelRatio: 1,
      warmupFrames: warmup,
      measuredFrames: samples,
      totalMilliseconds: Number(elapsed.toFixed(3)),
      meanFrameMilliseconds: Number(meanMs.toFixed(4)),
      approximateFps: Number((1000 / meanMs).toFixed(2)),
      drawCalls: renderer.info.render.calls,
      triangles: renderer.info.render.triangles,
      userAgent: navigator.userAgent,
      note: "performance.now() around renderer.render() with gl.finish() before and after; CPU submit + completion wall time on this browser/GPU.",
    };
    $("frameMs").textContent = `${meanMs.toFixed(3)} ms`;
    $("fps").textContent = `${(1000 / meanMs).toFixed(1)} FPS`;
    $("sampleCount").textContent = samples.toString();
    const a = document.createElement("a");
    const url = URL.createObjectURL(new Blob([JSON.stringify(lastBenchmark, null, 2)], { type: "application/json" }));
    a.href = url;
    a.download = "webgl_benchmark.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
    status.textContent = "Benchmark WebGL selesai; webgl_benchmark.json diunduh.";
  } catch (error) {
    console.error(error);
    status.textContent = `Benchmark gagal: ${error.message}`;
  } finally {
    button.disabled = false;
    button.textContent = "Ukur frame time";
  }
});
