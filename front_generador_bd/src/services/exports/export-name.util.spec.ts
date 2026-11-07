import { exportFileBase } from './export-name.util';

describe('exportFileBase', () => {
  it('turns the app name into a safe file name without accents or symbols', () => {
    expect(exportFileBase('Sistema Escolar UAGRM')).toBe('sistema-escolar-uagrm');
    expect(exportFileBase('  Gestión de Pedidos & Cía.  ')).toBe('gestion-de-pedidos-cia');
  });

  it('falls back to a neutral name when nothing usable is left', () => {
    expect(exportFileBase('')).toBe('mi-aplicacion');
    expect(exportFileBase('¿¡!?')).toBe('mi-aplicacion');
    expect(exportFileBase('', 'proyecto')).toBe('proyecto');
  });
});
