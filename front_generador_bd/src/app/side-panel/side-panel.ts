import { Component, Output, EventEmitter, PLATFORM_ID, Inject, signal, inject } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { DragDropModule, CdkDragEnd, CdkDragStart } from '@angular/cdk/drag-drop';
import { FormsModule } from '@angular/forms';
import { DiagramService } from '../../services/diagram/diagram.service';
import { UmlValidationService } from '../../services/colaboration/uml-validation.service';
import { ActivatedRoute, Router } from '@angular/router';
import { SqlExportService } from '../../services/exports/sql-export.service';
import { UmlImageServiceTs } from '../../services/imports/uml-image.service';
import { FrontendGeneratorService } from '../../services/exports/frontend-generator.service';
import { Spinner } from "../components/diagram/spinner/spinner";
import { ChatbotService } from '../../services/IA/chatbot.service';
import { BackendGeneratorService } from '../../services/exports/backend-generator.service';


@Component({
  selector: 'app-side-panel',
  imports: [CommonModule, DragDropModule, FormsModule, Spinner],
  templateUrl: './side-panel.html',
  styleUrl: './side-panel.css'
})
export class SidePanel {
  private frontendGeneratorService = inject(FrontendGeneratorService);
  private chatboxService = inject(ChatbotService);
  private backendGeneratorService=inject(BackendGeneratorService);
  @Output() elementDragged = new EventEmitter<CdkDragEnd>();
  @Output() saveClicked = new EventEmitter<void>();
  @Output() generateClicked = new EventEmitter<string>();

  public showActions: boolean = false;
  public showActionsImports: boolean = false;
  public showPalette: boolean = true;

  prompt: string = '';
  validationCollapsed = signal<boolean>(true);
  validationResult = signal<any>(null);
  analyzingModel = signal<boolean>(false);
  roomId: string | null = null;
  copied = signal<boolean>(false);
  recognizing = signal<boolean>(false);
  private mediaRecorder: MediaRecorder | null = null;
  private mediaStream: MediaStream | null = null;
  private audioChunks: Blob[] = [];
  isBrowser: boolean;

  constructor(
    private diagramService: DiagramService,
    private umlValidation: UmlValidationService,
    private router: Router,
    private route: ActivatedRoute,
    private sqlExportService: SqlExportService,
    private umlImageService: UmlImageServiceTs,
    @Inject(PLATFORM_ID) platformId: Object
  ) {
    this.isBrowser = isPlatformBrowser(platformId); // ✅ detecta si estamos en navegador
    this.roomId = this.route.snapshot.paramMap.get('roomId');

  }



  onDragEnded(event: CdkDragEnd) {
    this.elementDragged.emit(event);
    event.source.reset();
  }
  onSaveClicked() {
    this.saveClicked.emit();
  }
  onGenerate() {
    if (this.prompt.trim()) {
      this.generateClicked.emit(this.prompt.trim());
      this.prompt = '';
    }
  }
  // para colapsar el panel
  toggleValidationPanel() {
    this.validationCollapsed.set(!this.validationCollapsed());
  }

  analyzeNow() {
    this.analyzingModel.set(true);
    const umlJson = this.diagramService.exportToJson();
    this.umlValidation.validateModel(umlJson);
  }

  // para recibir resultados desde el padre (diagram)
  updateValidationResult(result: any) {
    this.validationResult.set(result);
    this.analyzingModel.set(false);
    if (this.validationCollapsed()) {
      this.validationCollapsed.set(false); // abrir solo si estaba cerrado
    }
    //this.analyzingModel = false;
  }
  goHome() {
    this.diagramService.clearStorage(); // Limpia el diagrama guardado
    this.diagramService.closeDiagram(this.roomId!); // Cierra conexiones y limpia estado
    this.router.navigate(['/']); // redirige al inicio
  }
  copyRoomCode() {
    const roomId = this.route.snapshot.paramMap.get('roomId');
    if (!roomId) return;

    const isSecure = window.location.protocol === 'https:' || window.location.hostname === 'localhost';

    if (isSecure && navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(roomId).then(() => {
        this.copied.set(true);
        setTimeout(() => this.copied.set(false), 2000);
      }).catch(() => this.fallbackCopy(roomId));
    } else {
      this.fallbackCopy(roomId);
    }
  }

