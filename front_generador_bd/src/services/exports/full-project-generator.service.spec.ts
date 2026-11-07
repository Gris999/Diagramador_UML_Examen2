import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../environments/environment';
import { FullProjectGeneratorService } from './full-project-generator.service';

describe('FullProjectGeneratorService', () => {
  let service: FullProjectGeneratorService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideZonelessChangeDetection(), provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(FullProjectGeneratorService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('asks the server for the single ZIP with backend, mobile app, SQL and instructions', () => {
    const diagram = { classes: [{ id: 'a', name: 'Alumno' }], relationships: [], appName: 'Sistema Escolar', sqlScript: 'CREATE TABLE a();' };
    service.generateAll(diagram, 'sistema-escolar.zip');

    const request = http.expectOne(`${environment.endpoint_python}api/generar_todo/`);
    expect(request.request.method).toBe('POST');
    expect(request.request.responseType).toBe('blob');
    expect(request.request.body).toEqual(diagram);
    expect(service.loading()).toBeTrue();
    request.flush(new Blob(['zip']));
    expect(service.loading()).toBeFalse();
  });

  it('tells the person when the project cannot be generated, and stops the spinner', () => {
    const alertSpy = spyOn(window, 'alert');
    spyOn(console, 'error');

    service.generateAll({ classes: [], relationships: [] });
    http.expectOne(`${environment.endpoint_python}api/generar_todo/`).flush(new Blob(['{}']), { status: 502, statusText: 'Bad Gateway' });

    expect(alertSpy).toHaveBeenCalledTimes(1);
    expect(alertSpy.calls.mostRecent().args[0]).toContain('No se pudo generar el proyecto completo');
    expect(service.loading()).toBeFalse();
  });
});
