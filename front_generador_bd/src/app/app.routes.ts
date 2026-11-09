import { Routes } from '@angular/router';
import { Diagram } from './diagram/diagram';
import { LandinPage } from './landin-page/landin-page';
import { FollowView } from './follow-view/follow-view';
import { LoginPage } from './login-page/login-page';
import { AccessDeniedPage } from './access-denied-page/access-denied-page';
import { authGuard } from '../services/auth/auth.guard';
import { editorRoomGuard, phoneGuard, roomAccessGuard } from '../services/auth/room.guards';
export const routes: Routes = [ 
  // Con el servidor en modo «entrar con el correo», las tres pantallas piden iniciar sesión (authGuard); sin él, todo funciona como siempre.
  { path: 'entrar', component: LoginPage },
  { path: 'sin-acceso', component: AccessDeniedPage },
  { path: '', component: LandinPage, canActivate: [authGuard] },
  { 
    path: 'diagram/:roomId', 
    component: Diagram,
    // Con login: tener sesión, tener acceso a la sala y, si solo es lector o está en un celular, ir a la vista de solo lectura en vez del editor.
    canActivate: [authGuard, editorRoomGuard, phoneGuard],
  },
  {
    path: 'sala/:roomId/seguir',
    component: FollowView,
    canActivate: [authGuard, roomAccessGuard],
  },
  { path: '**', redirectTo: '' }
];  
