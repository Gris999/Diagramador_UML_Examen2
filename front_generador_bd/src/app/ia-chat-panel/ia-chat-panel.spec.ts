import { HttpErrorResponse } from '@angular/common/http';
import { PLATFORM_ID, provideZonelessChangeDetection, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { Observable, of, Subject, throwError } from 'rxjs';
import { CollaborationService } from '../../services/colaboration/collaboration.service';
import { IdentityService } from '../../services/colaboration/identity.service';
import { IaActionsService } from '../../services/IA/ia-actions.service';
import { IaChatMessage, IaChatMode, IaChatResponse, IaChatService, IaProviderInfo } from '../../services/IA/ia-chat.service';
import { IaChatPanel } from './ia-chat-panel';

describe('IaChatPanel', () => {
  let fixture: ComponentFixture<IaChatPanel>;
  let history: jasmine.Spy<(room: string) => Observable<IaChatMessage[]>>;
  let roomProvider: jasmine.Spy<(room: string) => Observable<IaProviderInfo>>;
  let setRoomProvider: jasmine.Spy<(room: string, provider: string) => Observable<IaProviderInfo>>;
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

  const LOCAL: IaProviderInfo = {
    provider: 'ollama',
    label: 'IA local (qwen3.5:9b)',
    options: [
      { id: 'gemini', label: 'Nube (Gemini)', available: true },
      { id: 'ollama', label: 'Local (qwen3.5:9b)', available: true }
    ]
  };
  const CLOUD: IaProviderInfo = { ...LOCAL, provider: 'gemini', label: 'IA en la nube (Gemini)' };

  beforeEach(async () => {
    history = jasmine.createSpy('history').and.returnValue(of([]));
    roomProvider = jasmine.createSpy('roomProvider').and.returnValue(of(LOCAL));
    setRoomProvider = jasmine.createSpy('setRoomProvider').and.returnValue(of(CLOUD));
    request = jasmine.createSpy('request').and.returnValue(of({ reply: 'Respuesta de la IA' }));
    iaStatus = signal<{ state: 'thinking' | 'idle'; by: string }>({ state: 'idle', by: '' });

    await TestBed.configureTestingModule({
      imports: [IaChatPanel],
      providers: [
        provideZonelessChangeDetection(),
        { provide: PLATFORM_ID, useValue: 'browser' },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => 'sala-1' } } } },
        { provide: IaChatService, useValue: { history, roomProvider, setRoomProvider } },
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

    expect(request).toHaveBeenCalledOnceWith('sala-1', 'auto', '¿Qué hizo Beto?');
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

  it('has one single conversation: no tabs to pick ask, change or review', async () => {
    await openChat();

    expect(element('[data-testid="ia-mode-ask"]')).toBeNull();
    expect(element('[data-testid="ia-mode-change"]')).toBeNull();
    expect(element('[data-testid="ia-mode-review"]')).toBeNull();
    expect(element('[data-testid="ia-permission-hint"]')!.textContent).toContain('te pide permiso');
  });

  it('sends everything as one kind of message and lets the server decide what it is', async () => {
    await openChat();

    for (const text of ['agrega la clase Factura', 'revisa el diagrama', '¿Qué hizo Beto?']) {
      await type(text);
      (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
      fixture.detectChanges();
      await fixture.whenStable();
    }

    expect(request.calls.allArgs()).toEqual([
      ['sala-1', 'auto', 'agrega la clase Factura'],
      ['sala-1', 'auto', 'revisa el diagrama'],
      ['sala-1', 'auto', '¿Qué hizo Beto?']
    ]);
  });

  it('does not send an empty message', async () => {
    await openChat();

    expect((element('[data-testid="ia-chat-send"]') as HTMLButtonElement).disabled).toBeTrue();
    await type('   ');
    expect((element('[data-testid="ia-chat-send"]') as HTMLButtonElement).disabled).toBeTrue();
  });

  it('suggests what can be asked, including a change and a review', async () => {
    await openChat();

    const text = element('[data-testid="ia-chat-empty"]')!.textContent!;
    expect(text).toContain('¿Qué hizo Beto?');
    expect(text).toContain('Agrega una clase');
    expect(text).toContain('Revisa el diagrama');
  });

  describe('permission before changing the diagram', () => {
    const proposal: IaChatResponse = {
      reply: 'Esto es lo que haría:\n• Crear la clase Factura\n¿Lo aplico?',
      intent: 'change',
      proposal: { lines: ['Crear la clase Factura'], destructive: 0 }
    };

    async function propose(): Promise<void> {
      request.and.returnValue(of(proposal));
      await openChat();
      await type('agrega la clase Factura');
      (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    }

    it('shows what the AI would do and waits, with Apply and Discard buttons', async () => {
      await propose();

      expect(authorsAndTexts()[1][1]).toContain('Crear la clase Factura');
      expect(element('[data-testid="ia-proposal"]')!.textContent).toContain('espera tu permiso');
      expect(element('[data-testid="ia-proposal-apply"]')).not.toBeNull();
      expect(element('[data-testid="ia-proposal-discard"]')).not.toBeNull();
      expect(request).toHaveBeenCalledTimes(1);
    });

    it('warns when what is proposed also deletes things', async () => {
      request.and.returnValue(of({ ...proposal, proposal: { lines: ['Eliminar la clase Pedido'], destructive: 1 } }));
      await openChat();
      await type('elimina Pedido');
      (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();

      expect(element('[data-testid="ia-proposal"]')!.textContent).toContain('eliminar cosas');
    });

    it('applies only after the person presses Apply, saying yes in the conversation', async () => {
      await propose();
      request.and.returnValue(of({ reply: 'Listo, apliqué el cambio en el diagrama.', intent: 'confirm', changes: {} }));

      click('ia-proposal-apply');
      await fixture.whenStable();
      fixture.detectChanges();

      expect(request.calls.mostRecent().args).toEqual(['sala-1', 'auto', 'Sí, aplícalo']);
      expect(authorsAndTexts().slice(-2)).toEqual([['Ana', 'Sí, aplícalo'], ['IA', 'Listo, apliqué el cambio en el diagrama.']]);
      expect(element('[data-testid="ia-proposal"]')).toBeNull();
    });

    it('drops the proposal when the person presses Discard', async () => {
      await propose();
      request.and.returnValue(of({ reply: 'Listo, descarté la propuesta. No cambié el diagrama.', intent: 'discard' }));

      click('ia-proposal-discard');
      await fixture.whenStable();
      fixture.detectChanges();

      expect(request.calls.mostRecent().args).toEqual(['sala-1', 'auto', 'No, descártalo']);
      expect(element('[data-testid="ia-proposal"]')).toBeNull();
    });

    it('keeps the buttons when the person asks something else in the meantime', async () => {
      await propose();
      request.and.returnValue(of({ reply: 'Hay dos clases.', intent: 'ask' }));
      await type('¿Cuántas clases hay?');

      (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();

      expect(element('[data-testid="ia-proposal"]')).not.toBeNull();
    });

    it('closes the proposal when typing yes instead of pressing the button', async () => {
      await propose();
      request.and.returnValue(of({ reply: 'Listo.', intent: 'confirm', changes: {} }));
      await type('sí');

      (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();

      expect(element('[data-testid="ia-proposal"]')).toBeNull();
    });

    it('closes the proposal when the person asks to apply something directly', async () => {
      await propose();
      request.and.returnValue(of({ reply: 'Listo.', intent: 'change', changes: {} }));
      await type('agrega Venta directamente');

      (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();

      expect(element('[data-testid="ia-proposal"]')).toBeNull();
    });

    it('does not show buttons for an ordinary answer', async () => {
      request.and.returnValue(of({ reply: 'Hay dos clases.', intent: 'ask' }));
      await openChat();
      await type('¿Cuántas clases hay?');

      (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();

      expect(element('[data-testid="ia-proposal"]')).toBeNull();
    });
  });

  describe('model of the room', () => {
    it('shows which AI answers and the models the server has', async () => {
      await openChat();

      expect(roomProvider).toHaveBeenCalledWith('sala-1');
      expect(element('[data-testid="ia-provider"]')!.textContent).toContain('IA local (qwen3.5:9b)');
      expect(element('[data-testid="ia-model-gemini"]')!.textContent).toContain('Nube (Gemini)');
      expect(element('[data-testid="ia-model-ollama"]')!.textContent).toContain('Local (qwen3.5:9b)');
      expect(element('[data-testid="ia-model-ollama"]')!.getAttribute('aria-checked')).toBe('true');
      expect(element('[data-testid="ia-model-gemini"]')!.getAttribute('aria-checked')).toBe('false');
    });

    it('switches the model of the whole room when one is chosen', async () => {
      await openChat();

      click('ia-model-gemini');
      await fixture.whenStable();
      fixture.detectChanges();

      expect(setRoomProvider).toHaveBeenCalledOnceWith('sala-1', 'gemini');
      expect(element('[data-testid="ia-provider"]')!.textContent).toContain('IA en la nube (Gemini)');
      expect(element('[data-testid="ia-model-gemini"]')!.getAttribute('aria-checked')).toBe('true');
    });

    it('does nothing when the chosen model is the one already in use', async () => {
      await openChat();

      click('ia-model-ollama');

      expect(setRoomProvider).not.toHaveBeenCalled();
    });

    it('does not let anyone choose a model that this server does not have', async () => {
      roomProvider.and.returnValue(of({
        ...CLOUD,
        options: [
          { id: 'gemini', label: 'Nube (Gemini)', available: true },
          { id: 'ollama', label: 'Local (qwen3.5:9b)', available: false }
        ]
      }));

      await openChat();

      const local = element('[data-testid="ia-model-ollama"]') as HTMLButtonElement;
      expect(local.disabled).toBeTrue();
      expect(local.title).toContain('No está disponible');
      local.click();
      expect(setRoomProvider).not.toHaveBeenCalled();
    });

    it('explains why the model could not be changed and keeps the one in use', async () => {
      setRoomProvider.and.returnValue(throwError(() => new HttpErrorResponse({
        status: 409, error: { error: 'Ese modelo no está disponible en este servidor.' }
      })));
      await openChat();

      click('ia-model-gemini');
      await fixture.whenStable();
      fixture.detectChanges();

      expect(element('[data-testid="ia-chat-error"]')!.textContent).toContain('no está disponible');
      expect(element('[data-testid="ia-provider"]')!.textContent).toContain('IA local');
    });

    it('shows what the server says when the model was changed too many times in a row', async () => {
      setRoomProvider.and.returnValue(throwError(() => new HttpErrorResponse({
        status: 429, error: { error: 'Cambiaste el modelo muchas veces seguidas. Espera un momento.' }
      })));
      await openChat();

      click('ia-model-gemini');
      await fixture.whenStable();
      fixture.detectChanges();

      expect(element('[data-testid="ia-chat-error"]')!.textContent).toContain('muchas veces seguidas');
    });

    it('reads the model again when the AI finishes, in case someone else changed it', async () => {
      await openChat();
      roomProvider.and.returnValue(of(CLOUD));

      iaStatus.set({ state: 'thinking', by: 'Beto' });
      fixture.detectChanges();
      iaStatus.set({ state: 'idle', by: '' });
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();

      expect(element('[data-testid="ia-provider"]')!.textContent).toContain('IA en la nube (Gemini)');
    });

    it('keeps working when the model cannot be known', async () => {
      roomProvider.and.returnValue(throwError(() => new HttpErrorResponse({ status: 500 })));

      await openChat();

      expect(element('[data-testid="ia-provider"]')).toBeNull();
      expect(element('[data-testid="ia-chat-input"]')).not.toBeNull();
    });
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
