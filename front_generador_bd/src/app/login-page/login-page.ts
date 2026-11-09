import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../services/auth/auth.service';
import { ThemeService } from '../../services/theme.service';

/** Segundos que hay que esperar para pedir otro código (el servidor además limita cuántos se piden). */
export const RESEND_SECONDS = 30;

/** A dónde volver después de entrar: solo direcciones de esta misma página (nunca otro sitio). */
export function safeReturnUrl(value: string | null): string {
  return value && value.startsWith('/') && !value.startsWith('//') && !value.startsWith('/entrar') ? value : '/';
}

/**
 * Pantalla de entrada: se escribe el correo, llega un código de 6 dígitos y, al escribirlo, se entra. No hay contraseñas.
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
      // Si no hay que iniciar sesión, o ya se inició, esta pantalla no tiene nada que hacer.
      if (!config.authRequired || this.auth.loggedIn()) void this.router.navigateByUrl(this.destination());
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
