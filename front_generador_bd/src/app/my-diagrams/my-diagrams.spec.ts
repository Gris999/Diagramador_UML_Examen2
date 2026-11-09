import { HttpErrorResponse } from '@angular/common/http';
import { provideZonelessChangeDetection, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { Observable, of, throwError } from 'rxjs';
import { AuthService, Session } from '../../services/auth/auth.service';
import { MyRoom, RoomAccess, RoomAccessService } from '../../services/auth/room-access.service';
import { MyDiagrams, timeAgo } from './my-diagrams';

const HOUR = 3600_000;
const iso = (hoursAgo: number) => new Date(Date.now() - hoursAgo * HOUR).toISOString();

const MINE: MyRoom = { room: 'sala-a', title: 'Tienda', role: 'owner', owner: 'ana@x.com', link_access: 'restricted', created_at: iso(30), last_opened_at: iso(2) };
const INVITED: MyRoom = { room: 'sala-b', title: '', role: 'viewer', owner: 'beto@x.com', link_access: 'anyone', created_at: iso(100), last_opened_at: null };

describe('timeAgo', () => {
  it('says how long ago in plain Spanish', () => {
    const now = Date.parse('2026-11-09T12:00:00Z');
    const ago = (seconds: number) => new Date(now - seconds * 1000).toISOString();

    expect(timeAgo(ago(10), now)).toBe('ahora');
    expect(timeAgo(ago(5 * 60), now)).toBe('hace 5 min');
    expect(timeAgo(ago(3 * 3600), now)).toBe('hace 3 h');
    expect(timeAgo(ago(30 * 3600), now)).toBe('ayer');
    expect(timeAgo(ago(4 * 86400), now)).toBe('hace 4 d');
  });

  it('says nothing when the date is missing or unreadable', () => {
    expect(timeAgo(null)).toBe('');
    expect(timeAgo('no es fecha')).toBe('');
  });
});

describe('MyDiagrams', () => {
  let fixture: ComponentFixture<MyDiagrams>;
  let myRooms: jasmine.Spy<() => Observable<MyRoom[]>>;
  let updateSettings: jasmine.Spy;
  let deleteRoom: jasmine.Spy;
  let removeMember: jasmine.Spy;
  let navigate: jasmine.Spy;

  const element = (testId: string) => fixture.nativeElement.querySelector(`[data-testid="${testId}"]`) as HTMLElement | null;
  const all = (testId: string) => Array.from(fixture.nativeElement.querySelectorAll(`[data-testid="${testId}"]`)) as HTMLElement[];

  async function create(rooms: Observable<MyRoom[]> = of([MINE, INVITED])): Promise<void> {
    myRooms = jasmine.createSpy('myRooms').and.returnValue(rooms);
    updateSettings = jasmine.createSpy('updateSettings').and.callFake((_room: string, patch: { title?: string }) => of({ title: patch.title } as RoomAccess));
    deleteRoom = jasmine.createSpy('deleteRoom').and.returnValue(of(undefined));
    removeMember = jasmine.createSpy('removeMember').and.returnValue(of({ left: true }));
    navigate = jasmine.createSpy('navigate').and.resolveTo(true);
    TestBed.configureTestingModule({
      imports: [MyDiagrams],
      providers: [
        provideZonelessChangeDetection(),
        { provide: RoomAccessService, useValue: { myRooms, updateSettings, deleteRoom, removeMember } },
        { provide: AuthService, useValue: { session: signal<Session | null>({ token: 't', email: 'ana@x.com', name: 'Ana' }) } },
        { provide: Router, useValue: { navigate } }
      ]
    });
    fixture = TestBed.createComponent(MyDiagrams);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }

  it('shows each diagram with its name, its role and when it was opened', async () => {
    await create();

    const cards = all('diagram-card');
    expect(cards.length).toBe(2);
    expect(cards[0].querySelector('[data-testid="diagram-title"]')!.textContent).toContain('Tienda');
    expect(cards[0].querySelector('[data-testid="diagram-role"]')!.textContent).toContain('Propietario');
    expect(cards[0].querySelector('[data-testid="diagram-when"]')!.textContent).toContain('hace 2 h');
    expect(cards[0].querySelector('[data-testid="diagram-owner"]')).toBeNull();
    expect(cards[1].querySelector('[data-testid="diagram-title"]')!.textContent).toContain('Sin título');
    expect(cards[1].querySelector('[data-testid="diagram-role"]')!.textContent).toContain('Lector');
    expect(cards[1].querySelector('[data-testid="diagram-owner"]')!.textContent).toContain('De beto@x.com');
    expect(cards[1].querySelector('[data-testid="diagram-public"]')).not.toBeNull();
  });

  it('says there is nothing yet when the list is empty', async () => {
    await create(of([]));

    expect(element('diagrams-empty')!.textContent).toContain('Todavía no tienes diagramas');
    expect(all('diagram-card').length).toBe(0);
  });

  it('says it could not load when the server fails, and keeps the new-diagram button', async () => {
    await create(throwError(() => new HttpErrorResponse({ status: 500 })));

    expect(element('diagrams-error')!.textContent).toContain('No pudimos cargar tus diagramas');
    expect(element('new-diagram')).not.toBeNull();
  });

  it('creates a new diagram with a fresh code', async () => {
    await create();

    element('new-diagram')!.click();

    const [path, code] = navigate.calls.mostRecent().args[0] as [string, string];
    expect(path).toBe('/diagram');
    expect(code).toMatch(/^[0-9a-f-]{36}$/);
  });

  it('opens a diagram when its card is pressed', async () => {
    await create();

    (all('diagram-open')[1] as HTMLButtonElement).click();

    expect(navigate).toHaveBeenCalledOnceWith(['/diagram', 'sala-b']);
  });

  it('offers rename and delete only to the owner, and "quitar de mi lista" to the others', async () => {
    await create();

    (all('diagram-menu')[0] as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(element('diagram-rename')).not.toBeNull();
    expect(element('diagram-delete')).not.toBeNull();
    expect(element('diagram-leave')).toBeNull();

    (all('diagram-menu')[1] as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(element('diagram-rename')).toBeNull();
    expect(element('diagram-delete')).toBeNull();
    expect(element('diagram-leave')).not.toBeNull();
  });

  it('closes the menu with Escape', async () => {
    await create();
    (all('diagram-menu')[0] as HTMLButtonElement).click();
    fixture.detectChanges();

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    fixture.detectChanges();

    expect(element('diagram-menu-list')).toBeNull();
  });

  it('renames a diagram with the name the person types', async () => {
    await create();
    spyOn(window, 'prompt').and.returnValue('Mi tienda');
    (all('diagram-menu')[0] as HTMLButtonElement).click();
    fixture.detectChanges();

    element('diagram-rename')!.click();
    fixture.detectChanges();

    expect(updateSettings).toHaveBeenCalledOnceWith('sala-a', { title: 'Mi tienda' });
    expect(all('diagram-title')[0].textContent).toContain('Mi tienda');
  });

  it('does nothing when the person cancels the rename', async () => {
    await create();
    spyOn(window, 'prompt').and.returnValue(null);
    (all('diagram-menu')[0] as HTMLButtonElement).click();
    fixture.detectChanges();

    element('diagram-rename')!.click();

    expect(updateSettings).not.toHaveBeenCalled();
  });

  it('deletes a diagram only after the person confirms, and it leaves the list', async () => {
    await create();
    const confirm = spyOn(window, 'confirm').and.returnValue(true);
    (all('diagram-menu')[0] as HTMLButtonElement).click();
    fixture.detectChanges();

    element('diagram-delete')!.click();
    fixture.detectChanges();

    expect(confirm).toHaveBeenCalledOnceWith(jasmine.stringContaining('Tienda'));
    expect(deleteRoom).toHaveBeenCalledOnceWith('sala-a');
    expect(all('diagram-card').length).toBe(1);
  });

  it('keeps the diagram when the person does not confirm the deletion', async () => {
    await create();
    spyOn(window, 'confirm').and.returnValue(false);
    (all('diagram-menu')[0] as HTMLButtonElement).click();
    fixture.detectChanges();

    element('diagram-delete')!.click();

    expect(deleteRoom).not.toHaveBeenCalled();
    expect(all('diagram-card').length).toBe(2);
  });

  it('takes a diagram that is not mine off my list with my own address', async () => {
    await create();
    spyOn(window, 'confirm').and.returnValue(true);
    (all('diagram-menu')[1] as HTMLButtonElement).click();
    fixture.detectChanges();

    element('diagram-leave')!.click();
    fixture.detectChanges();

    expect(removeMember).toHaveBeenCalledOnceWith('sala-b', 'ana@x.com');
    expect(all('diagram-card').length).toBe(1);
  });

  it('says so when a deletion fails and keeps the diagram', async () => {
    await create();
    spyOn(window, 'confirm').and.returnValue(true);
    deleteRoom.and.returnValue(throwError(() => new HttpErrorResponse({ status: 403 })));
    (all('diagram-menu')[0] as HTMLButtonElement).click();
    fixture.detectChanges();

    element('diagram-delete')!.click();
    fixture.detectChanges();

    expect(element('diagrams-error')!.textContent).toContain('No pudimos eliminar');
    expect(all('diagram-card').length).toBe(2);
  });
});
