import { Routes } from '@angular/router';
import { Diagram } from './diagram/diagram';
import { LandinPage } from './landin-page/landin-page';
import { FollowView } from './follow-view/follow-view';
import { LoginPage } from './login-page/login-page';
import { authGuard } from '../services/auth/auth.guard';
export const routes: Routes = [ 
  // Con el servidor en modo «entrar con el correo», las tres pantallas piden iniciar sesión (authGuard); sin él, todo funciona como siempre.
  { path: 'entrar', component: LoginPage },
  { path: '', component: LandinPage, canActivate: [authGuard] },
  { 
    path: 'diagram/:roomId', 
    component: Diagram,
    canActivate: [authGuard],
  },
  {
    path: 'sala/:roomId/seguir',
    component: FollowView,
    canActivate: [authGuard],
  },
  { path: '**', redirectTo: '' }
];  
