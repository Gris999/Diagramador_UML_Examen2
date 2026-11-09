import { HttpErrorResponse } from '@angular/common/http';
import { provideZonelessChangeDetection, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { Observable, of, throwError } from 'rxjs';
import { AuthConfig, AuthService, Session } from '../../services/auth/auth.service';
import { LoginPage, RESEND_SECONDS, safeReturnUrl } from './login-page';

describe('safeReturnUrl', () => {
  it('only goes back to addresses of this same page', () => {
    expect(safeReturnUrl('/diagram/abc')).toBe('/diagram/abc');
    expect(safeReturnUrl('/sala/x/seguir')).toBe('/sala/x/seguir');
  });

  it('never goes to another site or back to the login page', () => {
    for (const value of [null, '', 'https://malo.com', '//malo.com', 'javascript:alert(1)', 'diagram/x', '/entrar', '/entrar?volver=/']) {
      expect(safeReturnUrl(value)).withContext(String(value)).toBe('/');
    }
  });
});

describe('LoginPage', () => {
  let fixture: ComponentFixture<LoginPage>;
  let requestCode: jasmine.Spy<(email: string) => Observable<void>>;
  let verify: jasmine.Spy<(email: string, code: string) => Observable<Session>>;
  let navigateByUrl: jasmine.Spy;
  let config: ReturnType<typeof signal<AuthConfig | null>>;
  let loggedIn: ReturnType<typeof signal<boolean>>;
  let volver: string | null;
  let cambiar: string | null;
  let accounts: ReturnType<typeof signal<Session[]>>;
  let active: ReturnType<typeof signal<Session | null>>;
  let resume: jasmine.Spy<(email: string) => Observable<Session>>;
  let forgetAccount: jasmine.Spy;

  const element = (testId: string) => fixture.nativeElement.querySelector(`[data-testid="${testId}"]`) as HTMLElement | null;
  const input = (testId: string) => element(testId) as HTMLInputElement;

  async function create(authConfig: AuthConfig = { authRequired: true, mailConfigured: true }): Promise<void> {
    config = signal<AuthConfig | null>(authConfig);
    loggedIn = signal(false);
    active = signal<Session | null>(null);
    resume = jasmine.createSpy('resume').and.returnValue(of({ token: 'nueva', email: 'beto@x.com', name: 'Beto' }));
    forgetAccount = jasmine.createSpy('forgetAccount').and.callFake((email: string) => accounts.update(list => list.filter(a => a.email !== email)));
    requestCode = jasmine.createSpy('requestCode').and.returnValue(of(undefined));
    verify = jasmine.createSpy('verify').and.returnValue(of({ token: 't', email: 'ana@x.com', name: 'Ana' }));
    navigateByUrl = jasmine.createSpy('navigateByUrl').and.resolveTo(true);
    TestBed.configureTestingModule({
      imports: [LoginPage],
      providers: [
        provideZonelessChangeDetection(),
        {
          provide: AuthService,
          useValue: { config, loggedIn, session: active, accounts, ensureConfig: () => of(config()), requestCode, verify, resume, forgetAccount }
        },
        { provide: Router, useValue: { navigateByUrl } },
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: { get: (key: string) => (key === 'cambiar' ? cambiar : volver) } } } }
      ]
    });
    fixture = TestBed.createComponent(LoginPage);
    fixture.detectChanges();
    await fixture.whenStable();
  }

  async function type(testId: string, value: string): Promise<void> {
    const field = input(testId);
    field.value = value;
    field.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    await fixture.whenStable();
  }

  async function sendEmail(email = 'ana@x.com'): Promise<void> {
    await type('login-email', email);
    element('login-send-code')!.click();
    fixture.detectChanges();
    await fixture.whenStable();
  }

  beforeEach(() => {
    volver = null;
    cambiar = null;
    accounts = signal<Session[]>([]);
  });

  it('starts by asking for the email, with nothing sent yet', async () => {
    await create();

    expect(element('login-email-form')).not.toBeNull();
    expect(element('login-code-form')).toBeNull();
    expect((element('login-send-code') as HTMLButtonElement).disabled).toBeTrue();
  });

  it('mails the code to the typed address and then asks for it', async () => {
    await create();

    await sendEmail('  Ana@X.com ');

    expect(requestCode).toHaveBeenCalledOnceWith('Ana@X.com');
    expect(element('login-code-form')).not.toBeNull();
    expect(element('login-sent-to')!.textContent).toContain('Ana@X.com');
  });

  it('shows the reason when the code could not be sent and stays on the email step', async () => {
    await create();
    requestCode.and.returnValue(throwError(() => new HttpErrorResponse({ status: 429, error: { error: 'Pediste demasiados códigos. Espera unos minutos.' } })));

    await sendEmail();

    expect(element('login-error')!.textContent).toContain('demasiados códigos');
    expect(element('login-email-form')).not.toBeNull();
    expect((element('login-send-code') as HTMLButtonElement).disabled).toBeFalse();
  });

  it('has a generic message when the server gives no reason', async () => {
    await create();
    requestCode.and.returnValue(throwError(() => new HttpErrorResponse({ status: 500 })));

    await sendEmail();

    expect(element('login-error')!.textContent).toContain('No pudimos mandar el correo');
  });

  it('only accepts digits in the code and no more than six', async () => {
    await create();
    await sendEmail();

    await type('login-code', '12a3-4 5678');

    expect(input('login-code').value).toBe('123456');
    expect((element('login-verify') as HTMLButtonElement).disabled).toBeFalse();
  });

  it('does not let the person send an incomplete code', async () => {
    await create();
    await sendEmail();

    await type('login-code', '123');

    expect((element('login-verify') as HTMLButtonElement).disabled).toBeTrue();
    element('login-verify')!.click();
    expect(verify).not.toHaveBeenCalled();
  });

  it('enters with the right code and goes to the start page', async () => {
    await create();
    await sendEmail('ana@x.com');
    await type('login-code', '123456');

    element('login-verify')!.click();
    fixture.detectChanges();
    await fixture.whenStable();

    expect(verify).toHaveBeenCalledOnceWith('ana@x.com', '123456');
    expect(navigateByUrl).toHaveBeenCalledOnceWith('/');
  });

  it('goes back to where the person was heading, when that is a page of this site', async () => {
    volver = '/diagram/3f2a9c1e';
    await create();
    await sendEmail();
    await type('login-code', '123456');

    element('login-verify')!.click();
    fixture.detectChanges();

    expect(navigateByUrl).toHaveBeenCalledWith('/diagram/3f2a9c1e');
  });

  it('never goes to another site even if the address asks for it', async () => {
    volver = 'https://malo.com';
    await create();
    await sendEmail();
    await type('login-code', '123456');

    element('login-verify')!.click();
    fixture.detectChanges();

    expect(navigateByUrl).toHaveBeenCalledWith('/');
  });

  it('says so when the code is wrong and lets the person try again', async () => {
    await create();
    await sendEmail();
    verify.and.returnValue(throwError(() => new HttpErrorResponse({ status: 400, error: { error: 'El código no es válido o ya venció. Pide uno nuevo.' } })));
    await type('login-code', '000000');

    element('login-verify')!.click();
    fixture.detectChanges();
    await fixture.whenStable();

    expect(element('login-error')!.textContent).toContain('no es válido');
    expect(navigateByUrl).not.toHaveBeenCalled();
    expect(element('login-code-form')).not.toBeNull();
  });

  it('lets the person fix a mistyped address', async () => {
    await create();
    await sendEmail('mal@x.com');

    element('login-change-email')!.click();
    fixture.detectChanges();

    expect(element('login-email-form')).not.toBeNull();
    expect(element('login-error')).toBeNull();
  });

  describe('asking for another code', () => {
    beforeEach(() => jasmine.clock().install());
    afterEach(() => jasmine.clock().uninstall());

    it('makes the person wait before asking again, counting down', async () => {
      await create();
      await sendEmail();

      expect((element('login-resend') as HTMLButtonElement).disabled).toBeTrue();
      expect(element('login-resend')!.textContent).toContain(`${RESEND_SECONDS} s`);

      jasmine.clock().tick(1000 * 5);
      fixture.detectChanges();
      expect(element('login-resend')!.textContent).toContain(`${RESEND_SECONDS - 5} s`);

      jasmine.clock().tick(1000 * RESEND_SECONDS);
      fixture.detectChanges();
      expect((element('login-resend') as HTMLButtonElement).disabled).toBeFalse();
      expect(element('login-resend')!.textContent).not.toContain(' s)');
    });

    it('mails a new code when the person asks after the wait', async () => {
      await create();
      await sendEmail();
      jasmine.clock().tick(1000 * (RESEND_SECONDS + 1));
      fixture.detectChanges();

      element('login-resend')!.click();
      fixture.detectChanges();

      expect(requestCode).toHaveBeenCalledTimes(2);
    });
  });

  it('warns when the server cannot send mail, so nobody waits for a code that will not come', async () => {
    await create({ authRequired: true, mailConfigured: false });

    expect(element('login-mail-missing')!.textContent).toContain('no puede mandar correos');
  });

  it('does not warn when the server can send mail', async () => {
    await create();

    expect(element('login-mail-missing')).toBeNull();
  });

  it('has nothing to do when the server does not ask for a session: it goes to the start page', async () => {
    await create({ authRequired: false, mailConfigured: true });

    expect(navigateByUrl).toHaveBeenCalledWith('/');
  });

  it('has nothing to do when the person already has a session', async () => {
    config = signal<AuthConfig | null>({ authRequired: true, mailConfigured: true });
    loggedIn = signal(true);
    navigateByUrl = jasmine.createSpy('navigateByUrl').and.resolveTo(true);
    TestBed.configureTestingModule({
      imports: [LoginPage],
      providers: [
        provideZonelessChangeDetection(),
        { provide: AuthService, useValue: { config, loggedIn, session: signal(null), accounts, ensureConfig: () => of(config()), requestCode, verify } },
        { provide: Router, useValue: { navigateByUrl } },
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: { get: () => null } } } }
      ]
    });

    TestBed.createComponent(LoginPage).detectChanges();

    expect(navigateByUrl).toHaveBeenCalledWith('/');
  });

  describe('the accounts remembered in this browser', () => {
    const ana = { token: 'ta', email: 'ana@x.com', name: 'Ana' };
    const beto = { token: 'tb', email: 'beto@x.com', name: 'Beto' };
    const rows = () => Array.from(fixture.nativeElement.querySelectorAll('[data-testid="login-account"]')) as HTMLButtonElement[];

    it('shows the remembered accounts instead of asking for the email', async () => {
      accounts.set([ana, beto]);
      await create();

      expect(element('login-accounts')).not.toBeNull();
      expect(element('login-email-form')).toBeNull();
      expect(rows().map(row => row.textContent)).toEqual([jasmine.stringContaining('ana@x.com'), jasmine.stringContaining('beto@x.com')]);
    });

    it('asks for the email as before when no account is remembered', async () => {
      await create();

      expect(element('login-accounts')).toBeNull();
      expect(element('login-email-form')).not.toBeNull();
      expect(element('login-back-to-accounts')).toBeNull();
    });

    it('enters with a remembered account in one click, with no code, and goes where the person was heading', async () => {
      accounts.set([ana, beto]);
      volver = '/diagram/sala-9';
      await create();

      rows()[1].click();
      fixture.detectChanges();
      await fixture.whenStable();

      expect(resume).toHaveBeenCalledWith('beto@x.com');
      expect(requestCode).not.toHaveBeenCalled();
      expect(navigateByUrl).toHaveBeenCalledWith('/diagram/sala-9');
    });

    it('asks for a new code of that address when its session is over', async () => {
      accounts.set([ana, beto]);
      await create();
      resume.and.returnValue(throwError(() => new HttpErrorResponse({ status: 401 })));

      rows()[0].click();
      fixture.detectChanges();
      await fixture.whenStable();

      expect(element('login-email-form')).not.toBeNull();
      expect(input('login-email').value).toBe('ana@x.com');
      expect(element('login-error')!.textContent).toContain('venció');
      expect(navigateByUrl).not.toHaveBeenCalledWith('/');
    });

    it('says it could not enter now, and keeps the list, when the failure is not a finished session', async () => {
      accounts.set([ana]);
      await create();
      resume.and.returnValue(throwError(() => new HttpErrorResponse({ status: 500 })));

      rows()[0].click();
      fixture.detectChanges();
      await fixture.whenStable();

      expect(element('login-error')!.textContent).toContain('No pudimos entrar ahora');
      expect(element('login-accounts')).not.toBeNull();
    });

    it('goes straight on when the account chosen is the one already in use', async () => {
      accounts.set([ana, beto]);
      await create();
      active.set(ana);
      fixture.detectChanges();

      rows()[0].click();

      expect(resume).not.toHaveBeenCalled();
      expect(navigateByUrl).toHaveBeenCalledWith('/');
      expect(fixture.nativeElement.textContent).toContain('Cuenta actual');
    });

    it('lets the person use another email, and come back to the list', async () => {
      accounts.set([ana]);
      await create();

      element('login-add-account')!.click();
      fixture.detectChanges();
      expect(element('login-email-form')).not.toBeNull();
      expect(input('login-email').value).toBe('');

      element('login-back-to-accounts')!.click();
      fixture.detectChanges();
      expect(element('login-accounts')).not.toBeNull();
    });

    it('removes an account from the list of this browser', async () => {
      accounts.set([ana, beto]);
      await create();

      (element('login-account-forget') as HTMLButtonElement).click();
      fixture.detectChanges();

      expect(forgetAccount).toHaveBeenCalledWith('ana@x.com');
      expect(rows().length).toBe(1);
    });

    it('stays on the page when asked to change account even if there is a session', async () => {
      config = signal<AuthConfig | null>({ authRequired: true, mailConfigured: true });
      loggedIn = signal(true);
      cambiar = '1';
      accounts.set([ana, beto]);
      navigateByUrl = jasmine.createSpy('navigateByUrl').and.resolveTo(true);
      TestBed.configureTestingModule({
        imports: [LoginPage],
        providers: [
          provideZonelessChangeDetection(),
          { provide: AuthService, useValue: { config, loggedIn, session: signal(ana), accounts, ensureConfig: () => of(config()), requestCode, verify } },
          { provide: Router, useValue: { navigateByUrl } },
          { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: { get: (key: string) => (key === 'cambiar' ? '1' : null) } } } }
        ]
      });

      const page = TestBed.createComponent(LoginPage);
      page.detectChanges();

      expect(navigateByUrl).not.toHaveBeenCalled();
      expect(page.nativeElement.querySelector('[data-testid="login-accounts"]')).not.toBeNull();
    });
  });

  it('says that no password is needed', async () => {
    await create();

    expect(fixture.nativeElement.textContent).toContain('No hay contraseñas');
  });
});
