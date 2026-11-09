/**
 * ¿El navegador es el de un celular? (iPhone, iPod, Android con «Mobile», etc.). Las tabletas no cuentan: en el celular la herramienta es
 * informativa (se sigue el diagrama y llegan avisos) y la edición se hace desde un computador o una tableta.
 */
export function isPhone(userAgent: string = typeof navigator !== 'undefined' ? navigator.userAgent : ''): boolean {
  return /iPhone|iPod|Android.+Mobile|Windows Phone|IEMobile|BlackBerry|Opera Mini|webOS/i.test(userAgent ?? '');
}
