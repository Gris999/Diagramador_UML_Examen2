import { isPhone } from './device';

describe('isPhone', () => {
  const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1';
  const ANDROID_PHONE = 'Mozilla/5.0 (Linux; Android 16; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36';

  it('recognizes the phones', () => {
    expect(isPhone(IPHONE)).toBeTrue();
    expect(isPhone(ANDROID_PHONE)).toBeTrue();
    expect(isPhone('Mozilla/5.0 (iPod touch; CPU iPhone OS 12_0 like Mac OS X)')).toBeTrue();
    expect(isPhone('Mozilla/5.0 (Windows Phone 10.0; Android 6.0.1) Mobile Safari')).toBeTrue();
  });

  it('does not take tablets or computers for phones: those can edit', () => {
    expect(isPhone('Mozilla/5.0 (iPad; CPU OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1')).toBeFalse();
    expect(isPhone('Mozilla/5.0 (Linux; Android 14; SM-X710) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36')).toBeFalse();
    expect(isPhone('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/18.0 Safari/605.1.15')).toBeFalse();
    expect(isPhone('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36')).toBeFalse();
  });

  it('says no when there is no user agent', () => {
    expect(isPhone('')).toBeFalse();
    // sin dato se mira el navegador de la prueba, que es un computador
    expect(isPhone(undefined as unknown as string)).toBeFalse();
  });
});
