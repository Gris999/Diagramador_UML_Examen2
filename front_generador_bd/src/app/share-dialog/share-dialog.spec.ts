import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ShareDialog } from './share-dialog';

describe('ShareDialog', () => {
  let fixture: ComponentFixture<ShareDialog>;
  let writeText: jasmine.Spy;
  const ROOM = '3f2c1b7e-9a4d-4c55-8e21-0b6f7d9a1c42';

  const element = (testId: string) => fixture.nativeElement.querySelector(`[data-testid="${testId}"]`) as HTMLElement | null;
  const input = (testId: string) => element(testId) as HTMLInputElement;

  async function create(roomId = ROOM): Promise<void> {
    TestBed.configureTestingModule({ providers: [provideZonelessChangeDetection()] });
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
});
