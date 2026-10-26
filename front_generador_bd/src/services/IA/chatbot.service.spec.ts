import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../environments/environment';
import { ChatbotService } from './chatbot.service';

describe('ChatbotService', () => {
  let service: ChatbotService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideZonelessChangeDetection(), provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(ChatbotService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('only transcribes the dictated instruction: the model is not built from the audio', () => {
    let result: unknown;
    service.transcribeAudio(new Blob(['audio'], { type: 'audio/webm;codecs=opus' })).subscribe(response => (result = response));

    const request = http.expectOne(`${environment.endpoint_python}api/uml_from_audio/`);
    expect(request.request.method).toBe('POST');
    const form = request.request.body as FormData;
    expect(form.get('transcribe_only')).toBe('1');
    expect((form.get('audio') as File).name).toBe('instruccion-uml.webm');
    request.flush({ transcript: 'agrega una clase Factura' });

    expect(result).toEqual({ transcript: 'agrega una clase Factura' });
  });

  it('names an ogg recording with the ogg extension', () => {
    service.transcribeAudio(new Blob(['audio'], { type: 'audio/ogg' })).subscribe();

    const request = http.expectOne(`${environment.endpoint_python}api/uml_from_audio/`);
    expect(((request.request.body as FormData).get('audio') as File).name).toBe('instruccion-uml.ogg');
    request.flush({ transcript: 'x' });
  });
});
