import { validate as isUuid } from 'uuid';
import {
  IDENTITY_NAME_STORAGE_KEY,
  IDENTITY_TOKEN_STORAGE_KEY,
  IdentityService
} from './identity.service';

describe('IdentityService', () => {
  beforeEach(() => {
    localStorage.removeItem(IDENTITY_TOKEN_STORAGE_KEY);
    localStorage.removeItem(IDENTITY_NAME_STORAGE_KEY);
  });

  afterEach(() => {
    localStorage.removeItem(IDENTITY_TOKEN_STORAGE_KEY);
    localStorage.removeItem(IDENTITY_NAME_STORAGE_KEY);
  });

  it('remembers a UUID token and sanitized display name in browser storage', () => {
    const prompt = spyOn(window, 'prompt').and.returnValue('  Ana\u0000  ');
    const firstService = new IdentityService('browser');

    const first = firstService.getIdentity();
    const secondService = new IdentityService('browser');
    const second = secondService.getIdentity();

    expect(isUuid(first.token)).toBeTrue();
    expect(first.name).toBe('Ana');
    expect(second).toEqual(first);
    expect(prompt).toHaveBeenCalledTimes(1);
  });

  it('keeps a stable in-memory identity when storage is unavailable', () => {
    spyOn(localStorage, 'getItem').and.throwError('storage unavailable');
    spyOn(localStorage, 'setItem').and.throwError('storage unavailable');
    spyOn(window, 'prompt').and.returnValue('Beatriz');
    const service = new IdentityService('browser');

    const first = service.getIdentity();
    const second = service.getIdentity();

    expect(isUuid(first.token)).toBeTrue();
    expect(second).toEqual(first);
    expect(first.name).toBe('Beatriz');
  });

  it('uses memory only and never touches browser APIs during SSR', () => {
    const getItem = spyOn(localStorage, 'getItem');
    const setItem = spyOn(localStorage, 'setItem');
    const prompt = spyOn(window, 'prompt');
    const service = new IdentityService('server');

    const first = service.getIdentity();
    const second = service.getIdentity();

    expect(isUuid(first.token)).toBeTrue();
    expect(first.name).toBe('Usuario');
    expect(second).toEqual(first);
    expect(getItem).not.toHaveBeenCalled();
    expect(setItem).not.toHaveBeenCalled();
    expect(prompt).not.toHaveBeenCalled();
  });
});
