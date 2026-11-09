import { provideZonelessChangeDetection, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Observable, of, throwError } from 'rxjs';
import { AuthConfig, AuthService } from '../../services/auth/auth.service';
import { RoomAccess, RoomAccessService } from '../../services/auth/room-access.service';
import { RoomTitle } from './room-title';

describe('RoomTitle', () => {
  let fixture: ComponentFixture<RoomTitle>;
  let config: ReturnType<typeof signal<AuthConfig | null>>;
  let lastAccess: jasmine.Spy;
  let info: jasmine.Spy<(room: string) => Observable<RoomAccess>>;
  let updateSettings: jasmine.Spy;

  const OWNER: RoomAccess = { required: true, email: 'ana@x.com', role: 'owner', is_owner: true, can_edit: true, title: 'Tienda', members: [] };
  const element = (testId: string) => fixture.nativeElement.querySelector(`[data-testid="${testId}"]`) as HTMLElement | null;

  async function create(access: RoomAccess | null = OWNER, authRequired = true): Promise<void> {
    config = signal<AuthConfig | null>({ authRequired, mailConfigured: true });
    lastAccess = jasmine.createSpy('lastAccess').and.returnValue(access ?? undefined);
    info = jasmine.createSpy('info').and.returnValue(of(OWNER));
    updateSettings = jasmine.createSpy('updateSettings').and.callFake((_room: string, patch: { title?: string }) => of({ ...OWNER, title: patch.title ?? '' }));
    TestBed.configureTestingModule({
      imports: [RoomTitle],
      providers: [
        provideZonelessChangeDetection(),
        { provide: AuthService, useValue: { config, ensureConfig: () => of(config()) } },
        { provide: RoomAccessService, useValue: { lastAccess, info, updateSettings } }
      ]
    });
    fixture = TestBed.createComponent(RoomTitle);
    fixture.componentRef.setInput('roomId', 'sala-1');
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }

  async function type(text: string): Promise<void> {
    const field = element('room-title-input') as HTMLInputElement;
    field.value = text;
    field.dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }

  it('shows the name of the diagram and the role of the person', async () => {
    await create();

    expect(element('room-title-text')!.textContent).toContain('Tienda');
    expect(element('room-role')!.textContent).toContain('Propietario');
  });

  it('says "Sin título" while the diagram has no name', async () => {
    await create({ ...OWNER, title: '' });

    expect(element('room-title-text')!.textContent).toContain('Sin título');
  });

  it('shows nothing when the server works without accounts', async () => {
    await create(OWNER, false);

    expect(element('room-title')).toBeNull();
  });

  it('asks the server how the room is when the guard did not leave it known', async () => {
    await create(null);

    expect(info).toHaveBeenCalledOnceWith('sala-1');
    expect(element('room-title-text')!.textContent).toContain('Tienda');
  });

  it('does not let anyone but the owner rename it', async () => {
    await create({ ...OWNER, role: 'editor', is_owner: false });

    expect((element('room-title-text') as HTMLButtonElement).disabled).toBeTrue();
    expect(element('room-role')!.textContent).toContain('Editor');
    element('room-title-text')!.click();
    fixture.detectChanges();
    expect(element('room-title-input')).toBeNull();
  });

  it('lets the owner rename it and saves with Enter', async () => {
    await create();

    element('room-title-text')!.click();
    fixture.detectChanges();
    await type('Mi tienda');
    (element('room-title-input') as HTMLInputElement).dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    fixture.detectChanges();

    expect(updateSettings).toHaveBeenCalledOnceWith('sala-1', { title: 'Mi tienda' });
    expect(element('room-title-input')).toBeNull();
    expect(element('room-title-text')!.textContent).toContain('Mi tienda');
  });

  it('cancels with Escape without saving', async () => {
    await create();
    element('room-title-text')!.click();
    fixture.detectChanges();
    await type('Otro');

    (element('room-title-input') as HTMLInputElement).dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    fixture.detectChanges();

    expect(updateSettings).not.toHaveBeenCalled();
    expect(element('room-title-text')!.textContent).toContain('Tienda');
  });

  it('does not call the server when the name did not change', async () => {
    await create();
    element('room-title-text')!.click();
    fixture.detectChanges();

    (element('room-title-input') as HTMLInputElement).dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    fixture.detectChanges();

    expect(updateSettings).not.toHaveBeenCalled();
    expect(element('room-title-input')).toBeNull();
  });

  it('says so when the name could not be saved and stays in edit mode', async () => {
    await create();
    updateSettings.and.returnValue(throwError(() => new Error('falló')));
    element('room-title-text')!.click();
    fixture.detectChanges();
    await type('Nuevo');

    (element('room-title-input') as HTMLInputElement).dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    fixture.detectChanges();

    expect(element('room-title-error')!.textContent).toContain('No pudimos guardar');
    expect(element('room-title-input')).not.toBeNull();
  });
});
