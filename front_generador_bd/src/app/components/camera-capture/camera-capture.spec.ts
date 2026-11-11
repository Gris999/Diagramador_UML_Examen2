import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CameraCapture, PHOTO_FILE_NAME, cameraErrorMessage } from './camera-capture';

describe('CameraCapture', () => {
  let fixture: ComponentFixture<CameraCapture>;
  let component: CameraCapture;
  let stopped: number;
  let getUserMedia: jasmine.Spy;

  const click = (testId: string) => (fixture.nativeElement.querySelector(`[data-testid="${testId}"]`) as HTMLElement).click();
  const has = (testId: string) => !!fixture.nativeElement.querySelector(`[data-testid="${testId}"]`);
  const waitForPhoto = async () => {
    for (let i = 0; i < 40 && component.photoUrl() === null; i++) await new Promise(resolve => setTimeout(resolve, 25));
  };

  /** Una cámara de mentira: la vista tiene el tamaño de una foto de 640 por 480. */
  async function open(sized = true) {
    stopped = 0;
    const track = { stop: () => { stopped++; } } as unknown as MediaStreamTrack;
    getUserMedia = jasmine.createSpy('getUserMedia').and.resolveTo({ getTracks: () => [track] } as unknown as MediaStream);
    spyOnProperty(navigator, 'mediaDevices', 'get').and.returnValue({ getUserMedia } as unknown as MediaDevices);
    fixture = TestBed.createComponent(CameraCapture);
    component = fixture.componentInstance;
    fixture.detectChanges();
    const video = fixture.nativeElement.querySelector('video') as HTMLVideoElement;
    if (sized) {
      Object.defineProperty(video, 'videoWidth', { value: 640 });
      Object.defineProperty(video, 'videoHeight', { value: 480 });
    }
    spyOnProperty(video, 'srcObject', 'set').and.stub();
    await component.start();
    fixture.detectChanges();
  }

  beforeEach(() => TestBed.configureTestingModule({ imports: [CameraCapture], providers: [provideZonelessChangeDetection()] }));

  it('opens the camera, preferring the rear one, and lets the person take the photo', async () => {
    await open();

    expect(getUserMedia).toHaveBeenCalledWith(jasmine.objectContaining({ video: jasmine.objectContaining({ facingMode: { ideal: 'environment' } }), audio: false }));
    expect(component.ready()).toBeTrue();
    expect((fixture.nativeElement.querySelector('[data-testid="camera-take"]') as HTMLButtonElement).disabled).toBeFalse();
  });

  it('says what happened when the camera is not allowed and keeps the option of the device camera', async () => {
    stopped = 0;
    getUserMedia = jasmine.createSpy('getUserMedia').and.rejectWith({ name: 'NotAllowedError' });
    spyOnProperty(navigator, 'mediaDevices', 'get').and.returnValue({ getUserMedia } as unknown as MediaDevices);
    fixture = TestBed.createComponent(CameraCapture);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await component.start();
    fixture.detectChanges();

    expect(component.ready()).toBeFalse();
    expect(fixture.nativeElement.querySelector('[data-testid="camera-error"]').textContent).toContain('No se permitió usar la cámara');
    expect((fixture.nativeElement.querySelector('[data-testid="camera-take"]') as HTMLButtonElement).disabled).toBeTrue();
    expect(has('camera-device')).toBeTrue();
  });

  it('takes the photo, shows it and lets the person take it again', async () => {
    await open();

    click('camera-take');
    await waitForPhoto();
    fixture.detectChanges();

    expect(component.photoUrl()).toMatch(/^blob:/);
    expect(has('camera-photo')).toBeTrue();
    expect(has('camera-use')).toBeTrue();
    expect(has('camera-take')).toBeFalse();

    click('camera-retake');
    fixture.detectChanges();

    expect(component.photoUrl()).toBeNull();
    expect(has('camera-take')).toBeTrue();
  });

  it('delivers the photo as an image file, closes and turns the camera off', async () => {
    await open();
    const delivered: File[] = [];
    let closed = 0;
    component.captured.subscribe(file => delivered.push(file));
    component.closed.subscribe(() => closed++);

    click('camera-take');
    await waitForPhoto();
    fixture.detectChanges();
    click('camera-use');

    expect(delivered.length).toBe(1);
    expect(delivered[0].name).toBe(PHOTO_FILE_NAME);
    expect(delivered[0].type).toBe('image/jpeg');
    expect(delivered[0].size).toBeGreaterThan(0);
    expect(closed).toBe(1);
    expect(stopped).toBe(1);
  });

  it('does not take a photo before the camera has a picture', async () => {
    await open(false);

    click('camera-take');
    fixture.detectChanges();

    expect(component.photoUrl()).toBeNull();
    expect(fixture.nativeElement.querySelector('[data-testid="camera-error"]').textContent).toContain('todavía no está lista');
  });

  it('accepts a photo taken with the device camera', async () => {
    await open();
    const delivered: File[] = [];
    component.captured.subscribe(file => delivered.push(file));
    const file = new File(['x'], 'IMG_0001.jpg', { type: 'image/jpeg' });
    const input = document.createElement('input');
    Object.defineProperty(input, 'files', { value: [file] });

    component.onDevicePhoto({ target: input } as unknown as Event);

    expect(delivered).toEqual([file]);
  });

  it('cancel closes without a photo and turns the camera off', async () => {
    await open();
    let closed = 0;
    const delivered: File[] = [];
    component.closed.subscribe(() => closed++);
    component.captured.subscribe(file => delivered.push(file));

    click('camera-cancel');

    expect(closed).toBe(1);
    expect(delivered).toEqual([]);
    expect(stopped).toBe(1);
  });

  it('explains each way the camera can fail', () => {
    expect(cameraErrorMessage({ name: 'NotAllowedError' })).toContain('No se permitió');
    expect(cameraErrorMessage({ name: 'NotFoundError' })).toContain('No se encontró una cámara');
    expect(cameraErrorMessage({ name: 'NotReadableError' })).toContain('en uso');
    expect(cameraErrorMessage(new Error('otra cosa'))).toContain('No se pudo abrir la cámara');
  });
});
