import { HttpErrorResponse } from '@angular/common/http';
import { PLATFORM_ID, provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { Observable, of, Subject, throwError } from 'rxjs';
import { DiagramService } from '../../services/diagram/diagram.service';
import { IaChatMessage, IaChatService } from '../../services/IA/ia-chat.service';
import { IaChatPanel } from './ia-chat-panel';

describe('IaChatPanel', () => {
  let fixture: ComponentFixture<IaChatPanel>;
  let history: jasmine.Spy<(room: string) => Observable<IaChatMessage[]>>;
  let ask: jasmine.Spy<(room: string, message: string, uml: unknown) => Observable<string>>;

  const uml = { classes: [{ id: 'c1', name: 'Cliente' }], relationships: [] };

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

  async function type(text: string): Promise<void> {
    const input = element('[data-testid="ia-chat-input"]') as HTMLTextAreaElement;
    input.value = text;
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }

  beforeEach(async () => {
    history = jasmine.createSpy('history').and.returnValue(of([]));
    ask = jasmine.createSpy('ask').and.returnValue(of('Respuesta de la IA'));

    await TestBed.configureTestingModule({
      imports: [IaChatPanel],
      providers: [
        provideZonelessChangeDetection(),
        { provide: PLATFORM_ID, useValue: 'browser' },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => 'sala-1' } } } },
        { provide: IaChatService, useValue: { history, ask } },
        { provide: DiagramService, useValue: { exportToJson: () => uml } }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(IaChatPanel);
    fixture.detectChanges();
  });

  it('starts closed and does not load the history until it is opened', () => {
    expect(element('[data-testid="ia-chat-input"]')).toBeNull();
    expect(history).not.toHaveBeenCalled();
  });

  it('loads the own history when opened and shows it as text', async () => {
    history.and.returnValue(of([
      { id: 1, role: 'user', content: '<b>hola</b>', created_at: 'x' },
      { id: 2, role: 'ia', content: 'Hola, ¿en qué ayudo?', created_at: 'y' }
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

    expect(ask).toHaveBeenCalledOnceWith('sala-1', '¿Qué hizo Beto?', uml);
    const texts = elements('[data-testid="ia-chat-message"]').map(row => row.textContent!.trim());
    expect(texts).toEqual(['¿Qué hizo Beto?', 'Respuesta de la IA']);
    expect((element('[data-testid="ia-chat-input"]') as HTMLTextAreaElement).value).toBe('');
  });

  it('blocks a second question while waiting and shows the thinking state', async () => {
    const pending = new Subject<string>();
    ask.and.returnValue(pending);
    await openChat();
    await type('primera');
    (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(element('[data-testid="ia-chat-thinking"]')).not.toBeNull();
    await type('segunda');
    (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
    expect(ask).toHaveBeenCalledTimes(1);

    pending.next('lista');
    pending.complete();
    fixture.detectChanges();
    expect(element('[data-testid="ia-chat-thinking"]')).toBeNull();
  });

  it('shows a clear message when the AI fails and keeps the chat usable', async () => {
    ask.and.returnValue(throwError(() => new HttpErrorResponse({ status: 502 })));
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

    ask.and.returnValue(throwError(() => new HttpErrorResponse({ status: 403 })));
    await type('uno');
    (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(element('[data-testid="ia-chat-error"]')!.textContent).toContain('identificaste');

    ask.and.returnValue(throwError(() => new HttpErrorResponse({ status: 429 })));
    await type('dos');
    (element('[data-testid="ia-chat-send"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(element('[data-testid="ia-chat-error"]')!.textContent).toContain('Demasiadas preguntas');
  });

  it('keeps working when the history cannot be loaded', async () => {
    history.and.returnValue(throwError(() => new HttpErrorResponse({ status: 500 })));

    await openChat();

    expect(element('[data-testid="ia-chat-input"]')).not.toBeNull();
    expect(element('[data-testid="ia-chat-error"]')).toBeNull();
  });
});
