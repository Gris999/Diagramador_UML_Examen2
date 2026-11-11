import { AfterViewInit, Component, ElementRef, OnDestroy, ViewChild, output, signal } from '@angular/core';

/** Cómo se llama el archivo de la foto que sale de la cámara (la IA solo lo lee; el nombre no importa). */
export const PHOTO_FILE_NAME = 'foto-diagrama.jpg';

/**
 * Tomar una foto con la cámara del equipo o del celular (por ejemplo, de un diagrama de clases dibujado en papel o en un pizarrón).
 *
 * Muestra la vista de la cámara, deja tomar la foto, verla y repetirla, y entrega un archivo de imagen: lo mismo que «Importar imagen»,
 * así que desde ahí la IA convierte la foto en un diagrama que se puede seguir editando. Si la cámara no está disponible o no se
 * permitió, se puede elegir la foto con la cámara del dispositivo (en un celular abre la cámara directamente).
 */
@Component({
  selector: 'app-camera-capture',
  template: `
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-scrim px-4 backdrop-blur-[2px]" role="dialog" aria-modal="true"
         aria-labelledby="camera-capture-title" data-testid="camera-capture">
      <div class="card w-full max-w-xl rounded-2xl p-5 shadow-xl">
        <h2 id="camera-capture-title" class="text-lg font-semibold text-fg">Tomar una foto del diagrama</h2>
        <p class="mt-1 text-sm text-fg-muted">Encuadra el diagrama de clases y toma la foto: la IA lo convierte en un diagrama que puedes seguir editando.</p>

        <div class="mt-4 overflow-hidden rounded-xl bg-black">
          <video #video class="block max-h-[55vh] w-full object-contain" [class.hidden]="photoUrl() !== null" autoplay playsinline muted></video>
          @if (photoUrl(); as url) {
            <img [src]="url" alt="Foto tomada" class="block max-h-[55vh] w-full object-contain" data-testid="camera-photo" />
          }
        </div>

        @if (error()) {
          <p class="mt-3 text-sm text-danger" role="alert" data-testid="camera-error">{{ error() }}</p>
        }

        <div class="mt-5 flex flex-col gap-2 sm:flex-row sm:justify-end">
          @if (photoUrl() === null) {
            <label class="btn btn-secondary cursor-pointer" data-testid="camera-device">
              Usar la cámara del dispositivo
              <input type="file" accept="image/*" capture="environment" class="hidden" (change)="onDevicePhoto($event)" />
            </label>
            <button type="button" class="btn btn-primary" data-testid="camera-take" [disabled]="!ready()" (click)="take()">Tomar foto</button>
          } @else {
            <button type="button" class="btn btn-secondary" data-testid="camera-retake" (click)="retake()">Repetir</button>
            <button type="button" class="btn btn-primary" data-testid="camera-use" (click)="use()">Usar esta foto</button>
          }
          <button type="button" class="btn btn-secondary" data-testid="camera-cancel" (click)="close()">Cancelar</button>
        </div>
      </div>
    </div>
  `
})
export class CameraCapture implements AfterViewInit, OnDestroy {
  /** La foto elegida, como archivo de imagen. */
  readonly captured = output<File>();
  /** Se cerró el cuadro (con foto o sin ella). */
  readonly closed = output<void>();

  readonly ready = signal(false);
  readonly error = signal('');
  readonly photoUrl = signal<string | null>(null);

  @ViewChild('video') private video?: ElementRef<HTMLVideoElement>;
  private stream: MediaStream | null = null;
  private photo: Blob | null = null;

  async ngAfterViewInit(): Promise<void> {
    await this.start();
  }

  ngOnDestroy(): void {
    this.stop();
    this.forgetPhoto();
  }

  /** Abre la cámara (la trasera si es un celular). */
  async start(): Promise<void> {
    this.error.set('');
    this.ready.set(false);
    try {
      const devices = typeof navigator !== 'undefined' ? navigator.mediaDevices : undefined;
      if (!devices?.getUserMedia) {
        throw new Error('sin cámara');
      }
      this.stream = await devices.getUserMedia({ video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 } }, audio: false });
      const element = this.video?.nativeElement;
      if (element) {
        element.srcObject = this.stream;
        this.ready.set(true);
      }
    } catch (error) {
      this.error.set(cameraErrorMessage(error));
    }
  }

  /** Congela lo que ve la cámara en una foto. */
  take(): void {
    const element = this.video?.nativeElement;
    if (!element || !element.videoWidth || !element.videoHeight) {
      this.error.set('La cámara todavía no está lista. Espera un momento y vuelve a intentarlo.');
      return;
    }
    const canvas = document.createElement('canvas');
    canvas.width = element.videoWidth;
    canvas.height = element.videoHeight;
    canvas.getContext('2d')?.drawImage(element, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(blob => {
      if (!blob) {
        this.error.set('No se pudo tomar la foto. Intenta de nuevo.');
        return;
      }
      this.forgetPhoto();
      this.photo = blob;
      this.photoUrl.set(URL.createObjectURL(blob));
    }, 'image/jpeg', 0.92);
  }

  retake(): void {
    this.forgetPhoto();
  }

  /** Entrega la foto como archivo y cierra. */
  use(): void {
    if (!this.photo) return;
    this.captured.emit(new File([this.photo], PHOTO_FILE_NAME, { type: 'image/jpeg' }));
    this.close();
  }

  /** La foto que se tomó con la cámara del dispositivo (un celular abre su cámara; un equipo, el selector de archivos). */
  onDevicePhoto(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    this.captured.emit(file);
    this.close();
  }

  close(): void {
    this.stop();
    this.closed.emit();
  }

  private stop(): void {
    this.stream?.getTracks().forEach(track => track.stop());
    this.stream = null;
    this.ready.set(false);
  }

  private forgetPhoto(): void {
    const url = this.photoUrl();
    if (url) URL.revokeObjectURL(url);
    this.photoUrl.set(null);
    this.photo = null;
  }
}

/** Qué decirle a la persona cuando no se pudo abrir la cámara. */
export function cameraErrorMessage(error: unknown): string {
  const name = (error as { name?: string } | null)?.name ?? '';
  if (name === 'NotAllowedError' || name === 'SecurityError') {
    return 'No se permitió usar la cámara. Permítela en el navegador o usa la cámara del dispositivo.';
  }
  if (name === 'NotFoundError' || name === 'OverconstrainedError') {
    return 'No se encontró una cámara en este equipo. Usa la cámara del dispositivo o importa una imagen.';
  }
  if (name === 'NotReadableError') {
    return 'La cámara está en uso por otra aplicación. Ciérrala e inténtalo de nuevo.';
  }
  return 'No se pudo abrir la cámara. Usa la cámara del dispositivo o importa una imagen.';
}
