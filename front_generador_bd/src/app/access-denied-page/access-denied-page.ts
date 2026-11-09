import { Component, computed, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../services/auth/auth.service';
import { ThemeService } from '../../services/theme.service';

/** Pantalla para quien inició sesión pero su correo no tiene invitación a esa sala. */
@Component({
  selector: 'app-access-denied-page',
  standalone: true,
  templateUrl: './access-denied-page.html'
})
export class AccessDeniedPage {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  readonly theme = inject(ThemeService);

  readonly email = computed(() => this.auth.session()?.email ?? '');

  /** Cambiar de cuenta: se cierra la sesión y, al entrar con otro correo, se vuelve a la misma sala. */
  changeAccount(): void {
    const room = this.route.snapshot.queryParamMap.get('sala');
    this.auth.logout();
    void this.router.navigate(['/entrar'], room ? { queryParams: { volver: `/diagram/${room}` } } : {});
  }

  goHome(): void {
    void this.router.navigateByUrl('/');
  }
}
