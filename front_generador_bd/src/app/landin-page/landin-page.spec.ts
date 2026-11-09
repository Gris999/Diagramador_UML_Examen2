import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { validate as isUuid } from 'uuid';
import { SESSION_STORAGE_KEY, AuthService } from '../../services/auth/auth.service';
import { THEME_STORAGE_KEY, ThemeService } from '../../services/theme.service';

import { LandinPage } from './landin-page';

describe('LandinPage', () => {
  let component: LandinPage;
  let fixture: ComponentFixture<LandinPage>;

  let navigate: jasmine.Spy;

  function element(selector: string): HTMLElement | null {
    return (fixture.nativeElement as HTMLElement).querySelector(selector);
  }

  function typeCode(code: string): void {
    const input = element('input') as HTMLInputElement;
    input.value = code;
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }

  function clickJoin(): void {
    const buttons = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button')) as HTMLButtonElement[];
    buttons.find(button => button.textContent?.includes('Unirse al Lienzo'))!.click();
    fixture.detectChanges();
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LandinPage],
      providers: [provideZonelessChangeDetection(), provideRouter([]), provideHttpClient(), provideHttpClientTesting()]
    })
    .compileComponents();

    navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(LandinPage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('offers the help assistant before entering any room', () => {
    const help = (fixture.nativeElement as HTMLElement).querySelector('app-help-panel [data-testid="help-toggle"]');

    expect(help).not.toBeNull();
    expect(help!.textContent).toContain('Ayuda');
  });

  it('creates a new room with a unique code and opens its editor', () => {
    component.crearNuevoLienzo();
    component.crearNuevoLienzo();

    const [first, second] = navigate.calls.allArgs().map(args => args[0] as string[]);
    expect(first[0]).toBe('/diagram');
    expect(isUuid(first[1])).toBeTrue();
    expect(isUuid(second[1])).toBeTrue();
    expect(first[1]).not.toBe(second[1]);
  });

  it('joins the room whose code is typed, ignoring spaces and capital letters', async () => {
    typeCode('  3F2A9C1E-5B7D-4E8A-9C3B-1A2B3C4D5E6F  ');
    await fixture.whenStable();

    clickJoin();

    expect(navigate).toHaveBeenCalledOnceWith(['/diagram', '3f2a9c1e-5b7d-4e8a-9c3b-1a2b3c4d5e6f']);
    expect(element('[data-testid="join-error"]')).toBeNull();
  });

  it('does not join with something that is not a room code and tells the person why', async () => {
    typeCode('mi-sala');
    await fixture.whenStable();

    clickJoin();

    expect(navigate).not.toHaveBeenCalled();
    expect(element('[data-testid="join-error"]')!.textContent).toContain('El código no es válido');
  });

  it('clears the warning when the person edits the code again', async () => {
    typeCode('mi-sala');
    await fixture.whenStable();
    clickJoin();

    typeCode('mi-sala-2');
    await fixture.whenStable();
    fixture.detectChanges();

    expect(element('[data-testid="join-error"]')).toBeNull();
  });

  it('does not let a person join without typing a code', () => {
    const join = (Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button')) as HTMLButtonElement[]).find(button =>
      button.textContent?.includes('Unirse al Lienzo')
    )!;

    expect(join.disabled).toBeTrue();
  });

  it('lets the person switch between the dark and the light theme from the start page', () => {
    const theme = TestBed.inject(ThemeService);
    const before = theme.theme();
    try {
      (element('[data-testid="theme-toggle"]') as HTMLButtonElement).click();
      fixture.detectChanges();

      expect(theme.theme()).not.toBe(before);
      expect(document.documentElement.getAttribute('data-theme')).toBe(theme.theme());
    } finally {
      localStorage.removeItem(THEME_STORAGE_KEY);
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  });

  describe('the list of diagrams', () => {
    const stored = { token: 'tok', email: 'ana@x.com', name: 'Ana' };
    let auth: AuthService;

    beforeEach(() => {
      localStorage.removeItem(SESSION_STORAGE_KEY);
      auth = TestBed.inject(AuthService);
    });

    afterEach(() => localStorage.removeItem(SESSION_STORAGE_KEY));

    it('keeps the code boxes of always when the server works without accounts', () => {
      auth.config.set({ authRequired: false, mailConfigured: false });
      fixture.detectChanges();

      expect(element('[data-testid="my-diagrams"]')).toBeNull();
      expect(element('input[aria-label="Código del lienzo"]')).not.toBeNull();
    });

    it('shows "Mis diagramas" instead of the code boxes when the person logged in with the email', () => {
      auth.config.set({ authRequired: true, mailConfigured: true });
      auth.session.set(stored);
      fixture.detectChanges();

      expect(element('[data-testid="my-diagrams"]')).not.toBeNull();
      expect(element('input[aria-label="Código del lienzo"]')).toBeNull();
    });
  });

  describe('the account', () => {
    const stored = { token: 'tok', email: 'ana@x.com', name: 'Ana' };
    let auth: AuthService;

    beforeEach(() => {
      localStorage.removeItem(SESSION_STORAGE_KEY);
      auth = TestBed.inject(AuthService);
    });

    afterEach(() => localStorage.removeItem(SESSION_STORAGE_KEY));

    it('shows nothing about an account when nobody logged in', () => {
      expect(element('[data-testid="account-email"]')).toBeNull();
      expect(element('[data-testid="logout"]')).toBeNull();
    });

    it('shows who is logged in and a button to log out', () => {
      auth.session.set(stored);
      fixture.detectChanges();

      expect(element('[data-testid="account-email"]')!.textContent).toContain('ana@x.com');
      expect(element('[data-testid="logout"]')!.textContent).toContain('Cerrar sesión');
    });

    it('offers to change account, which opens the login page with the remembered accounts without closing the session', () => {
      auth.session.set(stored);
      auth.config.set({ authRequired: true, mailConfigured: true });
      fixture.detectChanges();

      (element('[data-testid="switch-account"]') as HTMLButtonElement).click();

      expect(navigate).toHaveBeenCalledWith(['/entrar'], { queryParams: { cambiar: 1 } });
      expect(auth.loggedIn()).toBeTrue();
    });

    it('logs out and goes to the login page when the server asks for a session', () => {
      auth.session.set(stored);
      auth.config.set({ authRequired: true, mailConfigured: true });
      fixture.detectChanges();

      (element('[data-testid="logout"]') as HTMLButtonElement).click();
      fixture.detectChanges();

      expect(auth.loggedIn()).toBeFalse();
      expect(navigate).toHaveBeenCalledWith(['/entrar']);
      expect(element('[data-testid="account-email"]')).toBeNull();
    });

    it('logs out and stays on the start page when the server does not ask for a session', () => {
      auth.session.set(stored);
      auth.config.set({ authRequired: false, mailConfigured: true });
      fixture.detectChanges();

      (element('[data-testid="logout"]') as HTMLButtonElement).click();

      expect(auth.loggedIn()).toBeFalse();
      expect(navigate).not.toHaveBeenCalledWith(['/entrar']);
    });
  });
});
