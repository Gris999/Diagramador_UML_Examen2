/**
 * Copia un texto al portapapeles. Usa la API moderna cuando la página es segura (https o localhost) y, si no, el método antiguo
 * con un campo oculto, que funciona también en http. Devuelve `true` si se pudo copiar.
 */
export async function copyText(text: string): Promise<boolean> {
  const secure = window.location.protocol === 'https:' || window.location.hostname === 'localhost';
  if (secure && navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // El navegador la rechazó (permiso o foco): se prueba el método antiguo.
    }
  }
  return fallbackCopy(text);
}

function fallbackCopy(text: string): boolean {
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  try {
    return document.execCommand('copy');
  } catch (err) {
    console.error('Fallback copy failed', err);
    return false;
  } finally {
    document.body.removeChild(textarea);
  }
}
