import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';
import { authInterceptor } from './auth.interceptor';

describe('authInterceptor', () => {
  const api = `${environment.endpoint_python}api/`;
  let http: HttpClient;
  let controller: HttpTestingController;
  let token: string | null;
  let expire: jasmine.Spy;

  beforeEach(() => {
    token = 'sesion-1';
    expire = jasmine.createSpy('expire');
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: { token: () => token, expire } }
      ]
    });
    http = TestBed.inject(HttpClient);
    controller = TestBed.inject(HttpTestingController);
  });

  it('sends the session with every request to this system API', () => {
    http.get(`${api}rooms/x/activity/`).subscribe();

    const request = controller.expectOne(`${api}rooms/x/activity/`);
    expect(request.request.headers.get('Authorization')).toBe('Bearer sesion-1');
    request.flush({});
  });

  it('keeps the session a request already carries (going back to another remembered account)', () => {
    http.get(`${api}auth/me/`, { headers: { Authorization: 'Bearer de-otra-cuenta' } }).subscribe();

    const request = controller.expectOne(`${api}auth/me/`);
    expect(request.request.headers.get('Authorization')).toBe('Bearer de-otra-cuenta');
    request.flush({});
  });

  it('sends nothing without a session', () => {
    token = null;

    http.get(`${api}rooms/x/activity/`).subscribe();

    const request = controller.expectOne(`${api}rooms/x/activity/`);
    expect(request.request.headers.has('Authorization')).toBeFalse();
    request.flush({});
  });

  it('never sends the session to another site', () => {
    http.get('https://otro-sitio.com/api/datos').subscribe();
    http.get('https://generativelanguage.googleapis.com/x').subscribe();

    for (const request of controller.match(() => true)) {
      expect(request.request.headers.has('Authorization')).toBeFalse();
      request.flush({});
    }
  });

  it('keeps the other headers of the request', () => {
    http.get(`${api}rooms/x/chat/`, { headers: { 'X-Participant-Token': 'abc' } }).subscribe();

    const request = controller.expectOne(`${api}rooms/x/chat/`);
    expect(request.request.headers.get('X-Participant-Token')).toBe('abc');
    expect(request.request.headers.get('Authorization')).toBe('Bearer sesion-1');
    request.flush({});
  });

  it('expires the session when the API says 401', () => {
    http.get(`${api}rooms/x/activity/`).subscribe({ error: () => undefined });

    controller.expectOne(`${api}rooms/x/activity/`).flush({ error: 'Inicia sesión' }, { status: 401, statusText: 'Unauthorized' });

    expect(expire).toHaveBeenCalledTimes(1);
  });

  it('does not expire the session because of a wrong code on the login routes', () => {
    http.post(`${api}auth/verify/`, {}).subscribe({ error: () => undefined });

    controller.expectOne(`${api}auth/verify/`).flush({ error: 'No' }, { status: 401, statusText: 'Unauthorized' });

    expect(expire).not.toHaveBeenCalled();
  });

  it('does not expire the session for other errors or for other sites', () => {
    http.get(`${api}a/`).subscribe({ error: () => undefined });
    http.get('https://otro-sitio.com/x').subscribe({ error: () => undefined });

    controller.expectOne(`${api}a/`).flush('x', { status: 403, statusText: 'Forbidden' });
    controller.expectOne('https://otro-sitio.com/x').flush('x', { status: 401, statusText: 'Unauthorized' });

    expect(expire).not.toHaveBeenCalled();
  });

  it('passes the error along so the caller still sees it', () => {
    let status = 0;
    http.get(`${api}a/`).subscribe({ error: error => (status = error.status) });

    controller.expectOne(`${api}a/`).flush('x', { status: 401, statusText: 'Unauthorized' });

    expect(status).toBe(401);
  });
});
