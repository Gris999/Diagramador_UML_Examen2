// Capturas del manual para el acceso con el correo, «Mis diagramas» y Compartir con roles.
//
// El sitio publicado pide entrar con un correo, y una captura automática no puede recibir el código por mail, así que estas
// capturas se toman sobre una copia LOCAL con datos de ejemplo (personas ficticias @example.com), no sobre diagramador.dev:
//   1. Django con AUTH_REQUIRED=True y Angular en el puerto 4200;
//   2. un archivo JSON con las sesiones y las salas de ejemplo, que arma `sembrar_capturas_acceso.py` (personas ficticias @example.com);
//   3. node capturas_acceso.mjs <archivo-de-sesiones.json>
import puppeteer from 'puppeteer-core';
import { mkdirSync, readFileSync } from 'node:fs';

const SITIO = process.env.SITIO || 'http://localhost:4200';
const archivo = process.argv[2];
if (!archivo) throw new Error('Uso: node capturas_acceso.mjs <sesiones.json>');
const { sesiones, salas } = JSON.parse(readFileSync(archivo, 'utf-8'));
const SALIDA = new URL('./capturas/', import.meta.url).pathname;
mkdirSync(SALIDA, { recursive: true });

const esperar = (ms) => new Promise((r) => setTimeout(r, ms));
const navegador = await puppeteer.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: 'new',
  args: ['--no-sandbox'],
  defaultViewport: { width: 1440, height: 900, deviceScaleFactor: 1.5 },
  protocolTimeout: 240000,
});

/** Una persona con su propio contexto (y su sesión ya guardada en el navegador, si se da). */
async function paginaDe(persona, correo, nombre) {
  const contexto = await navegador.createBrowserContext();
  const pagina = await contexto.newPage();
  pagina.on('dialog', (d) => d.accept(nombre || ''));
  if (persona) {
    await pagina.evaluateOnNewDocument((token, email, name) => {
      localStorage.setItem('diagramador-sesion', JSON.stringify({ token, email, name }));
      localStorage.setItem('uml-collab-participant-name', name);
    }, sesiones[persona], correo, nombre);
  }
  return pagina;
}

async function foto(pagina, nombre) {
  await pagina.screenshot({ path: SALIDA + nombre });
  console.log('captura', nombre);
}

async function clicTexto(pagina, texto, selector = 'button') {
  const ok = await pagina.evaluate((t, sel) => {
    const el = [...document.querySelectorAll(sel)].find((e) => e.textContent.trim().includes(t));
    if (el) el.click();
    return !!el;
  }, texto, selector);
  if (!ok) throw new Error(`No se encontró "${texto}"`);
}

// 1. Entrar con el correo: primero el correo, después el código
const nueva = await paginaDe(null);
await nueva.goto(`${SITIO}/entrar`, { waitUntil: 'networkidle2' });
await nueva.waitForSelector('[data-testid="login-email"]');
await nueva.type('[data-testid="login-email"]', 'ana.quispe@example.com');
await foto(nueva, '14-entrar.png');
await nueva.click('[data-testid="login-send-code"]');
await nueva.waitForSelector('[data-testid="login-code"]', { timeout: 30000 });
await esperar(500);
await foto(nueva, '14b-entrar-codigo.png');

// 2. «Mis diagramas»: la lista de la persona (los suyos, a los que la invitaron y los que abrió con un enlace)
const ana = await paginaDe('ana', 'ana.quispe@example.com', 'Ana Quispe');
await ana.goto(SITIO, { waitUntil: 'networkidle2' });
await ana.waitForSelector('[data-testid="diagram-card"]', { timeout: 30000 });
await esperar(800);
await foto(ana, '15-mis-diagramas.png');

// 3. Compartir como en Google Docs: personas con rol y acceso general
await ana.goto(`${SITIO}/diagram/${salas.tienda}`, { waitUntil: 'networkidle2' });
await ana.waitForFunction(() => [...document.querySelectorAll('button')].some((b) => b.textContent.includes('Compartir')), { timeout: 60000 });
await esperar(1500);
await clicTexto(ana, 'Compartir');
await ana.waitForSelector('[data-testid="share-members"]', { timeout: 30000 });
await esperar(800);
await foto(ana, '16-compartir-roles.png');

// 4. Quien no está en la lista no entra a una sala privada
const dario = await paginaDe('dario', 'dario.pinto@example.com', 'Dario Pinto');
await dario.goto(`${SITIO}/diagram/${salas.biblioteca}`, { waitUntil: 'networkidle2' });
await dario.waitForSelector('[data-testid="access-denied"]', { timeout: 30000 });
await esperar(500);
await foto(dario, '17-sin-acceso.png');

await navegador.close();