  private fallbackCopy(text: string) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    try {
      document.execCommand('copy');
      this.copied.set(true);
      setTimeout(() => this.copied.set(false), 2000);
    } catch (err) {
      console.error('Fallback copy failed', err);
    }
    document.body.removeChild(textarea);
  }

  async toggleVoiceInput() {
    if (!this.isBrowser) {
      return;
    }

    if (
      this.mediaRecorder &&
      this.mediaRecorder.state === 'recording'
    ) {
      this.mediaRecorder.stop();
      this.recognizing.set(false);
      return;
    }

    if (
      !navigator.mediaDevices?.getUserMedia ||
      typeof MediaRecorder === 'undefined'
    ) {
      alert(
        'Este navegador no permite grabar audio.'
      );
      return;
    }

    try {
      const stream =
        await navigator.mediaDevices.getUserMedia({
          audio: true
        });

      this.mediaStream = stream;
      this.audioChunks = [];

      const candidates = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus'
      ];

      const supportedMime =
        candidates.find((mime) =>
          MediaRecorder.isTypeSupported(mime)
        );

      this.mediaRecorder = supportedMime
        ? new MediaRecorder(
            stream,
            { mimeType: supportedMime }
          )
        : new MediaRecorder(stream);

      const recorder = this.mediaRecorder;

      recorder.ondataavailable = (
        event: BlobEvent
      ) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      recorder.onerror = (event: Event) => {
        console.error(
          'Error grabando audio:',
          event
        );

        this.recognizing.set(false);
        this.stopMicrophoneStream();
      };

      recorder.onstop = () => {
        const mimeType =
          recorder.mimeType
            ?.split(';', 1)[0]
            .trim() ||
          'audio/webm';

        const audioBlob = new Blob(
          this.audioChunks,
          { type: mimeType }
        );

        this.audioChunks = [];
        this.recognizing.set(false);
        this.stopMicrophoneStream();

        if (audioBlob.size === 0) {
          alert(
            'No se capturó audio. Intenta nuevamente.'
          );
          return;
        }

        this.processVoiceAudio(audioBlob);
      };

      recorder.start();
      this.recognizing.set(true);

    } catch (error) {
      console.error(
        'No se pudo acceder al micrófono:',
        error
      );

      this.recognizing.set(false);

      alert(
        'No se pudo acceder al micrófono.'
      );
    }
  }

  private processVoiceAudio(audio: Blob) {
    this.chatboxService.isLoading.set(true);
    const currentUml = this.diagramService.exportToJson();

    this.chatboxService
      .generateDiagramFromAudio(audio, currentUml)
      .subscribe({
        next: (response: any) => {
          const umlJson =
            response?.uml_json || response;

          if (
            umlJson?.error ||
            !umlJson ||
            !Array.isArray(umlJson.classes)
          ) {
            console.error(
              'Respuesta UML de voz inválida:',
              response
            );

            alert(
              response?.error ||
              'La IA no pudo interpretar la voz.'
            );

            this.chatboxService.isLoading.set(
              false
            );
            return;
          }

          if (response?.transcript) {
            this.prompt = response.transcript;
          }

          this.diagramService.loadFromJson(
            umlJson,
            true
          );

          this.chatboxService.isLoading.set(
            false
          );
        },

        error: (error: any) => {
          console.error(
            'Error procesando voz:',
            error
          );

          this.chatboxService.isLoading.set(
            false
          );

          alert(
            'No se pudo procesar la instrucción de voz.'
          );
        }
      });
  }

  private stopMicrophoneStream() {
    this.mediaStream
      ?.getTracks()
      .forEach((track) => track.stop());

    this.mediaStream = null;
    this.mediaRecorder = null;
  }

  exportImage() {
    this.diagramService.exportToImage('diagrama.png');
  }
  exportSql() {
    const umlJson = this.diagramService.exportToJson();
    this.sqlExportService.downloadSql(umlJson, 'diagrama.sql');
  }

  onImportImage(event: Event) {
    this.umlImageService.loading.set(true);
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;

    const file = input.files[0];
    this.analyzingModel.set(true);

    this.umlImageService.analyzeImage(file).subscribe({
      next: (res) => {
        const umlJson = res.uml_json || res;

        if (
          umlJson?.error ||
          !umlJson ||
          !Array.isArray(umlJson.classes)
        ) {
          console.error('Respuesta UML de imagen inválida:', umlJson);
          alert(
            umlJson?.error ||
            'La IA no pudo obtener un modelo UML válido de la imagen.'
          );
          this.analyzingModel.set(false);
          this.umlImageService.loading.set(false);
          input.value = '';
          return;
        }

        this.diagramService.loadFromJson(umlJson);
        this.analyzingModel.set(false);
        this.umlImageService.loading.set(false);
        input.value = '';
      },
      error: (err) => {
        console.error('❌ Error al analizar imagen UML:', err);
        this.analyzingModel.set(false);
        this.umlImageService.loading.set(false);
      }
    });
  }

  onGenerateFrontend() {
    const umlJson = this.diagramService.exportToJson();
    this.frontendGeneratorService.generateFrontend(umlJson);
  }

  isLoadingImage(): boolean {
    return this.umlImageService.loading();
  }
  isLoadingChatbox(): boolean {
    return this.chatboxService.isLoading();
  }
  isLoadingGeneratefrontend(): boolean {
    return this.frontendGeneratorService.loading();
  }
  isLoadingGenerateBackend():boolean{
    return this.backendGeneratorService.loading();
  }
  


}
