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

  const element = (testId: string) => fixture.nativeElement.querySelector(`[data-testid="${testId}"]`) as HTMLElement | null;
  const input = (testId: string) => element(testId) as HTMLInputElement;

  async function create(authConfig: AuthConfig = { authRequired: true, mailConfigured: true }): Promise<void> {
    config = signal<AuthConfig | null>(authConfig);
    loggedIn = signal(false);
    requestCode = jasmine.createSpy('requestCode').and.returnValue(of(undefined));
    verify = jasmine.createSpy('verify').and.returnValue(of({ token: 't', email: 'ana@x.com', name: 'Ana' }));
    navigateByUrl = jasmine.createSpy('navigateByUrl').and.resolveTo(true);
    TestBed.configureTestingModule({
      imports: [LoginPage],
      providers: [
        provideZonelessChangeDetection(),
        {
          provide: AuthService,
          useValue: { config, loggedIn, ensureConfig: () => of(config()), requestCode, verify }
        },
        { provide: Router, useValue: { navigateByUrl } },
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: { get: () => volver } } } }
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

  beforeEach(() => (volver = null));

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
        { provide: AuthService, useValue: { config, loggedIn, ensureConfig: () => of(config()), requestCode, verify } },
        { provide: Router, useValue: { navigateByUrl } },
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: { get: () => null } } } }
      ]
    });

    TestBed.createComponent(LoginPage).detectChanges();

    expect(navigateByUrl).toHaveBeenCalledWith('/');
  });

  it('says that no password is needed', async () => {
    await create();

    expect(fixture.nativeElement.textContent).toContain('No hay contraseñas');
  });
});
