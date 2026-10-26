import { HttpErrorResponse } from '@angular/common/http';
import { PLATFORM_ID, provideZonelessChangeDetection, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { Observable, of, Subject, throwError } from 'rxjs';
import { CollaborationService } from '../../services/colaboration/collaboration.service';
import { IdentityService } from '../../services/colaboration/identity.service';
import { IaActionsService } from '../../services/IA/ia-actions.service';
import { IaChatMessage, IaChatMode, IaChatResponse, IaChatService } from '../../services/IA/ia-chat.service';
import { IaChatPanel } from './ia-chat-panel';

describe('IaChatPanel', () => {
  let fixture: ComponentFixture<IaChatPanel>;
  let history: jasmine.Spy<(room: string) => Observable<IaChatMessage[]>>;
  let provider: jasmine.Spy<() => Observable<{ provider: string; label: string }>>;
  let request: jasmine.Spy<(room: string, mode: IaChatMode, message: string) => Observable<IaChatResponse>>;
  let iaStatus: ReturnType<typeof signal<{ state: 'thinking' | 'idle'; by: string }>>;

  function element(selector: string): HTMLElement | null {
    return (fixture.nativeElement as HTMLElement).querySelector(selector);
  }

  function elements(selector: string): HTMLElement[] {
    return Array.from((fixture.nativeElement as HTMLElement).querySelectorAll(selector));
  }

  async function openChat(): Promise<void> {
    element('[data-testid="ia-chat-toggle"]')!.click();
    fixture.detectChanges();
    await fixture.whenStable();
  }

  function authorsAndTexts(): string[][] {
    return elements('[data-testid="ia-chat-message"]').map(row => [
      row.querySelector('[data-testid="ia-chat-author"]')!.textContent!.trim(),
      row.querySelector('p')!.textContent!.trim()
    ]);
  }

  function click(testId: string): void {
    element(`[data-testid="${testId}"]`)!.click();
    fixture.detectChanges();
  }

  async function type(text: string): Promise<void> {
    const input = element('[data-testid="ia-chat-input"]') as HTMLTextAreaElement;
    input.value = text;
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }

  beforeEach(async () => {
    history = jasmine.createSpy('history').and.returnValue(of([]));
    provider = jasmine.createSpy('provider').and.returnValue(of({ provider: 'ollama', label: 'IA local (qwen3.5:9b)' }));
    request = jasmine.createSpy('request').and.returnValue(of({ reply: 'Respuesta de la IA' }));
    iaStatus = signal<{ state: 'thinking' | 'idle'; by: string }>({ state: 'idle', by: '' });

    await TestBed.configureTestingModule({
      imports: [IaChatPanel],
      providers: [
        provideZonelessChangeDetection(),
        { provide: PLATFORM_ID, useValue: 'browser' },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => 'sala-1' } } } },
        { provide: IaChatService, useValue: { history, provider } },
        { provide: IaActionsService, useValue: { request } },
        { provide: IdentityService, useValue: { getIdentity: () => ({ token: 't', name: 'Ana' }) } },
        { provide: CollaborationService, useValue: { iaStatus } }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(IaChatPanel);
    fixture.detectChanges();
  });

  it('starts closed and does not load the history until it is opened', () => {
    expect(element('[data-testid="ia-chat-input"]')).toBeNull();
    expect(history).not.toHaveBeenCalled();
  });

  it('loads the conversation of the room when opened and shows it as text', async () => {
    history.and.returnValue(of([
      { id: 1, role: 'user', author_name: 'Ana', content: '<b>hola</b>', created_at: 'x' },
      { id: 2, role: 'ia', author_name: 'IA', content: 'Hola, ¿en qué ayudo?', created_at: 'y' }
    ]));

    await openChat();

    expect(history).toHaveBeenCalledOnceWith('sala-1');
    const rows = elements('[data-testid="ia-chat-message"]');
    expect(rows.length).toBe(2);
    expect(rows[0].textContent).toContain('<b>hola</b>');
    expect(rows[0].querySelector('b')).toBeNull();
  });

  it('sends the question with the current diagram and shows the reply', async () => {
    await openChat();
    await type('  ¿Qué hizo Beto?  ');

    (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(request).toHaveBeenCalledOnceWith('sala-1', 'ask', '¿Qué hizo Beto?');
    expect(authorsAndTexts()).toEqual([['Ana', '¿Qué hizo Beto?'], ['IA', 'Respuesta de la IA']]);
    expect((element('[data-testid="ia-chat-input"]') as HTMLTextAreaElement).value).toBe('');
  });

  it('blocks a second question while waiting and shows the thinking state', async () => {
    const pending = new Subject<IaChatResponse>();
    request.and.returnValue(pending);
    await openChat();
    await type('primera');
    (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(element('[data-testid="ia-chat-thinking"]')).not.toBeNull();
    await type('segunda');
    (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
    expect(request).toHaveBeenCalledTimes(1);

    pending.next({ reply: 'lista' });
    pending.complete();
    fixture.detectChanges();
    expect(element('[data-testid="ia-chat-thinking"]')).toBeNull();
  });

  it('shows a clear message when the AI fails and keeps the chat usable', async () => {
    request.and.returnValue(throwError(() => new HttpErrorResponse({ status: 502 })));
    await openChat();
    await type('hola');

    (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(element('[data-testid="ia-chat-error"]')!.textContent)
      .toContain('La IA no pudo responder ahora');
    expect(element('[data-testid="ia-chat-thinking"]')).toBeNull();
    expect((element('[data-testid="ia-chat-send"]') as HTMLButtonElement).disabled).toBeTrue();
  });

  it('explains when the participant is not identified or is throttled', async () => {
    await openChat();

    request.and.returnValue(throwError(() => new HttpErrorResponse({ status: 403 })));
    await type('uno');
    (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(element('[data-testid="ia-chat-error"]')!.textContent).toContain('identificaste');

    request.and.returnValue(throwError(() => new HttpErrorResponse({ status: 429 })));
    await type('dos');
    (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(element('[data-testid="ia-chat-error"]')!.textContent).toContain('Demasiadas preguntas');
  });

  it('starts in ask mode and explains what each mode does', async () => {
    await openChat();

    expect(element('[data-testid="ia-mode-hint"]')!.textContent).toContain('solo responde');
    click('ia-mode-change');
    expect(element('[data-testid="ia-mode-hint"]')!.textContent).toContain('modifica el diagrama');
    click('ia-mode-review');
    expect(element('[data-testid="ia-mode-hint"]')!.textContent).toContain('publica sus ideas');
  });

  it('sends the selected mode with the message', async () => {
    await openChat();
    click('ia-mode-change');
    await type('agrega la clase Factura');

    (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(request).toHaveBeenCalledOnceWith('sala-1', 'change', 'agrega la clase Factura');
  });

  it('lets the user ask for a review without typing anything', async () => {
    await openChat();
    click('ia-mode-review');
    fixture.detectChanges();
    const send = element('[data-testid="ia-chat-send"]') as HTMLButtonElement;

    expect(send.disabled).toBeFalse();
    send.click();
    fixture.detectChanges();

    expect(request).toHaveBeenCalledOnceWith('sala-1', 'review', 'Revisa el diagrama');
  });

  it('keeps ask and change from being sent empty', async () => {
    await openChat();

    expect((element('[data-testid="ia-chat-send"]') as HTMLButtonElement).disabled).toBeTrue();
    click('ia-mode-change');
    fixture.detectChanges();
    expect((element('[data-testid="ia-chat-send"]') as HTMLButtonElement).disabled).toBeTrue();
  });

  it('shows which AI answers (cloud or local model)', async () => {
    await openChat();

    expect(element('[data-testid="ia-provider"]')!.textContent).toContain('IA local (qwen3.5:9b)');
  });

  it('keeps working when the provider cannot be known', async () => {
    provider.and.returnValue(throwError(() => new HttpErrorResponse({ status: 500 })));

    await openChat();

    expect(element('[data-testid="ia-provider"]')).toBeNull();
    expect(element('[data-testid="ia-chat-input"]')).not.toBeNull();
  });

  it('does not let the user send until the history has loaded, so nothing is duplicated', async () => {
    const pending = new Subject<IaChatMessage[]>();
    history.and.returnValue(pending);
    await openChat();
    await type('hola');

    const send = element('[data-testid="ia-chat-send"]') as HTMLButtonElement;
    expect(send.disabled).toBeTrue();
    send.click();
    expect(request).not.toHaveBeenCalled();

    pending.next([{ id: 1, role: 'user', author_name: 'Ana', content: 'antes', created_at: 'x' }]);
    pending.complete();
    fixture.detectChanges();

    expect(send.disabled).toBeFalse();
    expect(elements('[data-testid="ia-chat-message"]').length).toBe(1);
  });

  it('allows sending when the history cannot be loaded', async () => {
    history.and.returnValue(throwError(() => new HttpErrorResponse({ status: 500 })));
    await openChat();
    await type('hola');

    expect((element('[data-testid="ia-chat-send"]') as HTMLButtonElement).disabled).toBeFalse();
  });

  it('keeps working when the history cannot be loaded', async () => {
    history.and.returnValue(throwError(() => new HttpErrorResponse({ status: 500 })));

    await openChat();

    expect(element('[data-testid="ia-chat-input"]')).not.toBeNull();
    expect(element('[data-testid="ia-chat-error"]')).toBeNull();
  });

  it('says that the conversation belongs to the whole room', async () => {
    await openChat();

    const text = (fixture.nativeElement as HTMLElement).textContent!;
    expect(text).toContain('Lo ven todas las personas de la sala');
    expect(text).not.toContain('Privado');
  });

  it('shows who wrote each message and tells mine from the others', async () => {
    history.and.returnValue(of([
      { id: 1, role: 'user', author_name: 'Beto', content: '¿Qué hizo Ana?', created_at: 'x' },
      { id: 2, role: 'ia', author_name: 'IA', content: 'Ana añadió Factura.', created_at: 'y' },
      { id: 3, role: 'user', author_name: 'Ana', content: 'Gracias', created_at: 'z' }
    ]));

    await openChat();

    const rows = elements('[data-testid="ia-chat-message"]');
    expect(rows.map(row => row.querySelector('[data-testid="ia-chat-author"]')!.textContent!.trim())).toEqual(['Beto', 'IA', 'Ana']);
    expect(rows[0].classList).not.toContain('justify-end');
    expect(rows[2].classList).toContain('justify-end');
  });

  it('reloads the conversation when the AI finishes working for someone else, so the room sees what the others asked', async () => {
    await openChat();
    expect(history).toHaveBeenCalledTimes(1);
    history.and.returnValue(of([
      { id: 1, role: 'user', author_name: 'Beto', content: 'pregunta de Beto', created_at: 'x' },
      { id: 2, role: 'ia', author_name: 'IA', content: 'respuesta para Beto', created_at: 'y' }
    ]));

    iaStatus.set({ state: 'thinking', by: 'Beto' });
    fixture.detectChanges();
    iaStatus.set({ state: 'idle', by: '' });
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(history).toHaveBeenCalledTimes(2);
    expect(authorsAndTexts()).toEqual([['Beto', 'pregunta de Beto'], ['IA', 'respuesta para Beto']]);
  });

  it('does not reload while the chat is closed', async () => {
    iaStatus.set({ state: 'thinking', by: 'Beto' });
    fixture.detectChanges();
    iaStatus.set({ state: 'idle', by: '' });
    fixture.detectChanges();
    await fixture.whenStable();

    expect(history).not.toHaveBeenCalled();
  });

  it('keeps what is on screen when the reload brings nothing', async () => {
    await openChat();
    await type('hola');
    (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    iaStatus.set({ state: 'thinking', by: 'Ana' });
    fixture.detectChanges();
    iaStatus.set({ state: 'idle', by: '' });
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(elements('[data-testid="ia-chat-message"]').length).toBe(2);
  });

  it('tells who is being served when the AI is busy with another person', async () => {
    request.and.returnValue(throwError(() => new HttpErrorResponse({
      status: 409, error: { error: 'La IA está atendiendo a Beto. Espera a que termine.' }
    })));
    await openChat();
    await type('hola');

    (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(element('[data-testid="ia-chat-error"]')!.textContent).toContain('La IA está atendiendo a Beto');
  });
});
