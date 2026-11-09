import { provideZonelessChangeDetection, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService, Session } from '../../services/auth/auth.service';
import { AccessDeniedPage } from './access-denied-page';

describe('AccessDeniedPage', () => {
  let fixture: ComponentFixture<AccessDeniedPage>;
  let logout: jasmine.Spy;
  let navigate: jasmine.Spy;
  let navigateByUrl: jasmine.Spy;
  let sala: string | null;

  const element = (testId: string) => fixture.nativeElement.querySelector(`[data-testid="${testId}"]`) as HTMLElement | null;

  async function create(): Promise<void> {
    logout = jasmine.createSpy('logout');
    navigate = jasmine.createSpy('navigate').and.resolveTo(true);
    navigateByUrl = jasmine.createSpy('navigateByUrl').and.resolveTo(true);
    TestBed.configureTestingModule({
      imports: [AccessDeniedPage],
      providers: [
        provideZonelessChangeDetection(),
        { provide: AuthService, useValue: { session: signal<Session | null>({ token: 't', email: 'beto@x.com', name: 'Beto' }), logout } },
        { provide: Router, useValue: { navigate, navigateByUrl } },
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: { get: () => sala } } } }
      ]
    });
    fixture = TestBed.createComponent(AccessDeniedPage);
    fixture.detectChanges();
    await fixture.whenStable();
  }

  beforeEach(() => (sala = 'sala-1'));

  it('says the person has no invitation and with which address they entered', async () => {
    await create();

    expect(element('access-denied-title')!.textContent).toContain('No tienes invitación');
    expect(element('access-denied-email')!.textContent).toContain('beto@x.com');
  });

  it('lets them change account: it logs out and comes back to the same room after entering with another address', async () => {
    await create();

    element('access-denied-change')!.click();

    expect(logout).toHaveBeenCalledTimes(1);
    expect(navigate).toHaveBeenCalledOnceWith(['/entrar'], { queryParams: { volver: '/diagram/sala-1' } });
  });

  it('changes account without a remembered room when there is none', async () => {
    sala = null;
    await create();

    element('access-denied-change')!.click();

    expect(navigate).toHaveBeenCalledOnceWith(['/entrar'], {});
  });

  it('can go back to the start page', async () => {
    await create();

    element('access-denied-home')!.click();

    expect(navigateByUrl).toHaveBeenCalledOnceWith('/');
    expect(logout).not.toHaveBeenCalled();
  });
});
