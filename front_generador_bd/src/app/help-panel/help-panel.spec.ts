import { HttpErrorResponse } from '@angular/common/http';
import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Observable, of, Subject, throwError } from 'rxjs';
import { HelpMessage, HelpService } from '../../services/IA/help.service';
import { HelpPanel } from './help-panel';

describe('HelpPanel', () => {
  let fixture: ComponentFixture<HelpPanel>;
  let ask: jasmine.Spy<(message: string, history: HelpMessage[]) => Observable<string>>;

  function element(testId: string): HTMLElement | null {
    return (fixture.nativeElement as HTMLElement).querySelector(`[data-testid="${testId}"]`);
  }

  function lines(): string[][] {
    return Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('[data-testid="help-message"]')).map(row => [
      row.querySelector('[data-testid="help-author"]')!.textContent!.trim(),
      row.querySelector('p')!.textContent!.trim()
    ]);
  }

  function open(): void {
    element('help-toggle')!.click();
    fixture.detectChanges();
  }

  function type(text: string): void {
    const input = element('help-input') as HTMLTextAreaElement;
    input.value = text;
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }

  function send(): void {
    element('help-send')!.click();
    fixture.detectChanges();
  }

  beforeEach(async () => {
    ask = jasmine.createSpy('ask').and.returnValue(of('Pulsa «Crear Nuevo Lienzo».'));
    await TestBed.configureTestingModule({
      imports: [HelpPanel],
      providers: [provideZonelessChangeDetection(), { provide: HelpService, useValue: { ask } }]
    }).compileComponents();
    fixture = TestBed.createComponent(HelpPanel);
    fixture.detectChanges();
  });

  it('starts closed with only the help button', () => {
    expect(element('help-toggle')!.textContent).toContain('Ayuda');
    expect(element('help-input')).toBeNull();
  });

  it('opens and closes with the button, and says it is personal', () => {
    open();
    expect(element('help-input')).not.toBeNull();
    expect(element('help-private')!.textContent).toContain('Solo tú ves');

    element('help-close')!.click();
    fixture.detectChanges();
    expect(element('help-input')).toBeNull();
  });

  it('shows example questions before there is any conversation', () => {
    open();

    expect(element('help-empty')!.textContent).toContain('¿Cómo');
  });

  it('shows the question and the answer, with who said each', () => {
    open();
    type('¿Cómo creo una sala?');
    send();

    expect(ask).toHaveBeenCalledOnceWith('¿Cómo creo una sala?', []);
    expect(lines()).toEqual([
      ['Tú', '¿Cómo creo una sala?'],
      ['Ayuda', 'Pulsa «Crear Nuevo Lienzo».']
    ]);
    expect((element('help-input') as HTMLTextAreaElement).value).toBe('');
  });

  it('sends the earlier messages with the next question so the assistant keeps the thread', () => {
    open();
    type('¿Cómo creo una sala?');
    send();
    type('¿Y cómo invito a alguien?');
    send();

    expect(ask.calls.mostRecent().args).toEqual([
      '¿Y cómo invito a alguien?',
      [
        { role: 'user', content: '¿Cómo creo una sala?' },
        { role: 'ia', content: 'Pulsa «Crear Nuevo Lienzo».' }
      ]
    ]);
  });

  it('keeps the conversation when the panel is closed and opened again', () => {
    open();
    type('hola');
    send();
    element('help-close')!.click();
    fixture.detectChanges();

    open();

    expect(lines().length).toBe(2);
  });

  it('shows that it is thinking and does not send a second question meanwhile', () => {
    const pending = new Subject<string>();
    ask.and.returnValue(pending);
    open();
    type('primera');
    send();

    expect(element('help-thinking')).not.toBeNull();
    expect((element('help-send') as HTMLButtonElement).disabled).toBeTrue();
    type('segunda');
    send();
    expect(ask).toHaveBeenCalledTimes(1);

    pending.next('respuesta');
    pending.complete();
    fixture.detectChanges();
    expect(element('help-thinking')).toBeNull();
  });

  it('does not send an empty question', () => {
    open();
    type('   ');

    expect((element('help-send') as HTMLButtonElement).disabled).toBeTrue();
    send();
    expect(ask).not.toHaveBeenCalled();
  });

  it('sends with Enter and breaks the line with Shift+Enter', () => {
    open();
    type('hola');
    const input = element('help-input') as HTMLTextAreaElement;

    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true }));
    expect(ask).not.toHaveBeenCalled();

    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    expect(ask).toHaveBeenCalledTimes(1);
  });

  it('explains the wait when the person asked too many questions', () => {
    ask.and.returnValue(throwError(() => new HttpErrorResponse({ status: 429 })));
    open();
    type('hola');
    send();

    expect(element('help-error')!.textContent).toContain('Demasiadas preguntas seguidas');
    expect(element('help-thinking')).toBeNull();
  });

  it('shows a clear message when the AI cannot answer and keeps what the person wrote visible', () => {
    ask.and.returnValue(throwError(() => new HttpErrorResponse({ status: 502 })));
    open();
    type('hola');
    send();

    expect(element('help-error')!.textContent).toContain('La IA no pudo responder ahora');
    expect(lines()).toEqual([['Tú', 'hola']]);
  });

  it('clears the error when the person asks again', () => {
    ask.and.returnValues(throwError(() => new HttpErrorResponse({ status: 502 })), of('ahora sí'));
    open();
    type('hola');
    send();
    type('hola otra vez');
    send();

    expect(element('help-error')).toBeNull();
    expect(lines().pop()).toEqual(['Ayuda', 'ahora sí']);
  });

  it('refuses a question that is too long without calling the server', () => {
    open();
    type('x'.repeat(2001));
    send();

    expect(ask).not.toHaveBeenCalled();
    expect(element('help-error')!.textContent).toContain('2000');
  });
});
