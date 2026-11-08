import { PLATFORM_ID, provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { NOTIFICATION_API, NotificationApi, NotificationService, SERVICE_WORKERS } from './notification.service';

class FakeNotification {
  static permission: NotificationPermission = 'default';
  static nextPermission: NotificationPermission = 'granted';
  static created: { title: string; options?: NotificationOptions }[] = [];
  static failConstructor = false;
  static requestPermission = jasmine.createSpy('requestPermission').and.callFake(async () => {
    FakeNotification.permission = FakeNotification.nextPermission;
    return FakeNotification.permission;
  });

  constructor(title: string, options?: NotificationOptions) {
    if (FakeNotification.failConstructor) throw new TypeError('Illegal constructor');
    FakeNotification.created.push({ title, options });
  }

  static reset(): void {
    FakeNotification.permission = 'default';
    FakeNotification.nextPermission = 'granted';
    FakeNotification.created = [];
    FakeNotification.failConstructor = false;
    FakeNotification.requestPermission.calls.reset();
  }
}

describe('NotificationService', () => {
  let register: jasmine.Spy;

  function create(options: { api?: NotificationApi | undefined; workers?: unknown } = {}): NotificationService {
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        { provide: PLATFORM_ID, useValue: 'browser' },
        { provide: NOTIFICATION_API, useValue: 'api' in options ? options.api : (FakeNotification as unknown as NotificationApi) },
        { provide: SERVICE_WORKERS, useValue: options.workers }
      ]
    });
    return TestBed.inject(NotificationService);
  }

  beforeEach(() => {
    FakeNotification.reset();
    register = jasmine.createSpy('register');
  });

  it('reports that notifications are unsupported where the browser has no Notification API', async () => {
    const service = create({ api: undefined });

    expect(service.permission()).toBe('unsupported');
    expect(await service.requestPermission()).toBe('unsupported');
    service.notifyChange('Ana', 'añadió una clase');
    expect(FakeNotification.created).toEqual([]);
  });

  it('reports unsupported on the server (SSR), where there is no browser to ask', () => {
    TestBed.configureTestingModule({
      providers: [provideZonelessChangeDetection(), { provide: PLATFORM_ID, useValue: 'server' }]
    });

    expect(TestBed.inject(NotificationService).permission()).toBe('unsupported');
  });

  it('starts with the permission the browser already has', () => {
    FakeNotification.permission = 'denied';

    expect(create().permission()).toBe('denied');
  });

  it('asks the browser for the permission and keeps the answer', async () => {
    const service = create();
    expect(service.permission()).toBe('default');

    const answer = await service.requestPermission();

    expect(FakeNotification.requestPermission).toHaveBeenCalledTimes(1);
    expect(answer).toBe('granted');
    expect(service.permission()).toBe('granted');
  });

  it('keeps a refusal as a refusal and does not ask again once it is blocked', async () => {
    FakeNotification.nextPermission = 'denied';
    const service = create();

    expect(await service.requestPermission()).toBe('denied');
    expect(await service.requestPermission()).toBe('denied');

    expect(FakeNotification.requestPermission).toHaveBeenCalledTimes(1);
  });

  it('does not ask again when the permission was already granted', async () => {
    FakeNotification.permission = 'granted';
    const service = create();

    expect(await service.requestPermission()).toBe('granted');

    expect(FakeNotification.requestPermission).not.toHaveBeenCalled();
  });

  it('never creates a notification without a granted permission', () => {
    const service = create();

    service.notifyChange('Ana', 'añadió una clase');
    service.notifyIdea('Falta una clave primaria');

    expect(FakeNotification.created).toEqual([]);
  });

  it('notifies a change with the author as title and the summary as body', async () => {
    const service = create();
    await service.requestPermission();

    service.notifyChange('Ana', 'añadió una clase');

    expect(FakeNotification.created.length).toBe(1);
    expect(FakeNotification.created[0].title).toBe('Ana');
    expect(FakeNotification.created[0].options?.body).toBe('añadió una clase');
  });

  it('notifies an idea from the AI', async () => {
    const service = create();
    await service.requestPermission();

    service.notifyIdea('La IA publicó una revisión con 3 ideas');

    expect(FakeNotification.created[0].title).toBe('Nueva idea de la IA');
    expect(FakeNotification.created[0].options?.body).toBe('La IA publicó una revisión con 3 ideas');
  });

  it('cuts very long texts so the notification stays readable', async () => {
    const service = create();
    await service.requestPermission();

    service.notifyChange('Ana', 'x'.repeat(500));

    const body = FakeNotification.created[0].options?.body ?? '';
    expect(body.length).toBeLessThanOrEqual(140);
    expect(body.endsWith('…')).toBeTrue();
  });

  const flush = () => new Promise<void>(resolve => setTimeout(resolve));

  it('shows the notification through the service worker first, and never builds it directly (iPhone ignores that silently)', async () => {
    FakeNotification.permission = 'granted';
    const registration = { showNotification: jasmine.createSpy('showNotification').and.resolveTo() };
    register.and.resolveTo(registration);
    const service = create({ workers: { register, ready: Promise.resolve(registration) } });

    service.notifyChange('Beto', 'eliminó un elemento');
    await flush();

    expect(register).toHaveBeenCalledOnceWith('/notification-sw.js');
    expect(registration.showNotification).toHaveBeenCalledOnceWith('Beto', jasmine.objectContaining({ body: 'eliminó un elemento' }));
    expect(FakeNotification.created).toEqual([]);
  });

  it('registers the service worker only once for several notifications', async () => {
    FakeNotification.permission = 'granted';
    const registration = { showNotification: jasmine.createSpy('showNotification').and.resolveTo() };
    register.and.resolveTo(registration);
    const service = create({ workers: { register, ready: Promise.resolve(registration) } });

    service.notifyChange('Ana', 'añadió una clase');
    service.notifyChange('Beto', 'eliminó una clase');
    await flush();

    expect(register).toHaveBeenCalledTimes(1);
    expect(registration.showNotification).toHaveBeenCalledTimes(2);
  });

  it('builds the notification directly when the service worker cannot be registered', async () => {
    FakeNotification.permission = 'granted';
    register.and.rejectWith(new Error('sin service worker'));
    const service = create({ workers: { register, ready: new Promise(() => undefined) } });

    service.notifyChange('Beto', 'eliminó un elemento');
    await flush();

    expect(FakeNotification.created.length).toBe(1);
    expect(FakeNotification.created[0].title).toBe('Beto');
  });

  it('builds the notification directly when the service worker refuses to show it', async () => {
    FakeNotification.permission = 'granted';
    const registration = { showNotification: jasmine.createSpy('showNotification').and.rejectWith(new Error('denegado')) };
    register.and.resolveTo(registration);
    const service = create({ workers: { register, ready: Promise.resolve(registration) } });

    service.notifyChange('Beto', 'eliminó un elemento');
    await flush();

    expect(FakeNotification.created.length).toBe(1);
  });

  it('tries to register the service worker again after a failure', async () => {
    FakeNotification.permission = 'granted';
    const registration = { showNotification: jasmine.createSpy('showNotification').and.resolveTo() };
    register.and.returnValues(Promise.reject(new Error('primera vez')), Promise.resolve(registration));
    const service = create({ workers: { register, ready: Promise.resolve(registration) } });

    service.notifyChange('Ana', 'primera');
    await flush();
    service.notifyChange('Ana', 'segunda');
    await flush();

    expect(register).toHaveBeenCalledTimes(2);
    expect(registration.showNotification).toHaveBeenCalledTimes(1);
  });

  it('does not fail when neither way of notifying works', async () => {
    FakeNotification.permission = 'granted';
    FakeNotification.failConstructor = true;
    const service = create({ workers: undefined });

    expect(() => service.notifyChange('Beto', 'eliminó un elemento')).not.toThrow();
  });
});
