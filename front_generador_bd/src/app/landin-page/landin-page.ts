import { Component, computed, inject } from '@angular/core';
import { Router } from '@angular/router';
import { v4 as uuid, validate as isUuid } from 'uuid';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HelpPanel } from '../help-panel/help-panel';
import { MyDiagrams } from '../my-diagrams/my-diagrams';
import { ThemeService } from '../../services/theme.service';
import { AuthService } from '../../services/auth/auth.service';

@Component({
  selector: 'app-landin-page',
  imports: [CommonModule, FormsModule, HelpPanel, MyDiagrams],
  templateUrl: './landin-page.html',
  styleUrls: ['./landin-page.css']
})
export class LandinPage {
  joinCode: string = '';
  /** Por qué no se pudo entrar con el código escrito; vacío si no hay problema. */
  joinError: string = '';

  readonly theme = inject(ThemeService);
  readonly auth = inject(AuthService);
  /** Con «entrar con el correo» la portada es la lista «Mis diagramas»; sin él, crear o unirse con un código como siempre. */
  readonly library = computed(() => this.auth.config()?.authRequired === true && this.auth.loggedIn());

  constructor(private router: Router) {}

  /** Cierra la sesión del correo y vuelve a la pantalla de entrada (si el servidor no pide sesión, la portada sigue igual). */
  cerrarSesion() {
    this.auth.logout();
    if (this.auth.config()?.authRequired) void this.router.navigate(['/entrar']);
  }

  /** Pasa a otra cuenta recordada en este navegador (o a un correo nuevo) sin cerrar la actual. */
  cambiarDeCuenta() {
    void this.router.navigate(['/entrar'], { queryParams: { cambiar: 1 } });
  }

  crearNuevoLienzo() {
    const roomId = uuid();
    this.router.navigate(['/diagram', roomId]);
  }

  /**
   * El código de una sala es el identificador que genera «Crear Nuevo Lienzo». Con otro texto la sala no se podría respaldar ni retomar
   * (el servidor guarda los respaldos por identificador), así que no se entra y se explica por qué.
   */
  unirseAlLienzo() {
    const code = this.joinCode.trim().toLowerCase();
    if (!code) return;
    if (!isUuid(code)) {
      this.joinError = 'El código no es válido. Pídeselo a quien creó la sala: es el que copia con «Copiar código de sala».';
      return;
    }
    this.joinError = '';
    this.router.navigate(['/diagram', code]);
  }

  onCodeChange(value: string) {
    this.joinCode = value;
    this.joinError = '';
  }
}
