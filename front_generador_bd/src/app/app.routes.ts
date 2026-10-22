import { Routes } from '@angular/router';
import { Diagram } from './diagram/diagram';
import { LandinPage } from './landin-page/landin-page';
import { FollowView } from './follow-view/follow-view';
export const routes: Routes = [ 
  { path: '', component: LandinPage },  
  { 
    path: 'diagram/:roomId', 
    component: Diagram,
  },
  {
    path: 'sala/:roomId/seguir',
    component: FollowView,
  },
  { path: '**', redirectTo: '' }
];  
