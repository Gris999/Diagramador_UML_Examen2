import { resolveWsHost } from './ws-host.util';

describe('resolveWsHost', () => {
  const https = { protocol: 'https:', hostname: 'demo.trycloudflare.com', host: 'demo.trycloudflare.com' };
  const httpDirect = { protocol: 'http:', hostname: '18.188.167.127', host: '18.188.167.127:4200' };

  it('usa el host de la propia página por https cuando el entorno no fija uno', () => {
    expect(resolveWsHost(https, '')).toBe('demo.trycloudflare.com');
    expect(resolveWsHost(https, undefined)).toBe('demo.trycloudflare.com');
  });

  it('respeta el host configurado por https si existe', () => {
    expect(resolveWsHost(https, 'ws.ejemplo.com')).toBe('ws.ejemplo.com');
  });

  it('por http usa el hostname de la página sin el puerto de la web', () => {
    expect(resolveWsHost(httpDirect, '')).toBe('18.188.167.127');
    expect(resolveWsHost(httpDirect, 'ws.ejemplo.com')).toBe('18.188.167.127');
  });
});
