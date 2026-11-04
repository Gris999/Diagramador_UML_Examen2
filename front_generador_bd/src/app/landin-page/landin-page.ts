import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { v4 as uuid, validate as isUuid } from 'uuid';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HelpPanel } from '../help-panel/help-panel';

@Component({
  selector: 'app-landin-page',
  imports: [CommonModule, FormsModule, HelpPanel],
  templateUrl: './landin-page.html',
  styleUrls: ['./landin-page.css']
})
export class LandinPage {
  joinCode: string = '';
  /** Por qué no se pudo entrar con el código escrito; vacío si no hay problema. */
  joinError: string = '';

  constructor(private router: Router) {}

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
