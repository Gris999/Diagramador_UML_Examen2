import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { PLATFORM_ID, provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { environment } from '../../environments/environment';
import { AuthService, SESSION_STORAGE_KEY, readStoredSession } from './auth.service';

describe('AuthService', () => {
  const api = `${environment.endpoint_python}api/auth/`;
  let http: HttpTestingController;
  let navigate: jasmine.Spy;
  const session = { token: 'tok', email: 'ana@x.com', name: 'Ana' };

  function create(platform: 'browser' | 'server' = 'browser'): AuthService {
    navigate = jasmine.createSpy('navigate').and.resolveTo(true);
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: PLATFORM_ID, useValue: platform },
        { provide: Router, useValue: { navigate, url: '/diagram/sala-1' } }
      ]
    });
    http = TestBed.inject(HttpTestingController);
    return TestBed.inject(AuthService);
  }

  beforeEach(() => localStorage.removeItem(SESSION_STORAGE_KEY));
  afterEach(() => localStorage.removeItem(SESSION_STORAGE_KEY));

  describe('the stored session', () => {
    it('starts without a session when nothing was saved', () => {
      const auth = create();

      expect(auth.session()).toBeNull();
      expect(auth.loggedIn()).toBeFalse();
      expect(auth.token()).toBeNull();
    });

    it('picks up the session saved by an earlier visit', () => {
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));

      const auth = create();

      expect(auth.loggedIn()).toBeTrue();
      expect(auth.token()).toBe('tok');
      expect(auth.session()?.email).toBe('ana@x.com');
    });

    it('ignores saved data that is not a session', () => {
      for (const raw of ['no es json', '"texto"', '{"token":"x"}', '{"token":"","email":"a@b.c","name":"A"}', '[1,2]', 'null']) {
        localStorage.setItem(SESSION_STORAGE_KEY, raw);
        expect(readStoredSession()).withContext(raw).toBeNull();
      }
    });

    it('does not read the browser storage on the server', () => {
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));

      expect(create('server').loggedIn()).toBeFalse();
    });
  });

  describe('what the server asks', () => {
    it('asks once and remembers the answer', () => {
      const auth = create();
      const answers: unknown[] = [];

      auth.ensureConfig().subscribe(value => answers.push(value));
      http.expectOne(`${api}config/`).flush({ authRequired: true, mailConfigured: true });
      auth.ensureConfig().subscribe(value => answers.push(value));

      http.expectNone(`${api}config/`);
      expect(answers).toEqual([{ authRequired: true, mailConfigured: true }, { authRequired: true, mailConfigured: true }]);
      expect(auth.config()).toEqual({ authRequired: true, mailConfigured: true });
    });

    it('takes anything that is not a clear true as false', () => {
      const auth = create();

      auth.ensureConfig().subscribe();
      http.expectOne(`${api}config/`).flush({ authRequired: 'sí', mailConfigured: 1 });

      expect(auth.config()).toEqual({ authRequired: false, mailConfigured: false });
    });

    it('lets people through when the server does not answer, instead of locking everybody out', () => {
      const auth = create();
      let answer: unknown;

      auth.ensureConfig().subscribe(value => (answer = value));
      http.expectOne(`${api}config/`).flush('error', { status: 500, statusText: 'Error' });

      expect(answer).toEqual({ authRequired: false, mailConfigured: false });
    });
  });

  describe('logging in', () => {
    it('asks for a code to be mailed to the address', () => {
      const auth = create();
      let done = false;

      auth.requestCode('ana@x.com').subscribe(() => (done = true));
      const request = http.expectOne(`${api}code/`);
      expect(request.request.method).toBe('POST');
      expect(request.request.body).toEqual({ email: 'ana@x.com' });
      request.flush({ sent: true });

      expect(done).toBeTrue();
    });

    it('exchanges the code for a session and keeps it for the next visit', () => {
      const auth = create();

      auth.verify('ana@x.com', '123456').subscribe();
      const request = http.expectOne(`${api}verify/`);
      expect(request.request.body).toEqual({ email: 'ana@x.com', code: '123456' });
      request.flush(session);

      expect(auth.loggedIn()).toBeTrue();
      expect(auth.token()).toBe('tok');
      expect(readStoredSession()).toEqual(session);
    });

    it('does not keep anything when the code is wrong', () => {
      const auth = create();
      let failed = false;

      auth.verify('ana@x.com', '000000').subscribe({ error: () => (failed = true) });
      http.expectOne(`${api}verify/`).flush({ error: 'El código no es válido' }, { status: 400, statusText: 'Bad Request' });

      expect(failed).toBeTrue();
      expect(auth.loggedIn()).toBeFalse();
      expect(readStoredSession()).toBeNull();
    });

    it('logs out: the session is gone from memory and from the browser', () => {
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
      const auth = create();

      auth.logout();

      expect(auth.loggedIn()).toBeFalse();
      expect(localStorage.getItem(SESSION_STORAGE_KEY)).toBeNull();
    });

    it('still logs in for this visit when the browser refuses to store it', () => {
      const auth = create();
      spyOn(Storage.prototype, 'setItem').and.throwError('bloqueado');

      auth.verify('ana@x.com', '123456').subscribe();
      http.expectOne(`${api}verify/`).flush(session);

      expect(auth.loggedIn()).toBeTrue();
    });
  });

  describe('when the session stops working', () => {
    it('clears it and goes back to the login page remembering where the person was, if login is required', () => {
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
      const auth = create();
      auth.config.set({ authRequired: true, mailConfigured: true });

      auth.expire();

      expect(auth.loggedIn()).toBeFalse();
      expect(navigate).toHaveBeenCalledOnceWith(['/entrar'], { queryParams: { volver: '/diagram/sala-1' } });
    });

    it('does not move the person when login is not required', () => {
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
      const auth = create();
      auth.config.set({ authRequired: false, mailConfigured: true });

      auth.expire();

      expect(auth.loggedIn()).toBeFalse();
      expect(navigate).not.toHaveBeenCalled();
    });

    it('does nothing when there was no session', () => {
      const auth = create();
      auth.config.set({ authRequired: true, mailConfigured: true });

      auth.expire();

      expect(navigate).not.toHaveBeenCalled();
    });
  });
});
