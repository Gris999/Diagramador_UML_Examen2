import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../environments/environment';
import { RoomAccess, RoomAccessService } from './room-access.service';

describe('RoomAccessService', () => {
  const base = `${environment.endpoint_python}api/rooms/`;
  const INFO: RoomAccess = { required: true, email: 'ana@x.com', role: 'owner', is_owner: true, can_edit: true, title: 'Uno', members: [] };
  let http: HttpTestingController;
  let service: RoomAccessService;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideZonelessChangeDetection(), provideHttpClient(), provideHttpClientTesting()] });
    http = TestBed.inject(HttpTestingController);
    service = TestBed.inject(RoomAccessService);
  });

  it('enters a room with POST and remembers what it said, so a guard can use the role', () => {
    service.enter('sala 1').subscribe();

    const request = http.expectOne(`${base}sala%201/access/`);
    expect(request.request.method).toBe('POST');
    request.flush(INFO);

    expect(service.lastAccess('sala 1')).toEqual(INFO);
    expect(service.lastAccess('otra')).toBeUndefined();
  });

  it('looks at a room with GET without claiming it', () => {
    service.info('sala-1').subscribe();

    const request = http.expectOne(`${base}sala-1/access/`);
    expect(request.request.method).toBe('GET');
    request.flush(INFO);
    expect(service.lastAccess('sala-1')?.title).toBe('Uno');
  });

  it('changes the name and the general access of the room', () => {
    service.updateSettings('sala-1', { title: 'Nuevo', link_access: 'anyone', link_role: 'editor' }).subscribe();

    const request = http.expectOne(`${base}sala-1/settings/`);
    expect(request.request.method).toBe('PUT');
    expect(request.request.body).toEqual({ title: 'Nuevo', link_access: 'anyone', link_role: 'editor' });
    request.flush({ ...INFO, title: 'Nuevo' });
    expect(service.lastAccess('sala-1')?.title).toBe('Nuevo');
  });

  it('changes the role of someone and takes someone out', () => {
    service.setMemberRole('sala-1', 'beto@x.com', 'viewer').subscribe();
    const put = http.expectOne(`${base}sala-1/members/`);
    expect(put.request.method).toBe('PUT');
    expect(put.request.body).toEqual({ email: 'beto@x.com', role: 'viewer' });
    put.flush(INFO);

    service.removeMember('sala-1', 'beto@x.com').subscribe();
    const del = http.expectOne(`${base}sala-1/members/`);
    expect(del.request.method).toBe('DELETE');
    expect(del.request.body).toEqual({ email: 'beto@x.com' });
    del.flush({ left: true });
  });

  it('deletes the room', () => {
    let done = false;
    service.deleteRoom('sala-1').subscribe(() => (done = true));

    const request = http.expectOne(`${base}sala-1/`);
    expect(request.request.method).toBe('DELETE');
    request.flush({ deleted: true });
    expect(done).toBeTrue();
  });

  it('lists my diagrams and gives an empty list when the answer has none', () => {
    let rooms: unknown;
    service.myRooms().subscribe(value => (rooms = value));
    http.expectOne(base).flush({ rooms: [{ room: 'a', title: 'A', role: 'owner' }] });
    expect(rooms).toEqual([{ room: 'a', title: 'A', role: 'owner' } as never]);

    service.myRooms().subscribe(value => (rooms = value));
    http.expectOne(base).flush({ required: false });
    expect(rooms).toEqual([]);
  });
});
