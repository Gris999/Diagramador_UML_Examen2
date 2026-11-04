import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../environments/environment';
import { FrontendGeneratorService } from './frontend-generator.service';

describe('FrontendGeneratorService', () => {
  let service: FrontendGeneratorService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideZonelessChangeDetection(), provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(FrontendGeneratorService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('asks the server for the Flutter project of the diagram', () => {
    service.generateFrontend({ classes: [], relationships: [] });

    const request = http.expectOne(`${environment.endpoint_python}api/generar_flutter/`);
    expect(request.request.method).toBe('POST');
    expect(request.request.responseType).toBe('blob');
    request.flush(new Blob(['zip']));
    expect(service.loading()).toBeFalse();
  });

  it('tells the person when the diagram cannot be generated, and stops the spinner', () => {
    const alertSpy = spyOn(window, 'alert');
    spyOn(console, 'error');

    service.generateFrontend({ classes: [], relationships: [] });
    expect(service.loading()).toBeTrue();
    http.expectOne(`${environment.endpoint_python}api/generar_flutter/`).flush(new Blob(['{}']), { status: 400, statusText: 'Bad Request' });

    expect(alertSpy).toHaveBeenCalledOnceWith('No se pudo generar la aplicación móvil. Revisa que el diagrama tenga clases e inténtalo de nuevo.');
    expect(service.loading()).toBeFalse();
  });
});
