import { of, Subject, throwError } from 'rxjs';
import { IaActionsService } from './ia-actions.service';
import { IaChatService } from './ia-chat.service';
import { CollaborationService } from '../colaboration/collaboration.service';
import { IdentityService } from '../colaboration/identity.service';
import { DiagramService } from '../diagram/diagram.service';
import { TestBed } from '@angular/core/testing';
import { provideZonelessChangeDetection } from '@angular/core';

describe('IaActionsService', () => {
  let service: IaActionsService;
  let send: jasmine.Spy;
  let loadFromJson: jasmine.Spy;
  let setIaStatus: jasmine.Spy;
  let markSuggestionApplied: jasmine.Spy;
  let appliedWhileMarked: boolean[];
  const uml = { classes: [{ id: 'c1', name: 'Cliente' }], relationships: [] };

  beforeEach(() => {
    send = jasmine.createSpy('send');
    appliedWhileMarked = [];
    let marked = false;
    loadFromJson = jasmine.createSpy('loadFromJson').and.callFake(() => appliedWhileMarked.push(marked));
    setIaStatus = jasmine.createSpy('setIaStatus');
    markSuggestionApplied = jasmine.createSpy('markSuggestionApplied');

    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        { provide: IaChatService, useValue: { send } },
        { provide: DiagramService, useValue: { exportToJson: () => uml, loadFromJson } },
        {
          provide: CollaborationService,
          useValue: {
            setIaStatus,
            markSuggestionApplied,
            runAsIa: (action: () => unknown) => {
              marked = true;
              try {
                return action();
              } finally {
                marked = false;
              }
            }
          }
        },
        { provide: IdentityService, useValue: { getIdentity: () => ({ token: 't', name: 'Ana' }) } }
      ]
    });
    service = TestBed.inject(IaActionsService);
  });

  it('sends the current diagram and announces that the IA is working for the requester', () => {
    const pending = new Subject<{ reply: string }>();
    send.and.returnValue(pending);

    service.request('sala', 'ask', '¿qué hay?').subscribe();

    expect(send).toHaveBeenCalledOnceWith('sala', 'ask', '¿qué hay?', uml);
    expect(setIaStatus).toHaveBeenCalledOnceWith('thinking', 'Ana');

    pending.next({ reply: 'hola' });
    pending.complete();
    expect(setIaStatus).toHaveBeenCalledWith('idle', '');
  });

  it('applies the changes of change mode marked as IA', () => {
    const changes = { classes: [{ name: 'Factura' }] };
    send.and.returnValue(of({ reply: 'Listo', changes }));

    service.request('sala', 'change', 'agrega Factura').subscribe();

    expect(loadFromJson).toHaveBeenCalledOnceWith(changes, true);
    expect(appliedWhileMarked).toEqual([true]);
  });

  it('never touches the diagram in ask or review mode, even if the server returned one', () => {
    send.and.returnValue(of({ reply: 'x', changes: { classes: [{ name: 'Intrusa' }] } }));

    service.request('sala', 'ask', 'a').subscribe();
    service.request('sala', 'review', 'b').subscribe();

    expect(loadFromJson).not.toHaveBeenCalled();
  });

  it('reports the IA as idle again when the request fails', () => {
    send.and.returnValue(throwError(() => new Error('502')));
    let failed = false;

    service.request('sala', 'change', 'x').subscribe({ error: () => (failed = true) });

    expect(failed).toBeTrue();
    expect(setIaStatus).toHaveBeenCalledWith('idle', '');
    expect(loadFromJson).not.toHaveBeenCalled();
  });

  it('applies a suggestion as a change request and marks it as applied for everyone', () => {
    send.and.returnValue(of({ reply: 'Listo', changes: { classes: [] } }));
    let reply = '';

    service.applySuggestion('sala', 12, 1, 'agrega id a Cliente').subscribe(value => (reply = value));

    expect(send).toHaveBeenCalledOnceWith('sala', 'change', 'agrega id a Cliente', uml);
    expect(markSuggestionApplied).toHaveBeenCalledOnceWith(12, 1);
    expect(reply).toBe('Listo');
  });

  it('does not mark a suggestion as applied when the change fails', () => {
    send.and.returnValue(throwError(() => new Error('502')));

    service.applySuggestion('sala', 12, 1, 'x').subscribe({ error: () => undefined });

    expect(markSuggestionApplied).not.toHaveBeenCalled();
  });
});
