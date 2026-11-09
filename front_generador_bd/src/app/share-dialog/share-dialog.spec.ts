import { HttpErrorResponse } from '@angular/common/http';
import { provideZonelessChangeDetection, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Observable, of, throwError } from 'rxjs';
import { AuthConfig, AuthService } from '../../services/auth/auth.service';
import { RoomAccess, RoomAccessService } from '../../services/auth/room-access.service';
import { InviteResult, InviteService } from '../../services/colaboration/invite.service';
import { ShareDialog } from './share-dialog';

const OWNER_INFO: RoomAccess = {
  required: true, email: 'ana@x.com', role: 'owner', is_owner: true, can_edit: true, title: 'Mi modelo',
  link_access: 'restricted', link_role: 'viewer', owner: 'ana@x.com',
  members: [{ email: 'ana@x.com', role: 'owner' }, { email: 'beto@x.com', role: 'editor' }]
};

describe('ShareDialog', () => {
  let fixture: ComponentFixture<ShareDialog>;
  let writeText: jasmine.Spy;
  let sendInvites: jasmine.Spy<(room: string, emails: string[], message: string, role?: string) => Observable<InviteResult>>;
  let updateSettings: jasmine.Spy;
  let setMemberRole: jasmine.Spy;
  let removeMember: jasmine.Spy;
  let authConfig: ReturnType<typeof signal<AuthConfig | null>>;
  let loadInfo: jasmine.Spy<(room: string) => Observable<RoomAccess>>;
  const ROOM = '3f2c1b7e-9a4d-4c55-8e21-0b6f7d9a1c42';

  const element = (testId: string) => fixture.nativeElement.querySelector(`[data-testid="${testId}"]`) as HTMLElement | null;
  const input = (testId: string) => element(testId) as HTMLInputElement;

  async function create(roomId = ROOM): Promise<void> {
    sendInvites = jasmine.createSpy('send').and.returnValue(of({ sent: [], failed: [] }));
    authConfig = signal<AuthConfig | null>({ authRequired: false, mailConfigured: true });
    loadInfo = jasmine.createSpy('info').and.returnValue(of(OWNER_INFO));
    updateSettings = jasmine.createSpy('updateSettings').and.callFake(() => of(OWNER_INFO));
    setMemberRole = jasmine.createSpy('setMemberRole').and.callFake(() => of(OWNER_INFO));
    removeMember = jasmine.createSpy('removeMember').and.callFake(() => of(OWNER_INFO));
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        { provide: InviteService, useValue: { send: sendInvites } },
        { provide: AuthService, useValue: { config: authConfig, ensureConfig: () => of(authConfig()) } },
        { provide: RoomAccessService, useValue: { info: loadInfo, updateSettings, setMemberRole, removeMember } }
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

      expect(sendInvites).toHaveBeenCalledOnceWith(ROOM, ['beto@x.com', 'luis@x.com'], 'Ven a modelar', 'editor');
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

  describe('with accounts: roles and general access, like Google Docs', () => {
    async function withAccounts(info: RoomAccess = OWNER_INFO, failure?: Observable<RoomAccess>): Promise<void> {
      await create();
      loadInfo.and.returnValue(failure ?? of(info));
      authConfig.set({ authRequired: true, mailConfigured: true });
      fixture.componentInstance.ngOnInit();
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    }

    const rows = () => Array.from(fixture.nativeElement.querySelectorAll('[data-testid="share-member"]')) as HTMLElement[];
    const pick = (testId: string, value: string) => {
      const select = element(testId) as HTMLSelectElement;
      select.value = value;
      select.dispatchEvent(new Event('change'));
      fixture.detectChanges();
    };

    it('names the diagram in the title and does not offer the link or the code while the access is restricted', async () => {
      await withAccounts();

      expect(element('share-title')!.textContent).toContain('Compartir «Mi modelo»');
      expect(element('share-invite-link')).toBeNull();
      expect(element('copy-invite-link')).toBeNull();
      expect(element('copy-room-code')).toBeNull();
      expect(element('share-general-note')!.textContent).toContain('El enlace por sí solo no abre el diagrama');
    });

    it('lists the people with access, the owner first, with their role', async () => {
      await withAccounts();

      expect(rows().length).toBe(2);
      expect(rows()[0].textContent).toContain('ana@x.com');
      expect(rows()[0].textContent).toContain('Propietario');
      expect(rows()[1].textContent).toContain('beto@x.com');
      expect((rows()[1].querySelector('[data-testid="member-role"]') as HTMLSelectElement).value).toBe('editor');
    });

    it('invites with the role chosen: editor by default and viewer when it is chosen', async () => {
      await withAccounts();
      sendInvites.and.returnValue(of({ sent: ['eva@x.com'], failed: [], members: [...OWNER_INFO.members, { email: 'eva@x.com', role: 'viewer' }] }));
      const emails = input('invite-emails');
      emails.value = 'eva@x.com';
      emails.dispatchEvent(new Event('input'));
      pick('invite-role', 'viewer');

      element('invite-send')!.click();
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();

      expect(sendInvites).toHaveBeenCalledOnceWith(ROOM, ['eva@x.com'], '', 'viewer');
      expect(rows().length).toBe(3);
    });

    it('lets the owner change the role of someone and take them out', async () => {
      await withAccounts();

      pick('member-role', 'viewer');
      expect(setMemberRole).toHaveBeenCalledOnceWith(ROOM, 'beto@x.com', 'viewer');

      (element('member-remove') as HTMLButtonElement).click();
      expect(removeMember).toHaveBeenCalledOnceWith(ROOM, 'beto@x.com');
    });

    it('shows the list as the server left it after a change', async () => {
      await withAccounts();
      removeMember.and.returnValue(of({ ...OWNER_INFO, members: [{ email: 'ana@x.com', role: 'owner' }] }));

      (element('member-remove') as HTMLButtonElement).click();
      fixture.detectChanges();

      expect(rows().length).toBe(1);
    });

    it('says why a change was refused and keeps the list', async () => {
      await withAccounts();
      setMemberRole.and.returnValue(throwError(() => new HttpErrorResponse({ status: 403, error: { error: 'Solo el propietario puede hacer esto.' } })));

      pick('member-role', 'viewer');
      fixture.detectChanges();

      expect(element('share-settings-error')!.textContent).toContain('Solo el propietario');
      expect(rows().length).toBe(2);
    });

    it('lets the owner open the link for anyone, as viewer or as editor, and then the link can be copied', async () => {
      await withAccounts();

      pick('link-access', 'anyone');
      expect(updateSettings).toHaveBeenCalledOnceWith(ROOM, { link_access: 'anyone' });

      updateSettings.and.returnValue(of({ ...OWNER_INFO, link_access: 'anyone', link_role: 'viewer' }));
      pick('link-access', 'anyone');
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();

      expect(input('share-invite-link').value).toBe(`${window.location.origin}/diagram/${ROOM}`);
      expect(element('copy-invite-link')).not.toBeNull();
      expect(element('share-general-note')!.textContent).toContain('puede ver el diagrama');

      pick('link-role', 'editor');
      expect(updateSettings).toHaveBeenCalledWith(ROOM, { link_role: 'editor' });
    });

    it('says that with the link as editor anyone can edit', async () => {
      await withAccounts({ ...OWNER_INFO, link_access: 'anyone', link_role: 'editor' });

      expect(element('share-general-note')!.textContent).toContain('ver y editar');
      expect((element('link-role') as HTMLSelectElement).value).toBe('editor');
    });

    it('does not let someone who is not the owner change the people or the general access', async () => {
      await withAccounts({ ...OWNER_INFO, role: 'editor', is_owner: false, email: 'beto@x.com' });

      expect(element('member-role')).toBeNull();
      expect(element('member-remove')).toBeNull();
      expect(element('link-access')).toBeNull();
      expect(rows()[1].textContent).toContain('Editor');
      expect(element('share-add')).not.toBeNull();
    });

    it('does not let a viewer invite anyone', async () => {
      await withAccounts({ ...OWNER_INFO, role: 'viewer', is_owner: false, can_edit: false, email: 'eva@x.com' });

      expect(element('share-add')).toBeNull();
      expect(element('invite-send')).toBeNull();
      expect(element('share-viewer-note')!.textContent).toContain('solo de lectura');
    });

    it('still lets the person copy the link of the read-only view for their own phone', async () => {
      await withAccounts();

      expect(element('copy-follow-link')).not.toBeNull();
      expect(fixture.nativeElement.textContent).toContain('Entra con tu mismo correo');
    });

    it('keeps working if the information of the room cannot be loaded', async () => {
      await withAccounts(OWNER_INFO, throwError(() => new HttpErrorResponse({ status: 500 })));

      expect(rows().length).toBe(0);
      expect(element('share-email-box')).not.toBeNull();
    });
  });

  it('still offers the link and the code when the server does not control access', async () => {
    await create();

    expect(element('copy-invite-link')).not.toBeNull();
    expect(element('copy-room-code')).not.toBeNull();
    expect(element('share-restricted-note')).toBeNull();
    expect(element('share-members')).toBeNull();
    expect(element('invite-role')).toBeNull();
    expect(loadInfo).not.toHaveBeenCalled();
  });
});
