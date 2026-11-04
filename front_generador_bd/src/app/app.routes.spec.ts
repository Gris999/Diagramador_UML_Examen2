import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { routes } from './app.routes';

describe('routes', () => {
  let router: Router;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideZonelessChangeDetection(), provideHttpClient(), provideHttpClientTesting(), provideRouter(routes)]
    });
    router = TestBed.inject(Router);
  });

  it('opens the editor only for a room: it takes the code from the address', () => {
    const editor = routes.find(route => route.path === 'diagram/:roomId');

    expect(editor).toBeDefined();
    expect(editor!.redirectTo).toBeUndefined();
  });

  it('sends whoever goes to the editor without a room back to the start page', async () => {
    await router.navigateByUrl('/diagram');

    expect(router.url).toBe('/');
  });

  it('sends any unknown address back to the start page', async () => {
    await router.navigateByUrl('/sala/algo/raro/mas');

    expect(router.url).toBe('/');
  });

  it('keeps the follow-along view on its own address', async () => {
    await router.navigateByUrl('/sala/3f2a9c1e-5b7d-4e8a-9c3b-1a2b3c4d5e6f/seguir');

    expect(router.url).toBe('/sala/3f2a9c1e-5b7d-4e8a-9c3b-1a2b3c4d5e6f/seguir');
  });
});
