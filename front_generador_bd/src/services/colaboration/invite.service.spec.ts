import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../environments/environment';
import { IdentityService } from './identity.service';
import { InviteService, parseEmails } from './invite.service';

describe('parseEmails', () => {
  it('separates addresses written with commas, semicolons, spaces or new lines', () => {
    expect(parseEmails('a@x.com, b@x.com;c@x.com d@x.com\ne@x.com').valid).toEqual(['a@x.com', 'b@x.com', 'c@x.com', 'd@x.com', 'e@x.com']);
  });

  it('lowercases and drops repeated addresses', () => {
    expect(parseEmails('Ana@X.com, ana@x.com ANA@X.COM').valid).toEqual(['ana@x.com']);
  });

  it('keeps the invalid ones apart, so the person can fix them', () => {
    const { valid, invalid } = parseEmails('ana@x.com, sinarroba, otro@, @x.com, malo@x');

    expect(valid).toEqual(['ana@x.com']);
    expect(invalid).toEqual(['sinarroba', 'otro@', '@x.com', 'malo@x']);
  });

  it('does not accept lookalikes of an address', () => {
    for (const text of ['a@b..com', '<a@b.com>', 'a@@b.com', 'a@b.c']) {
      expect(parseEmails(text).valid).withContext(text).toEqual([]);
    }
  });

  it('gives nothing for an empty text', () => {
    expect(parseEmails('')).toEqual({ valid: [], invalid: [] });
    expect(parseEmails('  ,; ')).toEqual({ valid: [], invalid: [] });
  });
});

describe('InviteService', () => {
  let http: HttpTestingController;
  let service: InviteService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: IdentityService, useValue: { getIdentity: () => ({ token: 'token-1', name: 'Ana' }) } }
      ]
    });
    http = TestBed.inject(HttpTestingController);
    service = TestBed.inject(InviteService);
  });

  it('asks the server to mail the room link, as someone who is in the room', () => {
    let result: unknown;

    service.send('sala 1', ['b@x.com'], 'Ven').subscribe(value => (result = value));

    const request = http.expectOne(`${environment.endpoint_python}api/rooms/sala%201/invite/`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ emails: ['b@x.com'], message: 'Ven' });
    expect(request.request.headers.get('X-Participant-Token')).toBe('token-1');
    request.flush({ sent: ['b@x.com'], failed: [] });
    expect(result).toEqual({ sent: ['b@x.com'], failed: [] });
  });
});
