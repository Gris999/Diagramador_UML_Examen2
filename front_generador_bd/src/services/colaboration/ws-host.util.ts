/**
 * Host del WebSocket de colaboración.
 *
 * - https (túnel o proxy de un solo origen): el host configurado en el entorno o, si está
 *   vacío, el de la propia página. Así el build no queda atado a una URL que puede cambiar
 *   (p. ej. un Quick Tunnel de Cloudflare cambia de dirección al reiniciarse).
 * - http (acceso directo): el hostname de la página; el puerto lo añade quien llama.
 */
export function resolveWsHost(
  loc: { protocol: string; hostname: string; host: string },
  configuredHost?: string | null
): string {
  if (loc.protocol === 'https:') {
    return configuredHost || loc.host;
  }
  return loc.hostname;
}
