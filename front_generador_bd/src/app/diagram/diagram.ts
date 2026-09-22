import { AfterViewInit, Component, ElementRef, HostListener, Inject, NgZone, OnDestroy, PLATFORM_ID, ViewChild } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { CdkDragEnd, CdkDropListGroup, CdkDropList } from '@angular/cdk/drag-drop';
import { SidePanel } from "../side-panel/side-panel";
import { DiagramService } from '../../services/diagram/diagram.service';
import { FallbackService } from '../../services/diagram/fallback.service';
import { RelationshipService } from '../../services/diagram/relationship.service';
import { UmlClass, Attribute, Method } from '../../models/uml-class.model';
import { DiagramExportService } from '../../services/exports/diagram-export.service';
import { BackendGeneratorService } from '../../services/exports/backend-generator.service';
import { ChatbotService } from '../../services/IA/chatbot.service';
import { UmlValidationService } from '../../services/colaboration/uml-validation.service';
import { ActivatedRoute } from '@angular/router';
import { XmiService } from '../../services/interop/xmi.service';
import { ParticipantsPanel } from '../participants-panel/participants-panel';

@Component({
  selector: 'app-diagram',
  standalone: true,
  templateUrl: './diagram.html',
  styleUrls: ['./diagram.css'],
  imports: [SidePanel, CdkDropListGroup, CdkDropList, ParticipantsPanel]
})
export class Diagram implements AfterViewInit, OnDestroy {
  @ViewChild('paperContainer', { static: true }) paperContainer!: ElementRef;
  @ViewChild(SidePanel) sidePanel!: SidePanel;

  private lastMousePos: { x: number; y: number } | null = null;
  private roomId: string | null = null;
  private roomLeft = false;

  constructor(
    @Inject(PLATFORM_ID) private platformId: Object,
    private ngZone: NgZone,
    private diagramService: DiagramService,
    private fallbackService: FallbackService,
    private relationshipService: RelationshipService,
    private exportService: DiagramExportService,
    private backendGen: BackendGeneratorService,
    private chatbot: ChatbotService,
    private umlValidation: UmlValidationService,
    private route: ActivatedRoute,
    private xmiService: XmiService
  ) {}
  
  async ngAfterViewInit(): Promise<void> {
    if (isPlatformBrowser(this.platformId)) {
      this.ngZone.run(async () => {
        try {
          const roomId = this.route.snapshot.paramMap.get('roomId') || 'default-room';
          this.roomId = roomId;
          await this.diagramService.initialize(this.paperContainer.nativeElement, roomId);
          
          this.sidePanel.elementDragged.subscribe((event: CdkDragEnd) => {
            this.onDragEnded(event);
          });

          this.sidePanel.saveClicked.subscribe(() => this.saveDiagram());

          this.sidePanel.generateClicked.subscribe((prompt: string) => {
            this.generateFromPrompt(prompt);
          });
          
          this.umlValidation.connect((result) => {
            this.sidePanel.updateValidationResult(result);
          });
          
          console.log('Diagrama inicializado correctamente');
        } catch (error) {
          console.error('Error al inicializar el diagrama:', error);
        }
      });
    }
      // Guardar la posición del mouse sobre el canvas
      if (this.paperContainer?.nativeElement) {
        this.paperContainer.nativeElement.addEventListener('mousemove', (evt: MouseEvent) => {
          const rect = this.paperContainer.nativeElement.getBoundingClientRect();
          this.lastMousePos = {
            x: evt.clientX - rect.left,
            y: evt.clientY - rect.top
          };
        });
        // Si el mouse sale del canvas, limpiar la posición
        this.paperContainer.nativeElement.addEventListener('mouseleave', () => {
          this.lastMousePos = null;
        });
      }
  }
  saveDiagram() {
    const json = this.exportService.export(this.diagramService.getGraph());
    console.log('JSON exportado:', JSON.stringify(json, null, 2));

    // luego lo puedes enviar a backend
    this.backendGen.generateBackend(json, 'mi-backend.zip');
  }

