import { Component, inject } from '@angular/core';
import { CollaborationService } from '../../services/colaboration/collaboration.service';
import { P2PService } from '../../services/colaboration/p2p.service';
import { avatarColor, avatarInitial } from './avatar';

/** Lista de la sala que se abre desde la barra superior del editor: personas conectadas, su rol y el estado de la IA. */
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

  readonly avatarColor = avatarColor;
  readonly avatarInitial = avatarInitial;

  /** Nombre a mostrar: el que dio la persona o, si no hay (conexiones antiguas), su posición en la lista. */
  label(participant: { name?: string | null }, index: number): string {
    return participant.name || 'Usuario ' + (index + 1);
  }

  isCurrent(peer: string) {
    return this.p2p.isCurrentParticipant(peer);
  }

  remove(peer: string) {
    this.p2p.removeParticipant(peer);
  }
}
