// Toma las capturas del manual de usuario sobre el sitio real (https://diagramador.dev).
// Crea una sala de prueba nueva y no toca ninguna otra. Uso: node capturas.mjs
import puppeteer from 'puppeteer-core';
import { mkdirSync } from 'node:fs';

const SITIO = process.env.SITIO || 'https://diagramador.dev';
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

async function paginaCon(nombre) {
  // Cada persona usa su propio contexto: así no comparten la identidad guardada en el navegador.
  const contexto = await navegador.createBrowserContext();
  const pagina = await contexto.newPage();
  // El nombre visible se pregunta con window.prompt: se responde sin intervención.
  pagina.on('dialog', async (d) => (d.type() === 'prompt' ? d.accept(nombre) : d.accept()));
  return pagina;
}

async function clicTexto(pagina, texto, selector = 'button') {
  const ok = await pagina.evaluate((t, sel) => {
    const el = [...document.querySelectorAll(sel)].find((e) => e.textContent.trim().includes(t));
    if (el) el.click();
    return !!el;
  }, texto, selector);
  if (!ok) throw new Error(`No se encontró "${texto}"`);
}

async function foto(pagina, archivo, opciones = {}) {
  await pagina.screenshot({ path: SALIDA + archivo, ...opciones });
  console.log('captura', archivo);
}

// 1. Inicio
const ana = await paginaCon('Ana');
await ana.goto(SITIO, { waitUntil: 'networkidle2' });
await foto(ana, '01-inicio.png');

// 1b. Código de sala que no es válido: se explica y no se entra
await ana.type('input[placeholder="Ingresa el código del lienzo"]', 'mi-sala');
await clicTexto(ana, 'Unirse al Lienzo');
await esperar(800);
await foto(ana, '11-codigo-invalido.png');
await ana.evaluate(() => { const i = document.querySelector('input[placeholder="Ingresa el código del lienzo"]'); i.value = ''; i.dispatchEvent(new Event('input')); });

// 1c. Asistente de ayuda desde la página principal
await clicTexto(ana, 'Ayuda');
await ana.waitForSelector('[data-testid="help-input"]');
await ana.type('[data-testid="help-input"]', '¿Cómo invito a un compañero a mi sala y cómo la sigo desde el celular?');
await ana.click('[data-testid="help-send"]');
await ana.waitForFunction(() => document.querySelectorAll('[data-testid="help-message"]').length >= 2, { timeout: 120000, polling: 1000 }).catch(() => {});
await esperar(1500);
await foto(ana, '10-ayuda.png');
await ana.click('[data-testid="help-close"]');

// 2. Crear la sala y generar un modelo desde texto
await clicTexto(ana, 'Crear Nuevo Lienzo');
await ana.waitForSelector('textarea', { timeout: 60000 });
await esperar(3000);
const sala = new URL(ana.url()).pathname.split('/').filter(Boolean).pop();
console.log('sala de prueba:', sala);
await ana.type('textarea', 'Crea un sistema de biblioteca con las clases Libro (isbn: string, titulo: string), Autor (id: int, nombre: string) y Prestamo (id: int, fecha: Date), y relaciona Autor con Libro y Libro con Prestamo');
await foto(ana, '02-generar-modelo.png');
await clicTexto(ana, 'Generar');
// La IA tarda unos segundos: se espera a que el lienzo muestre las clases.
await ana.waitForFunction(() => document.querySelectorAll('svg g[model-id]').length >= 3, { timeout: 180000, polling: 1000 });
await ana.waitForFunction(() => !document.body.innerText.includes('Cargando...'), { timeout: 60000, polling: 1000 }).catch(() => {});
await esperar(2000);
await foto(ana, '03-editor.png');

// 3. Una segunda persona entra con el código de la sala
const bruno = await paginaCon('Bruno');
await bruno.goto(`${SITIO}/diagram/${sala}`, { waitUntil: 'networkidle2' });
await ana.waitForFunction(() => document.body.innerText.includes('Participantes (2)'), { timeout: 60000, polling: 1000 }).catch(() => {});
await esperar(2000);
await foto(ana, '04-colaboracion.png');

// 4. Chat con la IA: preguntar (la pestaña de Ana vuelve al frente: en segundo plano no responde)
await ana.bringToFront();
await ana.click('[data-testid="ia-chat-toggle"]');
await esperar(1500);
await foto(ana, '05-chat-ia-abierto.png');
await ana.type('[data-testid="ia-chat-input"]', '¿Qué clases hay en el diagrama y qué hizo Ana hasta ahora?');
await ana.click('[data-testid="ia-chat-send"]');
await ana.waitForSelector('[data-testid="ia-chat-message"] ~ [data-testid="ia-chat-message"]', { timeout: 90000 }).catch(() => {});
await esperar(4000);
await foto(ana, '06-chat-ia-respuesta.png');

// 5. Revisión con ideas aplicables
await ana.click('[data-testid="ia-mode-review"]');
await esperar(800);
await ana.waitForFunction(() => !document.querySelector('[data-testid="ia-chat-send"]').disabled, { timeout: 60000, polling: 500 });
await ana.evaluate(() => document.querySelector('[data-testid="ia-chat-send"]').click());
await ana.waitForFunction(() => document.body.innerText.includes('revisó el diagrama'), { timeout: 150000, polling: 1000 });
await esperar(2500);
await foto(ana, '07-revision-ideas.png');

// 6. Menú de exportaciones y de importaciones
await clicTexto(ana, 'Exportaciones').catch(() => {});
await esperar(800);
await foto(ana, '08-exportaciones.png');

// 7. Vista móvil de seguimiento
await ana.bringToFront();
const celular = await navegador.newPage();
await celular.setViewport({ width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
await celular.goto(`${SITIO}/sala/${sala}/seguir`, { waitUntil: 'networkidle2' });
await esperar(6000);
await foto(celular, '09-vista-movil.png');

await navegador.close();
console.log('listo');