  exportXmi(): void {
    const umlJson = this.exportService.export(
      this.diagramService.getGraph()
    );

    this.xmiService.exportXmi(umlJson).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement('a');

        anchor.href = url;
        anchor.download = 'diagram.xmi';
        anchor.click();

        URL.revokeObjectURL(url);

        console.log('XMI exportado correctamente');
      },
      error: (error) => {
        console.error('Error exportando XMI:', error);
        alert('No se pudo exportar el archivo XMI.');
      }
    });
  }

  importXmi(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];

    if (!file) {
      return;
    }

    this.xmiService.importXmi(file).subscribe({
      next: (umlJson) => {
        this.applyDefaultXmiLayout(umlJson);

        this.diagramService.loadFromJson(
          umlJson,
          false
        );

        console.log('XMI importado correctamente');

        // Permite seleccionar nuevamente el mismo archivo.
        input.value = '';
      },
      error: (error) => {
        console.error('Error importando XMI:', error);
        alert('No se pudo importar el archivo XMI.');
        input.value = '';
      }
    });
  }

  private applyDefaultXmiLayout(umlJson: any): void {
    if (!Array.isArray(umlJson?.classes)) {
      return;
    }

    const columns = 3;
    const startX = 80;
    const startY = 80;
    const horizontalGap = 260;
    const verticalGap = 200;

    umlJson.classes.forEach((umlClass: any, index: number) => {
      if (!umlClass.position) {
        umlClass.position = {
          x: startX + (index % columns) * horizontalGap,
          y: startY + Math.floor(index / columns) * verticalGap
        };
      }

      if (!umlClass.size) {
        umlClass.size = {
          width: 180,
          height: 110
        };
      }
    });
  }

  generateFromPrompt(prompt: string) {
    this.chatbot.isLoading.set(true);
    const currentUml = this.diagramService.exportToJson();
    this.chatbot.generateDiagram(prompt, currentUml).subscribe({
      next: (json) => {
        console.log('Respuesta del chatbot:', json);

        if (!json || json.error) {
          console.error('Respuesta inválida del chatbot:', json);
          alert(
            json?.error ||
            'La IA no devolvió un modelo UML válido.'
          );
          this.chatbot.isLoading.set(false);
          return;
        }

        this.diagramService.loadFromJson(json, true);
        this.chatbot.isLoading.set(false);
      },
      error: (err) => {
        console.error('Error al generar diagrama desde chatbot', err);
        this.chatbot.isLoading.set(false);
      }
    });
  }

  @HostListener('document:keydown', ['$event'])
  handleEscape(event: KeyboardEvent) {
    if (event.key === 'Delete' || event.key === 'Backspace') {
      this.diagramService.deleteSelected();
    }
    if (event.key === 'Escape') {
      this.diagramService.clearSelection();
    }
      // Atajos globales copiar, pegar, duplicar, cortar
      if (event.ctrlKey && event.key === 'c') {
        this.diagramService.clipboard = this.diagramService['copyUmlClass']?.(this.diagramService['selectedCell']);
        this.diagramService.clearSelection();
        event.preventDefault();
      }
        if (event.ctrlKey && event.key === 'v') {
          this.diagramService.clearSelection();
          if (this.diagramService.clipboard) {
            // Si hay posición de mouse, pegar ahí
            if (this.lastMousePos) {
              const model = { ...this.diagramService.clipboard, position: { ...this.lastMousePos } };
              this.diagramService['pasteUmlClass']?.(model);
            } else {
              this.diagramService['pasteUmlClass']?.(this.diagramService.clipboard);
            }
            this.diagramService.clearSelection();
          }
          event.preventDefault();
        }
      if (event.ctrlKey && event.key === 'x') {
        this.diagramService.clipboard = this.diagramService['copyUmlClass']?.(this.diagramService['selectedCell']);
        this.diagramService.deleteSelected();
        this.diagramService.clearSelection();
        event.preventDefault();
      }
      if (event.ctrlKey && event.key === 'd') {
        const clone = this.diagramService['copyUmlClass']?.(this.diagramService['selectedCell']);
        this.diagramService.clearSelection();
        this.diagramService['pasteUmlClass']?.(clone);
        event.preventDefault();
      }
  }
  
  @HostListener('window:resize')
  onResize() {
    if (this.diagramService['paper'] && this.paperContainer) {
      const rect = this.paperContainer.nativeElement.getBoundingClientRect();
      this.diagramService['paper'].setDimensions(rect.width, rect.height);
    }
  }


  onDragEnded(event: CdkDragEnd) {
    // Ejecutamos dentro de ngZone para asegurar la detección de cambios
    this.ngZone.run(() => {
      const type = (event.source.data as any).type;
      const { x, y } = event.dropPoint; // posición absoluta en pantalla

      // Ajustar posición relativa al canvas
      const rect = this.paperContainer.nativeElement.getBoundingClientRect();
      const pos = { x: x - rect.left, y: y - rect.top };

      console.log('Elemento arrastrado:', type, 'Posición:', pos);

      if (type === 'class') {
        try {
          // Crear un modelo de clase UML
          const umlClassModel: UmlClass = {
            name: 'Entidad',
            position: pos,
            size: { width: 180, height: 110 },
            attributes: [
              { name: 'id', type: 'int' },
              { name: 'nombre', type: 'string' }
            ],
            methods: [
              { name: 'crear' },
              { name: 'eliminar' }
            ]
          };
          
          // Usar el servicio para crear la clase UML
          this.diagramService.createUmlClass(umlClassModel);
          console.log('Entidad UML creada correctamente');
        } catch (error) {
          console.error('Error al crear el elemento:', error);
          
          // Si falla, usamos el fallback HTML
          const fallbackClass: UmlClass = {
            name: 'Entidad',
            position: pos,
            attributes: [
              { name: 'id', type: 'int' },
              { name: 'nombre', type: 'string' }
            ],
            methods: [
              { name: 'crear' },
              { name: 'eliminar' }
            ]
          };
          
          this.fallbackService.createFallbackElement(
            this.paperContainer.nativeElement, 
            fallbackClass
          );
        }
      }

      if (['association','generalization','aggregation','composition','dependency'].includes(type)) {
        this.relationshipService.startLinkCreation(
          this.diagramService['paper'],
          this.paperContainer.nativeElement,
          type // 👈 pasamos el tipo
        );
        console.log(`Modo de creación de relación activado: ${type}`);
      }

    });
  }
  ngOnDestroy(): void {
    // Red de seguridad: si el usuario abandona la sala por cualquier vía que
    // no sea el botón "Home" (back button, otro enlace, cierre de pestaña
    // detectado por Angular al destruir la ruta), esto garantiza que el
    // backup final se envíe y el socket de colaboración se cierre, evitando
    // usuarios fantasma en la sala.
    if (this.roomId) {
      this.diagramService.leaveRoom(this.roomId);
    }
  }

  zoomIn() {
    this.diagramService.zoomIn();
  }

  zoomOut() {
    this.diagramService.zoomOut();
  }

  resetZoom() {
    this.diagramService.resetZoom();
  }
}
