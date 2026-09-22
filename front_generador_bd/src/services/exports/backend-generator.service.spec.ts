import { BackendGeneratorService } from './backend-generator.service';

describe('BackendGeneratorService generator endpoint resolution', () => {
  let http: any;
  let service: BackendGeneratorService;

  beforeEach(() => {
    http = { post: jasmine.createSpy('post').and.returnValue({ subscribe: () => undefined }) };
    service = new BackendGeneratorService(http);
  });

  it('builds the Spring generator URL from the current window.location and fixed port 7001', () => {
    // window.location no se puede stubear en Karma/Chrome (propiedades no
    // configurables), así que se compara contra el mismo cálculo hecho aquí
    // con los valores reales de la página de test, en vez de fijar un host.
    const expectedUrl = `${window.location.protocol}//${window.location.hostname}:7001/generate`;

    service.generateBackend({ classes: [], relationships: [] });

    expect(http.post).toHaveBeenCalledWith(
      expectedUrl,
      jasmine.any(Object),
      jasmine.objectContaining({ responseType: 'blob' })
    );
  });

  it('never sends the request to the dead spring-sw1.fournext.me domain', () => {
    // Regresión: antes dependía de environment.endpoint_java, un dominio fijo
    // que dejó de resolver (curl: "Could not resolve host"). Ahora se adapta
    // al host real, igual que el WebSocket de colaboración (SignalingService).
    service.generateBackend({ classes: [], relationships: [] });

    const calledUrl = http.post.calls.mostRecent().args[0] as string;
    expect(calledUrl).not.toContain('fournext.me');
    expect(calledUrl.endsWith(':7001/generate')).toBeTrue();
  });
});
