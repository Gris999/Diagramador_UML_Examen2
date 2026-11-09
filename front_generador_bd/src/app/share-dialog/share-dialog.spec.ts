import { HttpErrorResponse } from '@angular/common/http';
import { provideZonelessChangeDetection, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Observable, of, throwError } from 'rxjs';
import { AuthConfig, AuthService } from '../../services/auth/auth.service';
import { InviteResult, InviteService } from '../../services/colaboration/invite.service';
import { ShareDialog } from './share-dialog';

describe('ShareDialog', () => {
  let fixture: ComponentFixture<ShareDialog>;
  let writeText: jasmine.Spy;
  let sendInvites: jasmine.Spy<(room: string, emails: string[], message: string) => Observable<InviteResult>>;
  let authConfig: ReturnType<typeof signal<AuthConfig | null>>;
  const ROOM = '3f2c1b7e-9a4d-4c55-8e21-0b6f7d9a1c42';

  const element = (testId: string) => fixture.nativeElement.querySelector(`[data-testid="${testId}"]`) as HTMLElement | null;
  const input = (testId: string) => element(testId) as HTMLInputElement;

  async function create(roomId = ROOM): Promise<void> {
    sendInvites = jasmine.createSpy('send').and.returnValue(of({ sent: [], failed: [] }));
    authConfig = signal<AuthConfig | null>({ authRequired: false, mailConfigured: true });
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        { provide: InviteService, useValue: { send: sendInvites } },
        { provide: AuthService, useValue: { config: authConfig, ensureConfig: () => of(authConfig()) } }
      ]
    });
    fixture = TestBed.createComponent(ShareDialog);
    fixture.componentRef.setInput('roomId', roomId);
    await fixture.whenStable();
  }

  beforeEach(() => {
    writeText = jasmine.createSpy('writeText').and.resolveTo();
    spyOn(navigator.clipboard, 'writeText').and.callFake(writeText as never);
  });

  it('shows the link to invite someone to edit, the code of the room and the link to follow it from a phone', async () => {
    await create();

    expect(input('share-invite-link').value).toBe(`${window.location.origin}/diagram/${ROOM}`);
    expect(input('share-follow-link').value).toBe(`${window.location.origin}/sala/${ROOM}/seguir`);
    expect(element('copy-room-code')!.textContent).toContain('Copiar código de sala');
    expect(element('copy-follow-link')!.textContent).toContain('Copiar enlace para seguir desde el celular');
  });

  it('encodes a room code that has special characters inside the links', async () => {
    await create('sala de prueba/1');

    expect(input('share-invite-link').value).toContain('/diagram/sala%20de%20prueba%2F1');
    expect(input('share-follow-link').value).toContain('/sala/sala%20de%20prueba%2F1/seguir');
  });

  it('copies each thing with its own button', async () => {
    await create();

    element('copy-invite-link')!.click();
    await fixture.whenStable();
    element('copy-room-code')!.click();
    await fixture.whenStable();
    element('copy-follow-link')!.click();
    await fixture.whenStable();

    expect(writeText.calls.allArgs().map(args => args[0])).toEqual([
      `${window.location.origin}/diagram/${ROOM}`,
      ROOM,
      `${window.location.origin}/sala/${ROOM}/seguir`
    ]);
  });

  it('says «¡Copiado!» on the button that was used and goes back to normal after a moment', async () => {
    jasmine.clock().install();
    try {
      await create();

      element('copy-invite-link')!.click();
      await Promise.resolve();
      await Promise.resolve();
      fixture.detectChanges();

      expect(element('copy-invite-link')!.textContent).toContain('¡Copiado!');
      expect(element('copy-room-code')!.textContent).not.toContain('¡Copiado!');

      jasmine.clock().tick(2100);
      fixture.detectChanges();

      expect(element('copy-invite-link')!.textContent).toContain('Copiar enlace de invitación');
    } finally {
      jasmine.clock().uninstall();
    }
  });

  it('does not claim it copied when the browser refuses and the old method fails too', async () => {
    writeText.and.rejectWith(new Error('sin permiso'));
    spyOn(document, 'execCommand').and.returnValue(false);
    await create();

    element('copy-invite-link')!.click();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(element('copy-invite-link')!.textContent).not.toContain('¡Copiado!');
  });

  it('closes with the close button, with Escape and by tapping the dark background, but not by tapping inside', async () => {
    await create();
    const closed = jasmine.createSpy('closed');
    fixture.componentInstance.closed.subscribe(closed);

    element('share-close')!.click();
    expect(closed).toHaveBeenCalledTimes(1);

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(closed).toHaveBeenCalledTimes(2);

    element('share-dialog')!.click();
    expect(closed).toHaveBeenCalledTimes(3);

    input('share-invite-link').click();
    expect(closed).toHaveBeenCalledTimes(3);
  });

  it('is announced to assistive technology as a modal dialog with a title', async () => {
    await create();

    const dialog = element('share-dialog')!;
    expect(dialog.getAttribute('role')).toBe('dialog');
    expect(dialog.getAttribute('aria-modal')).toBe('true');
    expect(document.getElementById(dialog.getAttribute('aria-labelledby')!)!.textContent).toContain('Compartir la sala');
  });

  describe('invite by email', () => {
    async function writeEmails(text: string, note = ''): Promise<void> {
      const emails = input('invite-emails');
      emails.value = text;
      emails.dispatchEvent(new Event('input'));
      if (note) {
        const message = element('invite-message') as HTMLTextAreaElement;
        message.value = note;
        message.dispatchEvent(new Event('input'));
      }
      fixture.detectChanges();
      await fixture.whenStable();
    }

    async function pressSend(): Promise<void> {
      element('invite-send')!.click();
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    }

    it('does not let the person send until there is a valid address', async () => {
      await create();

      expect((element('invite-send') as HTMLButtonElement).disabled).toBeTrue();
      await writeEmails('sinarroba');
      expect((element('invite-send') as HTMLButtonElement).disabled).toBeTrue();
      await writeEmails('beto@x.com');
      expect((element('invite-send') as HTMLButtonElement).disabled).toBeFalse();
    });

    it('asks the server to mail the room link to every valid address, with the note', async () => {
      await create();
      sendInvites.and.returnValue(of({ sent: ['beto@x.com', 'luis@x.com'], failed: [] }));
      await writeEmails('Beto@X.com, luis@x.com; beto@x.com', 'Ven a modelar');

      await pressSend();

      expect(sendInvites).toHaveBeenCalledOnceWith(ROOM, ['beto@x.com', 'luis@x.com'], 'Ven a modelar');
      expect(element('invite-result')!.textContent).toContain('Invitación enviada a beto@x.com, luis@x.com');
      expect(input('invite-emails').value).toBe('');
    });

    it('points at the address that does not look right instead of sending', async () => {
      await create();
      await writeEmails('beto@x.com, malo@');

      await pressSend();

      expect(sendInvites).not.toHaveBeenCalled();
      expect(element('invite-result')!.textContent).toContain('«malo@»');
    });

    it('says which ones could not be sent and keeps what was typed', async () => {
      await create();
      sendInvites.and.returnValue(of({ sent: ['a@x.com'], failed: ['b@x.com'] }));
      await writeEmails('a@x.com, b@x.com');

      await pressSend();

      expect(element('invite-result')!.textContent).toContain('Enviada a a@x.com');
      expect(element('invite-result')!.textContent).toContain('No se pudo enviar a: b@x.com');
      expect(input('invite-emails').value).toContain('b@x.com');
    });

    it('shows the reason the server gives, for example too many invitations', async () => {
      await create();
      sendInvites.and.returnValue(throwError(() => new HttpErrorResponse({ status: 429, error: { error: 'Mandaste muchas invitaciones. Espera un rato.' } })));
      await writeEmails('a@x.com');

      await pressSend();

      expect(element('invite-result')!.textContent).toContain('Mandaste muchas invitaciones');
      expect((element('invite-send') as HTMLButtonElement).disabled).toBeFalse();
    });

    it('has a generic message when the server gives no reason', async () => {
      await create();
      sendInvites.and.returnValue(throwError(() => new HttpErrorResponse({ status: 500 })));
      await writeEmails('a@x.com');

      await pressSend();

      expect(element('invite-result')!.textContent).toContain('No pudimos mandar las invitaciones');
    });

    it('blocks a second press while the first is still being sent', async () => {
      await create();
      sendInvites.and.returnValue(new Observable<InviteResult>(() => undefined));
      await writeEmails('a@x.com');

      await pressSend();
      expect((element('invite-send') as HTMLButtonElement).disabled).toBeTrue();
      element('invite-send')!.click();

      expect(sendInvites).toHaveBeenCalledTimes(1);
    });

    it('offers the person\'s own mail app when the server cannot send mail', async () => {
      await create();
      authConfig.set({ authRequired: false, mailConfigured: false });
      fixture.detectChanges();
      await writeEmails('beto@x.com, luis@x.com', 'Ven');

      const link = element('invite-mailto') as HTMLAnchorElement;
      expect(element('invite-send')).toBeNull();
      expect(link.getAttribute('href')).toContain('mailto:beto@x.com,luis@x.com?subject=');
      const body = decodeURIComponent(link.getAttribute('href')!.split('body=')[1]);
      expect(body).toContain(`${window.location.origin}/diagram/${ROOM}`);
      expect(body).toContain('Ven');
    });

    it('falls back to the mail app when the server answers that it cannot send mail', async () => {
      await create();
      sendInvites.and.returnValue(throwError(() => new HttpErrorResponse({ status: 503, error: { error: 'x' } })));
      await writeEmails('beto@x.com');

      await pressSend();

      expect(element('invite-result')!.textContent).toContain('todavía no puede mandar correos');
      expect(element('invite-mailto')).not.toBeNull();
      expect(element('invite-send')).toBeNull();
    });

    it('limits the note to 300 characters', async () => {
      await create();

      expect((element('invite-message') as HTMLTextAreaElement).maxLength).toBe(300);
    });
  });
});
