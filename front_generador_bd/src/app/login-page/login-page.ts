import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService, Session } from '../../services/auth/auth.service';
import { ThemeService } from '../../services/theme.service';

/** Segundos que hay que esperar para pedir otro código (el servidor además limita cuántos se piden). */
export const RESEND_SECONDS = 30;

/** A dónde volver después de entrar: solo direcciones de esta misma página (nunca otro sitio). */
export function safeReturnUrl(value: string | null): string {
  return value && value.startsWith('/') && !value.startsWith('//') && !value.startsWith('/entrar') ? value : '/';
}

/**
 * Pantalla de entrada: se escribe el correo, llega un código de 6 dígitos y, al escribirlo, se entra. No hay contraseñas.
 *
 * Los correos que ya entraron en este navegador se recuerdan (como las cuentas de Google o de GitHub): al volver se elige uno y se entra con un
 * clic, sin pedir otro código, mientras su sesión valga. Con `?cambiar=1` (el botón «Cambiar de cuenta») la pantalla se muestra aunque ya haya
 * una sesión, para pasar de una cuenta a otra.
 */
@Component({
  selector: 'app-login-page',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './login-page.html'
})
export class LoginPage implements OnInit, OnDestroy {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  readonly theme = inject(ThemeService);

  readonly step = signal<'email' | 'code'>('email');
  /** Las cuentas que ya entraron en este navegador. */
  readonly accounts = this.auth.accounts;
  /** La cuenta con la que se está ahora, si la hay (aparece marcada en la lista). */
  readonly current = computed(() => this.auth.session()?.email ?? null);
  /** La persona pidió usar otro correo en vez de una cuenta recordada. */
  readonly adding = signal(false);
  /** Se muestra la lista de cuentas recordadas en vez de pedir el correo. */
  readonly choosing = computed(() => this.step() === 'email' && this.accounts().length > 0 && !this.adding());
  readonly email = signal('');
  readonly code = signal('');
  readonly busy = signal(false);
  readonly error = signal('');
  readonly cooldown = signal(0);
  /** El servidor dice que todavía no puede mandar correos: se avisa en vez de dejar esperando un código que no llegará. */
  readonly mailMissing = computed(() => this.auth.config()?.mailConfigured === false);

  private timer?: ReturnType<typeof setInterval>;

  ngOnInit(): void {
    this.auth.ensureConfig().subscribe(config => {
      // Si no hay que iniciar sesión, o ya se inició (y no se pidió cambiar de cuenta), esta pantalla no tiene nada que hacer.
      const switching = this.route.snapshot.queryParamMap.get('cambiar') === '1';
      if (!config.authRequired || (this.auth.loggedIn() && !switching)) void this.router.navigateByUrl(this.destination());
    });
  }

  ngOnDestroy(): void {
    this.stopTimer();
  }

  sendCode(): void {
    const email = this.email().trim();
    if (!email || this.busy()) return;
    this.busy.set(true);
    this.error.set('');
    this.auth.requestCode(email).subscribe({
      next: () => {
        this.email.set(email);
        this.code.set('');
        this.step.set('code');
        this.busy.set(false);
        this.startCooldown();
      },
      error: failure => this.fail(failure, 'No pudimos mandar el correo. Intenta de nuevo.')
    });
  }

  resend(): void {
    if (this.cooldown() > 0 || this.busy()) return;
    this.sendCode();
  }

  verify(): void {
    const code = this.code().trim();
    if (!/^\d{6}$/.test(code) || this.busy()) return;
    this.busy.set(true);
    this.error.set('');
    this.auth.verify(this.email(), code).subscribe({
      next: () => {
        this.busy.set(false);
        void this.router.navigateByUrl(this.destination());
      },
      error: failure => this.fail(failure, 'No pudimos comprobar el código. Intenta de nuevo.')
    });
  }

  /** Entra con una cuenta recordada, sin pedir otro código; si su sesión ya venció, se pide el código de ese correo. */
  useAccount(account: Session): void {
    if (this.busy()) return;
    this.error.set('');
    if (account.email === this.current()) {
      void this.router.navigateByUrl(this.destination());
      return;
    }
    this.busy.set(true);
    this.auth.resume(account.email).subscribe({
      next: () => {
        this.busy.set(false);
        void this.router.navigateByUrl(this.destination());
      },
      error: failure => {
        this.busy.set(false);
        if (failure instanceof HttpErrorResponse && failure.status === 401) {
          this.email.set(account.email);
          this.adding.set(true);
          this.error.set(`La sesión de ${account.email} venció. Pide un código nuevo para entrar.`);
        } else {
          this.error.set('No pudimos entrar ahora. Intenta de nuevo.');
        }
      }
    });
  }

  /** Quita una cuenta de la lista de este navegador (no borra nada en el servidor). */
  forget(account: Session): void {
    this.auth.forgetAccount(account.email);
  }

  /** «Usar otro correo»: se muestra el formulario del correo. */
  addAccount(): void {
    this.error.set('');
    this.email.set('');
    this.adding.set(true);
  }

  /** De vuelta a la lista de cuentas recordadas. */
  backToAccounts(): void {
    this.error.set('');
    this.adding.set(false);
  }

  changeEmail(): void {
    this.step.set('email');
    this.code.set('');
    this.error.set('');
    this.stopTimer();
    this.cooldown.set(0);
  }

  onCodeInput(value: string): void {
    this.code.set(value.replace(/\D/g, '').slice(0, 6));
  }

  private destination(): string {
    return safeReturnUrl(this.route.snapshot.queryParamMap.get('volver'));
  }

  private fail(failure: unknown, fallback: string): void {
    const reason = failure instanceof HttpErrorResponse ? failure.error?.error : undefined;
    this.error.set(typeof reason === 'string' ? reason : fallback);
    this.busy.set(false);
  }

  private startCooldown(): void {
    this.stopTimer();
    this.cooldown.set(RESEND_SECONDS);
    this.timer = setInterval(() => {
      this.cooldown.update(value => Math.max(0, value - 1));
      if (this.cooldown() === 0) this.stopTimer();
    }, 1000);
  }

  private stopTimer(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = undefined;
  }
}
