// Service worker mínimo: solo existe para que Android pueda mostrar los avisos de la vista de seguimiento
// (NotificationService). No guarda nada en caché ni recibe mensajes push.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(windows => {
      if (windows.length) return windows[0].focus();
    })
  );
});
