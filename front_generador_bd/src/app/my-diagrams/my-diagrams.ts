import { Component, HostListener, OnInit, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { v4 as uuid } from 'uuid';
import { AuthService } from '../../services/auth/auth.service';
import { MyRoom, RoomAccessService } from '../../services/auth/room-access.service';
import { roleLabel } from '../share-dialog/share-dialog';

/** «Hace 5 min», «ayer», «hace 3 d»… a partir de una fecha ISO; vacío si no se sabe. */
export function timeAgo(iso: string | null, now: number = Date.now()): string {
  if (!iso) return '';
  const seconds = Math.max(0, (now - new Date(iso).getTime()) / 1000);
  if (Number.isNaN(seconds)) return '';
  if (seconds < 60) return 'ahora';
  if (seconds < 3600) return `hace ${Math.floor(seconds / 60)} min`;
  if (seconds < 86400) return `hace ${Math.floor(seconds / 3600)} h`;
  if (seconds < 172800) return 'ayer';
  return `hace ${Math.floor(seconds / 86400)} d`;
}

/**
 * «Mis diagramas», como la lista de Documentos de Google: los diagramas que creó la persona, a los que la invitaron y los que abrió por un enlace
 * público, con su nombre, su rol y cuándo los abrió por última vez. Desde aquí se abre uno, se le cambia el nombre, se borra (el propietario) o se
 * quita de la lista (quien no es propietario), y se crea uno nuevo.
 */
@Component({
  selector: 'app-my-diagrams',
  standalone: true,
  templateUrl: './my-diagrams.html'
})
export class MyDiagrams implements OnInit {
  private readonly access = inject(RoomAccessService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly diagrams = signal<MyRoom[]>([]);
  readonly loading = signal(true);
  readonly error = signal('');
  /** El menú de acciones abierto (el código de la sala), o `null`. */
  readonly menuFor = signal<string | null>(null);
  readonly empty = computed(() => !this.loading() && !this.error() && this.diagrams().length === 0);
  readonly roleLabel = roleLabel;
  readonly timeAgo = timeAgo;

  ngOnInit(): void {
    this.access.myRooms().subscribe({
      next: rooms => {
        this.diagrams.set(rooms);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No pudimos cargar tus diagramas. Recarga la página para intentar de nuevo.');
        this.loading.set(false);
      }
    });
  }

  /** Crea un diagrama nuevo: la persona que lo abre primero queda como propietaria. */
  create(): void {
    void this.router.navigate(['/diagram', uuid()]);
  }

  open(room: string): void {
    this.menuFor.set(null);
    void this.router.navigate(['/diagram', room]);
  }

  toggleMenu(room: string, event: Event): void {
    event.stopPropagation();
    this.menuFor.update(current => (current === room ? null : room));
  }

  @HostListener('document:click')
  @HostListener('document:keydown.escape')
  closeMenu(): void {
    if (this.menuFor() !== null) this.menuFor.set(null);
  }

  rename(diagram: MyRoom): void {
    this.menuFor.set(null);
    const answer = typeof window === 'undefined' ? null : window.prompt('Nombre del diagrama', diagram.title);
    if (answer === null) return;
    this.access.updateSettings(diagram.room, { title: answer }).subscribe({
      next: info => this.diagrams.update(list => list.map(item => (item.room === diagram.room ? { ...item, title: info.title ?? answer } : item))),
      error: () => this.error.set('No pudimos cambiar el nombre. Intenta de nuevo.')
    });
  }

  /** El propietario borra el diagrama para todas las personas. */
  remove(diagram: MyRoom): void {
    this.menuFor.set(null);
    const name = diagram.title || 'Sin título';
    if (typeof window === 'undefined' || !window.confirm(`¿Eliminar «${name}»? Se borra para todas las personas y no se puede deshacer.`)) return;
    this.access.deleteRoom(diagram.room).subscribe({
      next: () => this.drop(diagram.room),
      error: () => this.error.set('No pudimos eliminar el diagrama. Intenta de nuevo.')
    });
  }

  /** Quien no es propietario lo quita de su lista (el diagrama sigue existiendo para los demás). */
  leave(diagram: MyRoom): void {
    this.menuFor.set(null);
    const email = this.auth.session()?.email;
    const name = diagram.title || 'Sin título';
    if (!email || typeof window === 'undefined' || !window.confirm(`¿Quitar «${name}» de tu lista?`)) return;
    this.access.removeMember(diagram.room, email).subscribe({
      next: () => this.drop(diagram.room),
      error: () => this.error.set('No pudimos quitarlo de tu lista. Intenta de nuevo.')
    });
  }

  private drop(room: string): void {
    this.diagrams.update(list => list.filter(item => item.room !== room));
  }
}
