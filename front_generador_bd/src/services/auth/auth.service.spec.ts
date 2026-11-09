import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { PLATFORM_ID, provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { environment } from '../../environments/environment';
import { ACCOUNTS_STORAGE_KEY, AuthService, MAX_ACCOUNTS, SESSION_STORAGE_KEY, readStoredAccounts, readStoredSession } from './auth.service';

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

  const clean = () => {
    localStorage.removeItem(SESSION_STORAGE_KEY);
    localStorage.removeItem(ACCOUNTS_STORAGE_KEY);
  };
  beforeEach(clean);
  afterEach(clean);

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

  describe('the accounts remembered in this browser', () => {
    const beto = { token: 'tok-b', email: 'beto@x.com', name: 'Beto' };

    it('remembers each account that logs in, the latest first, and the session is the latest', () => {
      const auth = create();

      auth.verify('ana@x.com', '123456').subscribe();
      http.expectOne(`${api}verify/`).flush(session);
      auth.verify('beto@x.com', '654321').subscribe();
      http.expectOne(`${api}verify/`).flush(beto);

      expect(auth.accounts().map(account => account.email)).toEqual(['beto@x.com', 'ana@x.com']);
      expect(auth.session()?.email).toBe('beto@x.com');
      expect(readStoredAccounts().map(account => account.email)).toEqual(['beto@x.com', 'ana@x.com']);
    });

    it('does not repeat an address: logging in again replaces its session', () => {
      const auth = create();

      auth.verify('ana@x.com', '1').subscribe();
      http.expectOne(`${api}verify/`).flush(session);
      auth.verify('ana@x.com', '2').subscribe();
      http.expectOne(`${api}verify/`).flush({ ...session, token: 'otro' });

      expect(auth.accounts()).toEqual([{ ...session, token: 'otro' }]);
    });

    it('remembers only a few: the one used the longest ago is forgotten', () => {
      const auth = create();

      for (let n = 0; n <= MAX_ACCOUNTS; n++) {
        auth.verify(`p${n}@x.com`, '1').subscribe();
        http.expectOne(`${api}verify/`).flush({ token: `t${n}`, email: `p${n}@x.com`, name: `P${n}` });
      }

      expect(auth.accounts().length).toBe(MAX_ACCOUNTS);
      expect(auth.accounts().some(account => account.email === 'p0@x.com')).toBeFalse();
    });

    it('picks up the accounts of an earlier visit, and the session of a version that did not keep a list', () => {
      localStorage.setItem(ACCOUNTS_STORAGE_KEY, JSON.stringify([beto]));
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));

      const auth = create();

      expect(auth.accounts().map(account => account.email)).toEqual(['ana@x.com', 'beto@x.com']);
    });

    it('ignores a list that is not a list of sessions', () => {
      for (const raw of ['no es json', '{"a":1}', '[1,"x",{"token":"x"}]', 'null']) {
        localStorage.setItem(ACCOUNTS_STORAGE_KEY, raw);
        expect(readStoredAccounts()).withContext(raw).toEqual([]);
      }
    });

    it('logging out forgets only the current account', () => {
      localStorage.setItem(ACCOUNTS_STORAGE_KEY, JSON.stringify([session, beto]));
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
      const auth = create();

      auth.logout();

      expect(auth.loggedIn()).toBeFalse();
      expect(auth.accounts().map(account => account.email)).toEqual(['beto@x.com']);
      expect(readStoredAccounts().map(account => account.email)).toEqual(['beto@x.com']);
    });

    it('forgets another account without touching the session', () => {
      localStorage.setItem(ACCOUNTS_STORAGE_KEY, JSON.stringify([session, beto]));
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
      const auth = create();

      auth.forgetAccount('beto@x.com');

      expect(auth.session()?.email).toBe('ana@x.com');
      expect(auth.accounts().map(account => account.email)).toEqual(['ana@x.com']);
    });

    it('forgetting the current account is the same as logging out', () => {
      localStorage.setItem(ACCOUNTS_STORAGE_KEY, JSON.stringify([session, beto]));
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
      const auth = create();

      auth.forgetAccount('ana@x.com');

      expect(auth.loggedIn()).toBeFalse();
      expect(localStorage.getItem(SESSION_STORAGE_KEY)).toBeNull();
    });

    it('goes back to a remembered account without a code, with the session that account kept, and renews it', () => {
      localStorage.setItem(ACCOUNTS_STORAGE_KEY, JSON.stringify([session, beto]));
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
      const auth = create();
      let result: unknown;

      auth.resume('beto@x.com').subscribe(value => (result = value));
      const request = http.expectOne(`${api}me/`);
      expect(request.request.headers.get('Authorization')).toBe('Bearer tok-b');
      request.flush({ email: 'beto@x.com', name: 'Beto', token: 'tok-b-nueva' });

      expect(result).toEqual({ token: 'tok-b-nueva', email: 'beto@x.com', name: 'Beto' });
      expect(auth.session()).toEqual({ token: 'tok-b-nueva', email: 'beto@x.com', name: 'Beto' });
      expect(readStoredSession()?.email).toBe('beto@x.com');
      expect(auth.accounts()[0].email).toBe('beto@x.com');
    });

    it('forgets the account and says so (401) when its session no longer works', () => {
      localStorage.setItem(ACCOUNTS_STORAGE_KEY, JSON.stringify([session, beto]));
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
      const auth = create();
      let status = 0;

      auth.resume('beto@x.com').subscribe({ error: error => (status = error.status) });
      http.expectOne(`${api}me/`).flush({ error: 'Inicia sesión' }, { status: 401, statusText: 'Unauthorized' });

      expect(status).toBe(401);
      expect(auth.accounts().map(account => account.email)).toEqual(['ana@x.com']);
      expect(auth.session()?.email).toBe('ana@x.com');
    });

    it('keeps the account when the failure is not a rejected session (no network, server down)', () => {
      localStorage.setItem(ACCOUNTS_STORAGE_KEY, JSON.stringify([beto]));
      const auth = create();

      auth.resume('beto@x.com').subscribe({ error: () => undefined });
      http.expectOne(`${api}me/`).flush('x', { status: 500, statusText: 'Server Error' });

      expect(auth.accounts().map(account => account.email)).toEqual(['beto@x.com']);
    });

    it('does not resume an account that is not remembered', () => {
      const auth = create();
      let failed = false;

      auth.resume('nadie@x.com').subscribe({ error: () => (failed = true) });

      http.expectNone(`${api}me/`);
      expect(failed).toBeTrue();
    });
  });

  describe('staying logged in', () => {
    beforeEach(() => localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session)));

    it('asks the server once per visit who the session is and keeps the fresh one it gets back', () => {
      const auth = create();

      auth.renew();
      auth.renew();
      const request = http.expectOne(`${api}me/`);
      request.flush({ email: 'ana@x.com', name: 'Ana', token: 'tok-nueva' });

      expect(auth.token()).toBe('tok-nueva');
      expect(readStoredSession()?.token).toBe('tok-nueva');
      http.expectNone(`${api}me/`);
    });

    it('asks to log in again when the server refuses the session', () => {
      const auth = create();
      auth.config.set({ authRequired: true, mailConfigured: true });

      auth.renew();
      http.expectOne(`${api}me/`).flush({ error: 'Inicia sesión' }, { status: 401, statusText: 'Unauthorized' });

      expect(auth.loggedIn()).toBeFalse();
      expect(navigate).toHaveBeenCalledWith(['/entrar'], { queryParams: { volver: '/diagram/sala-1' } });
    });

    it('keeps the session when the server cannot be reached', () => {
      const auth = create();

      auth.renew();
      http.expectOne(`${api}me/`).error(new ProgressEvent('error'));

      expect(auth.loggedIn()).toBeTrue();
    });

    it('does nothing without a session', () => {
      localStorage.removeItem(SESSION_STORAGE_KEY);
      create().renew();
      http.expectNone(`${api}me/`);
    });

    it('does nothing on the server render', () => {
      create('server').renew();
      http.expectNone(`${api}me/`);
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

  describe('when the account has no invitation to a room', () => {
    it('goes to the page that explains it, remembering the room', () => {
      const auth = create();

      auth.notInvited('sala-9');

      expect(navigate).toHaveBeenCalledOnceWith(['/sin-acceso'], { queryParams: { sala: 'sala-9' } });
    });

    it('goes there without a room when it is not known', () => {
      const auth = create();

      auth.notInvited(null);

      expect(navigate).toHaveBeenCalledOnceWith(['/sin-acceso'], {});
    });

    it('keeps the session: the address is fine, it just was not invited', () => {
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
      const auth = create();

      auth.notInvited('sala-9');

      expect(auth.loggedIn()).toBeTrue();
    });
  });
});
