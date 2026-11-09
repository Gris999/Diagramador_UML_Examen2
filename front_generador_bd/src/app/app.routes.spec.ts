import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { of } from 'rxjs';
import { AuthService } from '../services/auth/auth.service';
import { RoomAccessService } from '../services/auth/room-access.service';
import { routes } from './app.routes';

describe('routes', () => {
  let router: Router;
  let authRequired: boolean;
  let loggedIn: ReturnType<typeof signal<boolean>>;

  beforeEach(() => {
    authRequired = false;
    loggedIn = signal(false);
    // El servidor de pruebas no contesta: se simula lo que diría `/api/auth/config/`.
    const auth = {
      isBrowser: () => true,
      loggedIn,
      ensureConfig: () => of({ authRequired, mailConfigured: true }),
      config: signal(null),
      session: signal(null),
      token: () => null
    };
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter(routes),
        { provide: AuthService, useValue: auth },
        { provide: RoomAccessService, useValue: { enter: () => of({ required: true, email: 'ana@x.com', role: 'owner', members: [] }) } }
      ]
    });
    router = TestBed.inject(Router);
  });

  it('opens the editor only for a room: it takes the code from the address', () => {
    const editor = routes.find(route => route.path === 'diagram/:roomId');

    expect(editor).toBeDefined();
    expect(editor!.redirectTo).toBeUndefined();
  });

  it('sends whoever goes to the editor without a room back to the start page', async () => {
    await router.navigateByUrl('/diagram');

    expect(router.url).toBe('/');
  });

  it('sends any unknown address back to the start page', async () => {
    await router.navigateByUrl('/sala/algo/raro/mas');

    expect(router.url).toBe('/');
  });

  it('keeps the follow-along view on its own address', async () => {
    await router.navigateByUrl('/sala/3f2a9c1e-5b7d-4e8a-9c3b-1a2b3c4d5e6f/seguir');

    expect(router.url).toBe('/sala/3f2a9c1e-5b7d-4e8a-9c3b-1a2b3c4d5e6f/seguir');
  });

  describe('entering with the email', () => {
    it('lets everyone through when the server does not ask for a session', async () => {
      await router.navigateByUrl('/sala/3f2a9c1e-5b7d-4e8a-9c3b-1a2b3c4d5e6f/seguir');

      expect(router.url).toBe('/sala/3f2a9c1e-5b7d-4e8a-9c3b-1a2b3c4d5e6f/seguir');
    });

    it('sends whoever has no session to the login page and remembers where they were going', async () => {
      authRequired = true;

      await router.navigateByUrl('/diagram/3f2a9c1e-5b7d-4e8a-9c3b-1a2b3c4d5e6f');

      expect(router.url).toBe('/entrar?volver=%2Fdiagram%2F3f2a9c1e-5b7d-4e8a-9c3b-1a2b3c4d5e6f');
    });

    it('asks for the session on the start page and on the follow-along view too', async () => {
      authRequired = true;

      await router.navigateByUrl('/');
      expect(router.url).toBe('/entrar?volver=%2F');

      await router.navigateByUrl('/sala/3f2a9c1e-5b7d-4e8a-9c3b-1a2b3c4d5e6f/seguir');
      expect(router.url).toContain('/entrar?volver=%2Fsala%2F');
    });

    it('lets someone with a session go where they wanted', async () => {
      authRequired = true;
      loggedIn.set(true);

      await router.navigateByUrl('/diagram/3f2a9c1e-5b7d-4e8a-9c3b-1a2b3c4d5e6f');

      expect(router.url).toBe('/diagram/3f2a9c1e-5b7d-4e8a-9c3b-1a2b3c4d5e6f');
    });

    it('keeps the login page open for everybody', () => {
      const login = routes.find(route => route.path === 'entrar');

      expect(login).toBeDefined();
      expect(login!.canActivate).toBeUndefined();
    });
  });
});
