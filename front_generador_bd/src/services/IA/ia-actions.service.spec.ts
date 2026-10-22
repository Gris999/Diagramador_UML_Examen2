import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { defer, of, Subject, throwError } from 'rxjs';
import { CollaborationService } from '../colaboration/collaboration.service';
import { IdentityService } from '../colaboration/identity.service';
import { DiagramService } from '../diagram/diagram.service';
import { IaActionsService } from './ia-actions.service';
import { IaChatService } from './ia-chat.service';

describe('IaActionsService', () => {
  let service: IaActionsService;
  let send: jasmine.Spy;
  let claimSuggestion: jasmine.Spy;
  let releaseSuggestion: jasmine.Spy;
  let confirmSuggestion: jasmine.Spy;
  let loadFromJson: jasmine.Spy;
  let startIaRequest: jasmine.Spy;
  let finishIaRequest: jasmine.Spy;
  let appliedWhileMarked: boolean[];
  const uml = { classes: [{ id: 'c1', name: 'Cliente' }], relationships: [] };

  beforeEach(() => {
    send = jasmine.createSpy('send');
    claimSuggestion = jasmine.createSpy('claimSuggestion').and.returnValue(of({}));
    releaseSuggestion = jasmine.createSpy('releaseSuggestion').and.returnValue(of({}));
    confirmSuggestion = jasmine.createSpy('confirmSuggestion').and.returnValue(of({}));
    appliedWhileMarked = [];
    let marked = false;
    loadFromJson = jasmine.createSpy('loadFromJson').and.callFake(() => appliedWhileMarked.push(marked));
    startIaRequest = jasmine.createSpy('startIaRequest').and.returnValue('req-1');
    finishIaRequest = jasmine.createSpy('finishIaRequest');

    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        { provide: IaChatService, useValue: { send, claimSuggestion, releaseSuggestion, confirmSuggestion } },
        { provide: DiagramService, useValue: { exportToJson: () => uml, loadFromJson } },
        {
          provide: CollaborationService,
          useValue: {
            startIaRequest,
            finishIaRequest,
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
    expect(startIaRequest).toHaveBeenCalledOnceWith('Ana');
    expect(finishIaRequest).not.toHaveBeenCalled();

    pending.next({ reply: 'hola' });
    pending.complete();
    expect(finishIaRequest).toHaveBeenCalledOnceWith('req-1');
  });

  it('reports the request as finished when it fails or is abandoned', () => {
    send.and.returnValue(throwError(() => new Error('502')));
    service.request('sala', 'change', 'x').subscribe({ error: () => undefined });
    expect(finishIaRequest).toHaveBeenCalledOnceWith('req-1');
    expect(loadFromJson).not.toHaveBeenCalled();

    finishIaRequest.calls.reset();
    send.and.returnValue(new Subject());
    service.request('sala', 'ask', 'y').subscribe().unsubscribe();
    expect(finishIaRequest).toHaveBeenCalledOnceWith('req-1');
  });

  it('applies the changes of change mode marked as IA', () => {
    const changes = { classes: [{ name: 'Factura' }] };
    send.and.returnValue(of({ reply: 'Listo', changes, destructive: 0 }));

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

  it('asks for confirmation before applying a change that deletes things, and applies it if accepted', () => {
    const confirm = spyOn(window, 'confirm').and.returnValue(true);
    const changes = { classes: [{ name: 'Pedido', eliminar: true }] };
    send.and.returnValue(of({ reply: 'Listo', changes, destructive: 1 }));

    service.request('sala', 'change', 'quita Pedido').subscribe();

    expect(confirm).toHaveBeenCalledOnceWith(jasmine.stringContaining('eliminar 1 elemento del diagrama'));
    expect(loadFromJson).toHaveBeenCalledOnceWith(changes, true);
  });

  it('leaves the diagram alone and says so when the user refuses a destructive change', () => {
    spyOn(window, 'confirm').and.returnValue(false);
    send.and.returnValue(of({ reply: 'Listo', changes: { classes: [{ name: 'A', eliminar: true }] }, destructive: 3 }));
    let response: any;

    service.request('sala', 'change', 'borra todo').subscribe(value => (response = value));

    expect(loadFromJson).not.toHaveBeenCalled();
    expect(response.cancelled).toBeTrue();
    expect(response.changes).toBeUndefined();
    expect(response.reply).toContain('Cancelaste el cambio');
  });

  it('claims a suggestion before applying it, as a change request on behalf of the clicker', () => {
    send.and.returnValue(of({ reply: 'Listo', changes: { classes: [] }, destructive: 0 }));
    let reply = '';

    service.applySuggestion('sala', 12, 1, 'agrega id a Cliente').subscribe(value => (reply = value));

    expect(claimSuggestion).toHaveBeenCalledOnceWith('sala', 12, 1);
    expect(send).toHaveBeenCalledOnceWith('sala', 'change', 'agrega id a Cliente', uml);
    expect(releaseSuggestion).not.toHaveBeenCalled();
    expect(reply).toBe('Listo');
  });

  it('confirms the suggestion once the change reached the diagram, and not before', () => {
    const pending = new Subject<{ reply: string; changes: unknown; destructive: number }>();
    send.and.returnValue(pending);
    service.applySuggestion('sala', 12, 1, 'agrega id a Cliente').subscribe();

    expect(confirmSuggestion).not.toHaveBeenCalled();
    pending.next({ reply: 'Listo', changes: { classes: [] }, destructive: 0 });
    pending.complete();

    expect(loadFromJson).toHaveBeenCalledTimes(1);
    expect(confirmSuggestion).toHaveBeenCalledOnceWith('sala', 12, 1);
  });

  it('never confirms a suggestion whose change failed or was refused', () => {
    send.and.returnValue(throwError(() => new Error('502')));
    service.applySuggestion('sala', 12, 1, 'x').subscribe({ error: () => undefined });

    spyOn(window, 'confirm').and.returnValue(false);
    send.and.returnValue(of({ reply: 'x', changes: { classes: [{ eliminar: true }] }, destructive: 1 }));
    service.applySuggestion('sala', 12, 2, 'y').subscribe();

    expect(confirmSuggestion).not.toHaveBeenCalled();
  });

  describe('when the network fails while closing the reservation', () => {
    beforeEach(() => jasmine.clock().install());
    afterEach(() => jasmine.clock().uninstall());

    it('retries the confirmation instead of leaving the idea reserved', () => {
      let attempts = 0;
      // Como un pedido HTTP, cada suscripción vuelve a intentarlo.
      confirmSuggestion.and.returnValue(defer(() =>
        ++attempts < 3 ? throwError(() => new Error('red')) : of({})));
      send.and.returnValue(of({ reply: 'Listo', changes: { classes: [] }, destructive: 0 }));

      service.applySuggestion('sala', 12, 1, 'x').subscribe();
      jasmine.clock().tick(5000);

      expect(attempts).toBe(3);
    });

    it('retries the release when the change fails', () => {
      let attempts = 0;
      releaseSuggestion.and.returnValue(defer(() =>
        ++attempts < 2 ? throwError(() => new Error('red')) : of({})));
      send.and.returnValue(throwError(() => new Error('502')));

      service.applySuggestion('sala', 12, 1, 'x').subscribe({ error: () => undefined });
      jasmine.clock().tick(5000);

      expect(attempts).toBe(2);
    });

    it('gives up quietly after a few attempts', () => {
      let attempts = 0;
      confirmSuggestion.and.returnValue(defer(() => {
        attempts++;
        return throwError(() => new Error('red'));
      }));
      send.and.returnValue(of({ reply: 'Listo', changes: { classes: [] }, destructive: 0 }));
      let failure: unknown;

      service.applySuggestion('sala', 12, 1, 'x').subscribe({ error: error => (failure = error) });
      jasmine.clock().tick(10_000);

      expect(attempts).toBe(3);
      expect(failure).toBeUndefined();
    });
  });

  it('does not ask the IA anything when somebody else already took the suggestion', () => {
    claimSuggestion.and.returnValue(throwError(() => ({ status: 409 })));
    let failure: any;

    service.applySuggestion('sala', 12, 1, 'x').subscribe({ error: error => (failure = error) });

    expect(failure.status).toBe(409);
    expect(send).not.toHaveBeenCalled();
    expect(releaseSuggestion).not.toHaveBeenCalled();
  });

  it('releases the suggestion if the change fails or is refused', () => {
    send.and.returnValue(throwError(() => new Error('502')));
    service.applySuggestion('sala', 12, 1, 'x').subscribe({ error: () => undefined });
    expect(releaseSuggestion).toHaveBeenCalledOnceWith('sala', 12, 1);

    releaseSuggestion.calls.reset();
    spyOn(window, 'confirm').and.returnValue(false);
    send.and.returnValue(of({ reply: 'x', changes: { classes: [{ eliminar: true }] }, destructive: 1 }));
    service.applySuggestion('sala', 12, 2, 'y').subscribe();
    expect(releaseSuggestion).toHaveBeenCalledOnceWith('sala', 12, 2);
  });
});
