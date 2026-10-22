import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../environments/environment';
import { IdentityService } from '../colaboration/identity.service';
import { IaChatService } from './ia-chat.service';

describe('IaChatService', () => {
  let service: IaChatService;
  let http: HttpTestingController;
  const token = '3b8f6a52-5d0a-4f6e-9a3c-1f0e7f2f9b11';
  const base = `${environment.endpoint_python}api/rooms/sala%201/`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: IdentityService, useValue: { getIdentity: () => ({ token, name: 'Ana' }) } }
      ]
    });
    service = TestBed.inject(IaChatService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('loads only the messages the server returns for the participant token', () => {
    let result: unknown;
    service.history('sala 1').subscribe(messages => (result = messages));

    const request = http.expectOne(`${base}chat/?limit=50`);
    expect(request.request.method).toBe('GET');
    expect(request.request.headers.get('X-Participant-Token')).toBe(token);
    request.flush({ messages: [{ id: 1, role: 'user', content: 'hola', created_at: 'x' }] });

    expect(result).toEqual([{ id: 1, role: 'user', content: 'hola', created_at: 'x' }]);
  });

  it('returns an empty history when the response has no messages', () => {
    let result: unknown;
    service.history('sala 1').subscribe(messages => (result = messages));

    http.expectOne(`${base}chat/?limit=50`).flush({});

    expect(result).toEqual([]);
  });

  it('sends the mode, the message and the diagram with the participant token', () => {
    let result: unknown;
    service
      .send('sala 1', 'change', 'agrega Factura', { classes: [] })
      .subscribe(value => (result = value));

    const request = http.expectOne(`${base}ia/chat/`);
    expect(request.request.method).toBe('POST');
    expect(request.request.headers.get('X-Participant-Token')).toBe(token);
    expect(request.request.body).toEqual({
      mode: 'change',
      message: 'agrega Factura',
      uml: { classes: [] }
    });
    request.flush({ reply: 'Listo', changes: { classes: [] } });

    expect(result).toEqual({ reply: 'Listo', changes: { classes: [] } });
  });

  it('fails with a timeout instead of waiting forever for the IA', () => {
    jasmine.clock().install();
    try {
      let failure: unknown;
      service.send('sala 1', 'ask', 'hola', null).subscribe({ error: error => (failure = error) });
      http.expectOne(`${base}ia/chat/`);

      jasmine.clock().tick(110_001);

      expect((failure as Error).name).toBe('TimeoutError');
    } finally {
      jasmine.clock().uninstall();
    }
  });

  it('asks which provider answers without needing the participant token', () => {
    let info: unknown;
    service.provider().subscribe(value => (info = value));

    const request = http.expectOne(`${environment.endpoint_python}api/ia/provider/`);
    expect(request.request.headers.has('X-Participant-Token')).toBeFalse();
    request.flush({ provider: 'gemini', label: 'IA en la nube (Gemini)' });

    expect(info).toEqual({ provider: 'gemini', label: 'IA en la nube (Gemini)' });
  });

  it('claims a suggestion with the participant token and releases it with DELETE', () => {
    service.claimSuggestion('sala 1', 7, 2).subscribe();
    const claim = http.expectOne(`${base}activity/7/apply/2/`);
    expect(claim.request.method).toBe('POST');
    expect(claim.request.headers.get('X-Participant-Token')).toBe(token);
    claim.flush({});

    service.confirmSuggestion('sala 1', 7, 2).subscribe();
    const confirm = http.expectOne(`${base}activity/7/apply/2/`);
    expect(confirm.request.method).toBe('PUT');
    expect(confirm.request.headers.get('X-Participant-Token')).toBe(token);
    confirm.flush({});

    service.releaseSuggestion('sala 1', 7, 2).subscribe();
    const release = http.expectOne(`${base}activity/7/apply/2/`);
    expect(release.request.method).toBe('DELETE');
    expect(release.request.headers.get('X-Participant-Token')).toBe(token);
    release.flush({});
  });
});
