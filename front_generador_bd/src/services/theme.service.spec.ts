import { PLATFORM_ID, provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { THEME_STORAGE_KEY, ThemeService } from './theme.service';

describe('ThemeService', () => {
  function create(platform: 'browser' | 'server' = 'browser'): ThemeService {
    TestBed.configureTestingModule({
      providers: [provideZonelessChangeDetection(), { provide: PLATFORM_ID, useValue: platform }]
    });
    return TestBed.inject(ThemeService);
  }

  beforeEach(() => {
    localStorage.removeItem(THEME_STORAGE_KEY);
    document.documentElement.removeAttribute('data-theme');
  });

  afterEach(() => {
    localStorage.removeItem(THEME_STORAGE_KEY);
    document.documentElement.removeAttribute('data-theme');
  });

  it('starts dark when nothing was chosen before, and marks the page with it', () => {
    const service = create();

    expect(service.theme()).toBe('dark');
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('starts with the theme the person chose in an earlier visit', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'light');

    const service = create();

    expect(service.theme()).toBe('light');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('ignores an unknown saved value and falls back to dark', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'morado');

    expect(create().theme()).toBe('dark');
  });

  it('toggles between dark and light, updating the page and remembering the choice', () => {
    const service = create();

    service.toggle();
    expect(service.theme()).toBe('light');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('light');

    service.toggle();
    expect(service.theme()).toBe('dark');
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark');
  });

  it('still switches the theme when the browser refuses to store it', () => {
    const service = create();
    spyOn(Storage.prototype, 'setItem').and.throwError('bloqueado');

    expect(() => service.set('light')).not.toThrow();
    expect(service.theme()).toBe('light');
  });

  it('does not read the browser storage on the server and stays dark', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'light');

    expect(create('server').theme()).toBe('dark');
  });
});
