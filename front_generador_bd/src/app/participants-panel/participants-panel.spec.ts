import { computed, provideZonelessChangeDetection, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { P2PService } from '../../services/colaboration/p2p.service';
import { ParticipantsPanel } from './participants-panel';

describe('ParticipantsPanel', () => {
  let fixture: ComponentFixture<ParticipantsPanel>;
  let participants: ReturnType<typeof signal<any[]>>;
  let localPeer: ReturnType<typeof signal<string>>;
  let removeParticipant: jasmine.Spy;

  beforeEach(async () => {
    participants = signal<any[]>([]);
    localPeer = signal('peer-a');
    removeParticipant = jasmine.createSpy('removeParticipant');
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
        { provide: P2PService, useValue: p2p }
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
});
