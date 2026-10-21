import { isPlatformBrowser } from '@angular/common';
import { Inject, Injectable, PLATFORM_ID } from '@angular/core';
import { validate as isUuid, v4 as uuid } from 'uuid';

export const IDENTITY_TOKEN_STORAGE_KEY = 'uml-collab-participant-token';
export const IDENTITY_NAME_STORAGE_KEY = 'uml-collab-participant-name';

export type ParticipantIdentity = {
  token: string;
  name: string;
};

@Injectable({ providedIn: 'root' })
export class IdentityService {
  private memoryToken?: string;
  private memoryName?: string;

  constructor(@Inject(PLATFORM_ID) private readonly platformId: Object) {}

  getIdentity(): ParticipantIdentity {
    const token = this.getToken();
    const name = this.getName();
    return { token, name };
  }

  private getToken(): string {
    if (this.memoryToken) return this.memoryToken;

    const stored = this.readStorage(IDENTITY_TOKEN_STORAGE_KEY);
    this.memoryToken = stored && isUuid(stored) ? stored : uuid();
    this.writeStorage(IDENTITY_TOKEN_STORAGE_KEY, this.memoryToken);
    return this.memoryToken;
  }

  private getName(): string {
    if (this.memoryName) return this.memoryName;

    const stored = this.sanitizeName(this.readStorage(IDENTITY_NAME_STORAGE_KEY));
    if (stored) {
      this.memoryName = stored;
      this.writeStorage(IDENTITY_NAME_STORAGE_KEY, stored);
      return stored;
    }

    const requested = this.requestName();
    this.memoryName = requested || 'Usuario';
    this.writeStorage(IDENTITY_NAME_STORAGE_KEY, this.memoryName);
    return this.memoryName;
  }

  private requestName(): string {
    if (!this.isBrowser()) return '';
    try {
      return this.sanitizeName(window.prompt('¿Cómo deseas que te vean en la sala?'));
    } catch {
      return '';
    }
  }

  private sanitizeName(value: string | null): string {
    return (value ?? '')
      .replace(/[\u0000-\u001f\u007f-\u009f]/g, '')
      .trim()
      .slice(0, 40);
  }

  private readStorage(key: string): string | null {
    if (!this.isBrowser()) return null;
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  }

  private writeStorage(key: string, value: string): void {
    if (!this.isBrowser()) return;
    try {
      window.localStorage.setItem(key, value);
    } catch {
      // The in-memory fields keep the identity stable for this page lifetime.
    }
  }

  private isBrowser(): boolean {
    return isPlatformBrowser(this.platformId) && typeof window !== 'undefined';
  }
}
