import { Component, inject } from '@angular/core';
import { CollaborationService } from '../../services/colaboration/collaboration.service';
import { P2PService } from '../../services/colaboration/p2p.service';

@Component({
  selector: 'app-participants-panel',
  standalone: true,
  templateUrl: './participants-panel.html'
})
export class ParticipantsPanel {
  private readonly p2p = inject(P2PService);
  private readonly collab = inject(CollaborationService);

  readonly participants = this.p2p.participants;
  readonly isHost = this.p2p.isHost;
  /** La IA es un integrante fijo de la sala; aquí se ve cuándo trabaja y para quién. */
  readonly iaStatus = this.collab.iaStatus;

  isCurrent(peer: string) {
    return this.p2p.isCurrentParticipant(peer);
  }

  remove(peer: string) {
    this.p2p.removeParticipant(peer);
  }
}
