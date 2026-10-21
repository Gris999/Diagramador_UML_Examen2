import { computed, provideZonelessChangeDetection, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CollaborationService } from '../../services/colaboration/collaboration.service';
import { P2PService } from '../../services/colaboration/p2p.service';
import { ParticipantsPanel } from './participants-panel';

describe('ParticipantsPanel', () => {
  let fixture: ComponentFixture<ParticipantsPanel>;
  let participants: ReturnType<typeof signal<any[]>>;
  let localPeer: ReturnType<typeof signal<string>>;
  let removeParticipant: jasmine.Spy;
  let iaStatus: ReturnType<typeof signal<{ state: 'thinking' | 'idle'; by: string }>>;

  beforeEach(async () => {
    participants = signal<any[]>([]);
    localPeer = signal('peer-a');
    removeParticipant = jasmine.createSpy('removeParticipant');
    iaStatus = signal<{ state: 'thinking' | 'idle'; by: string }>({ state: 'idle', by: '' });
    const p2p = {
      participants,
      isHost: computed(() => participants().some(
        participant => participant.peer === localPeer()
          && participant.role === 'host'
      )),
      isCurrentParticipant: (peer: string) => peer === localPeer(),
      removeParticipant
    };

    await TestBed.configureTestingModule({
      imports: [ParticipantsPanel],
      providers: [
        provideZonelessChangeDetection(),
        { provide: P2PService, useValue: p2p },
        { provide: CollaborationService, useValue: { iaStatus } }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ParticipantsPanel);
  });

  it('shows host role, current client, and removal action to the host', () => {
    participants.set([
      { peer: 'peer-a', role: 'host' },
      { peer: 'peer-b', role: 'participant' }
    ]);
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent;
    const removeButton = fixture.nativeElement.querySelector(
      '[data-testid="remove-participant"]'
    ) as HTMLButtonElement;

    expect(text).toContain('Host');
    expect(text).toContain('Participantes (2)');
    expect(text).toContain('(Tú)');
    expect(removeButton.disabled).toBeFalse();

    removeButton.click();
    expect(removeParticipant).toHaveBeenCalledOnceWith('peer-b');
  });

  it('does not render an enabled removal action for a participant', () => {
    localPeer.set('peer-b');
    participants.set([
      { peer: 'peer-a', role: 'host' },
      { peer: 'peer-b', role: 'participant' }
    ]);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector(
      '[data-testid="remove-participant"]'
    )).toBeNull();
  });

  it('updates the UI when the current participant is promoted', () => {
    localPeer.set('peer-b');
    participants.set([
      { peer: 'peer-a', role: 'host' },
      { peer: 'peer-b', role: 'participant' }
    ]);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector(
      '[data-testid="remove-participant"]'
    )).toBeNull();

    participants.set([
      { peer: 'peer-b', role: 'host' },
      { peer: 'peer-c', role: 'participant' }
    ]);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Host');
    expect(fixture.nativeElement.querySelector(
      '[data-testid="remove-participant"]'
    )).not.toBeNull();
  });

  it('bounds and scrolls a long participant list', () => {
    participants.set(Array.from({ length: 12 }, (_, index) => ({
      peer: `peer-${index}`,
      role: index === 0 ? 'host' : 'participant'
    })));
    fixture.detectChanges();

    const list = fixture.nativeElement.querySelector(
      '[data-testid="participants-list"]'
    ) as HTMLElement;
    const entries = fixture.nativeElement.querySelectorAll(
      '[data-testid="participant-entry"]'
    );

    expect(fixture.nativeElement.textContent).toContain('Participantes (12)');
    expect(entries.length).toBe(12);
    expect(list.classList).toContain('max-h-48');
    expect(list.classList).toContain('overflow-y-auto');
  });

  it('shows supplied names and keeps the positional fallback for legacy members', () => {
    participants.set([
      { peer: 'peer-a', role: 'host', name: 'Ana' },
      { peer: 'peer-b', role: 'participant' }
    ]);
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent;
    expect(text).toContain('Ana');
    expect(text).toContain('Usuario 2');
    expect(text).toContain('(Tú)');
    expect(text).toContain('Host');
  });

  it('always lists the IA as a room member and shows who it is working for', () => {
    participants.set([{ peer: 'peer-a', role: 'host' }]);
    fixture.detectChanges();
    const status = () => fixture.nativeElement
      .querySelector('[data-testid="ia-participant-status"]').textContent.replace(/\s+/g, ' ').trim();

    expect(fixture.nativeElement.querySelector('[data-testid="ia-participant"]').textContent)
      .toContain('IA');
    expect(status()).toBe('Disponible');
    expect(fixture.nativeElement.textContent).toContain('Participantes (1)');

    iaStatus.set({ state: 'thinking', by: 'Ana' });
    fixture.detectChanges();

    expect(status()).toContain('Pensando (a pedido de Ana)');
  });
});
