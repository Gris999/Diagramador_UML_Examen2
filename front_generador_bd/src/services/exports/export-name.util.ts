/**
 * Nombre de archivo seguro a partir del nombre de la app: "Sistema Escolar UAGRM" -> "sistema-escolar-uagrm".
 * Sin tildes ni símbolos; si no queda nada, `fallback`.
 */
export function exportFileBase(appName: string, fallback = 'mi-aplicacion'): string {
  const slug = (appName ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return slug || fallback;
}
