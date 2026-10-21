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

  it('asks in ask mode, sending the diagram and the participant token', () => {
    let reply = '';
    service.ask('sala 1', '¿Qué hizo Beto?', { classes: [] }).subscribe(value => (reply = value));

    const request = http.expectOne(`${base}ia/chat/`);
    expect(request.request.method).toBe('POST');
    expect(request.request.headers.get('X-Participant-Token')).toBe(token);
    expect(request.request.body).toEqual({
      mode: 'ask',
      message: '¿Qué hizo Beto?',
      uml: { classes: [] }
    });
    request.flush({ reply: 'Beto añadió la clase Pedido.' });

    expect(reply).toBe('Beto añadió la clase Pedido.');
  });
});
