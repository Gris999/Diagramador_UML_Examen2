import { of } from 'rxjs';

import { XmiService } from './xmi.service';

// Sin TestBed: en este proyecto TestBed falla con NG0908 (falta Zone.js en la
// configuración de pruebas), igual que otras specs que instancian el servicio directo.
describe('XmiService export', () => {
  it('omits association-class connectors while preserving supported relationships', () => {
    const http: any = { post: jasmine.createSpy('post').and.returnValue(of(new Blob(['xmi']))) };
    const service = new XmiService(http);
    const uml: any = {
      classes: [
        { id: 'a', name: 'A', attributes: [], methods: [] },
        { id: 'b', name: 'B', attributes: [], methods: [] },
        { id: 'detail', name: 'Detail', attributes: [], methods: [] }
      ],
      relationships: [
        { id: 'mn', type: 'association', sourceId: 'a', targetId: 'b', labels: ['*', '*'] },
        { id: 'aux-a', type: 'association-class', sourceId: 'detail', targetId: 'a', labels: [] },
        { id: 'aux-b', type: 'association-class', sourceId: 'detail', targetId: 'b', labels: [] }
      ]
    };

    service.exportXmi(uml).subscribe();

    expect(http.post).toHaveBeenCalledTimes(1);
    const [url, body, options] = http.post.calls.mostRecent().args;
    expect(url.endsWith('/api/xmi/export/')).toBeTrue();
    expect(options).toEqual(jasmine.objectContaining({ responseType: 'blob' }));
    expect(body.classes).toEqual(uml.classes);
    expect(body.relationships).toEqual([uml.relationships[0]]);
    // El objeto original no se modifica.
    expect(uml.relationships.length).toBe(3);
  });
});
