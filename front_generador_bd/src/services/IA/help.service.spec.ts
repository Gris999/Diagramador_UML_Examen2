import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { PLATFORM_ID, provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../environments/environment';
import { HELP_TOKEN_STORAGE_KEY, HelpMessage, HelpService } from './help.service';

describe('HelpService', () => {
  const url = `${environment.endpoint_python}api/ia/help/`;
  let http: HttpTestingController;

  function create(platform = 'browser'): HelpService {
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: PLATFORM_ID, useValue: platform }
      ]
    });
    http = TestBed.inject(HttpTestingController);
    return TestBed.inject(HelpService);
  }

  beforeEach(() => localStorage.removeItem(HELP_TOKEN_STORAGE_KEY));
  afterEach(() => {
    http.verify();
    localStorage.removeItem(HELP_TOKEN_STORAGE_KEY);
  });

  it('asks the help endpoint with the question and gives back only the reply', () => {
    const service = create();
    let reply: string | undefined;

    service.ask('¿Cómo creo una sala?', []).subscribe(value => (reply = value));

    const request = http.expectOne(url);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ message: '¿Cómo creo una sala?', history: [] });
    request.flush({ reply: 'Pulsa «Crear Nuevo Lienzo».' });
    expect(reply).toBe('Pulsa «Crear Nuevo Lienzo».');
  });

  it('identifies the person with an anonymous token that is created once and kept', () => {
    const service = create();
    service.ask('uno', []).subscribe();
    const first = http.expectOne(url);
    const token = first.request.headers.get('X-Help-Token')!;
    first.flush({ reply: 'ok' });

    expect(token).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
    expect(localStorage.getItem(HELP_TOKEN_STORAGE_KEY)).toBe(token);

    service.ask('dos', []).subscribe();
    const second = http.expectOne(url);
    expect(second.request.headers.get('X-Help-Token')).toBe(token);
    second.flush({ reply: 'ok' });
  });

  it('keeps using the token that is already stored in the browser', () => {
    const stored = '3b8f6a52-5d0a-4f6e-9a3c-1f0e7f2f9b11';
    localStorage.setItem(HELP_TOKEN_STORAGE_KEY, stored);
    const service = create();

    service.ask('hola', []).subscribe();

    const request = http.expectOne(url);
    expect(request.request.headers.get('X-Help-Token')).toBe(stored);
    request.flush({ reply: 'ok' });
  });

  it('replaces a stored token that is not valid', () => {
    localStorage.setItem(HELP_TOKEN_STORAGE_KEY, 'basura');
    const service = create();

    service.ask('hola', []).subscribe();

    const request = http.expectOne(url);
    expect(request.request.headers.get('X-Help-Token')).not.toBe('basura');
    request.flush({ reply: 'ok' });
  });

  it('sends only the last six messages of the conversation', () => {
    const service = create();
    const history: HelpMessage[] = Array.from({ length: 10 }, (_, n) => ({ role: n % 2 ? 'ia' : 'user', content: `m${n}` }));

    service.ask('hola', history).subscribe();

    const request = http.expectOne(url);
    expect(request.request.body.history.map((m: HelpMessage) => m.content)).toEqual(['m4', 'm5', 'm6', 'm7', 'm8', 'm9']);
    request.flush({ reply: 'ok' });
  });

  it('works when the browser does not let it store the token', () => {
    const service = create();
    spyOn(Storage.prototype, 'setItem').and.throwError('bloqueado');
    spyOn(Storage.prototype, 'getItem').and.throwError('bloqueado');

    service.ask('uno', []).subscribe();
    const first = http.expectOne(url);
    const token = first.request.headers.get('X-Help-Token');
    first.flush({ reply: 'ok' });
    service.ask('dos', []).subscribe();
    const second = http.expectOne(url);

    expect(token).toBeTruthy();
    expect(second.request.headers.get('X-Help-Token')).toBe(token);
    second.flush({ reply: 'ok' });
  });

  it('turns a reply without text into an empty one instead of breaking', () => {
    const service = create();
    let reply: string | undefined;

    service.ask('hola', []).subscribe(value => (reply = value));

    http.expectOne(url).flush({});
    expect(reply).toBe('');
  });

  it('passes server errors to whoever asked', () => {
    const service = create();
    let status: number | undefined;

    service.ask('hola', []).subscribe({ error: error => (status = error.status) });

    http.expectOne(url).flush({ error: 'Demasiadas preguntas seguidas.' }, { status: 429, statusText: 'Too Many Requests' });
    expect(status).toBe(429);
  });
});
