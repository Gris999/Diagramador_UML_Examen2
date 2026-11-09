import { HttpErrorResponse } from '@angular/common/http';
import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, UrlTree, convertToParamMap } from '@angular/router';
import { Observable, firstValueFrom, isObservable, of, throwError } from 'rxjs';
import { AuthConfig, AuthService } from './auth.service';
import { RoomAccess, RoomAccessService } from './room-access.service';
import { phoneGuard, roomAccessGuard, viewerGuard } from './room.guards';

describe('room guards', () => {
  let router: Router;
  let config: AuthConfig;
  let browser: boolean;
  let enter: jasmine.Spy<(room: string) => Observable<RoomAccess>>;
  let lastAccess: jasmine.Spy<(room: string) => RoomAccess | undefined>;

  const route = (roomId: string | null) => ({ paramMap: convertToParamMap(roomId ? { roomId } : {}) }) as unknown as ActivatedRouteSnapshot;

  async function run(guard: typeof roomAccessGuard, roomId: string | null = 'sala-1'): Promise<boolean | UrlTree> {
    const result = TestBed.runInInjectionContext(() => guard(route(roomId), {} as never));
    return (isObservable(result) ? firstValueFrom(result) : result) as Promise<boolean | UrlTree>;
  }

  beforeEach(() => {
    config = { authRequired: true, mailConfigured: true };
    browser = true;
    enter = jasmine.createSpy('enter').and.returnValue(of({ required: true, email: 'ana@x.com', role: 'owner', members: [] }));
    lastAccess = jasmine.createSpy('lastAccess').and.returnValue(undefined);
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        { provide: AuthService, useValue: { isBrowser: () => browser, ensureConfig: () => of(config) } },
        { provide: RoomAccessService, useValue: { enter, lastAccess } }
      ]
    });
    router = TestBed.inject(Router);
  });

  describe('roomAccessGuard', () => {
    it('lets the person in when the server controls access and the address is on the list', async () => {
      expect(await run(roomAccessGuard)).toBeTrue();
      expect(enter).toHaveBeenCalledOnceWith('sala-1');
    });

    it('sends whoever was not invited to the page that explains it, remembering the room', async () => {
      enter.and.returnValue(throwError(() => new HttpErrorResponse({ status: 403, error: { code: 'not_invited' } })));

      const result = await run(roomAccessGuard);

      expect(result instanceof UrlTree).toBeTrue();
      expect(router.serializeUrl(result as UrlTree)).toBe('/sin-acceso?sala=sala-1');
    });

    it('does not open the room when the session was refused (the interceptor already goes to the login)', async () => {
      enter.and.returnValue(throwError(() => new HttpErrorResponse({ status: 401 })));

      expect(await run(roomAccessGuard)).toBeFalse();
    });

    it('lets the screen show its own error for any other failure', async () => {
      enter.and.returnValue(throwError(() => new HttpErrorResponse({ status: 500 })));

      expect(await run(roomAccessGuard)).toBeTrue();
    });

    it('asks nothing when the server does not control access', async () => {
      config = { authRequired: false, mailConfigured: false };

      expect(await run(roomAccessGuard)).toBeTrue();
      expect(enter).not.toHaveBeenCalled();
    });

    it('asks nothing on the server render or without a room', async () => {
      browser = false;
      expect(await run(roomAccessGuard)).toBeTrue();
      browser = true;
      expect(await run(roomAccessGuard, null)).toBeTrue();
      expect(enter).not.toHaveBeenCalled();
    });
  });

  describe('viewerGuard', () => {
    it('sends someone who can only read to the read-only view of the same room instead of the editor', async () => {
      lastAccess.and.returnValue({ required: true, email: 'eva@x.com', role: 'viewer', can_edit: false, members: [] });

      const result = await run(viewerGuard);

      expect(result instanceof UrlTree).toBeTrue();
      expect(router.serializeUrl(result as UrlTree)).toBe('/sala/sala-1/seguir');
    });

    it('lets owners and editors open the editor', async () => {
      lastAccess.and.returnValue({ required: true, email: 'ana@x.com', role: 'owner', can_edit: true, members: [] });
      expect(await run(viewerGuard)).toBeTrue();
      lastAccess.and.returnValue({ required: true, email: 'beto@x.com', role: 'editor', can_edit: true, members: [] });
      expect(await run(viewerGuard)).toBeTrue();
    });

    it('lets everyone through when nothing is known (the server without accounts, or no room)', async () => {
      expect(await run(viewerGuard)).toBeTrue();
      lastAccess.and.returnValue({ required: false, email: null, role: null, can_edit: true, members: [] });
      expect(await run(viewerGuard)).toBeTrue();
      expect(await run(viewerGuard, null)).toBeTrue();
    });
  });

  describe('phoneGuard', () => {
    const original = Object.getOwnPropertyDescriptor(window.navigator, 'userAgent');
    const setUserAgent = (value: string) => Object.defineProperty(window.navigator, 'userAgent', { value, configurable: true });

    afterEach(() => {
      if (original) Object.defineProperty(window.navigator, 'userAgent', original);
      else delete (window.navigator as { userAgent?: string }).userAgent;
    });

    it('sends a phone to the read-only view of the same room instead of the editor', async () => {
      setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1');

      const result = await run(phoneGuard);

      expect(result instanceof UrlTree).toBeTrue();
      expect(router.serializeUrl(result as UrlTree)).toBe('/sala/sala-1/seguir');
    });

    it('lets a computer or a tablet open the editor', async () => {
      setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/18.0 Safari/605.1.15');
      expect(await run(phoneGuard)).toBeTrue();

      setUserAgent('Mozilla/5.0 (iPad; CPU OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1');
      expect(await run(phoneGuard)).toBeTrue();
    });

    it('does nothing without a room', async () => {
      setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Mobile/15E148');

      expect(await run(phoneGuard, null)).toBeTrue();
    });
  });
});
