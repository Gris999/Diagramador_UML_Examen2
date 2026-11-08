import { AfterViewInit, Component, computed, effect, ElementRef, HostListener, inject, Inject, NgZone, OnDestroy, PLATFORM_ID, signal, ViewChild } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { CdkDragEnd, CdkDropListGroup, CdkDropList } from '@angular/cdk/drag-drop';
import { SidePanel } from "../side-panel/side-panel";
import { DiagramService } from '../../services/diagram/diagram.service';
import { FallbackService } from '../../services/diagram/fallback.service';
import { RelationshipService } from '../../services/diagram/relationship.service';
import { UmlClass, Attribute, Method } from '../../models/uml-class.model';
import { DiagramExportService } from '../../services/exports/diagram-export.service';
import { BackendGeneratorService } from '../../services/exports/backend-generator.service';
import { UmlValidationService } from '../../services/colaboration/uml-validation.service';
import { ActivatedRoute, Router } from '@angular/router';
import { XmiService } from '../../services/interop/xmi.service';
import { ParticipantsPanel } from '../participants-panel/participants-panel';
import { P2PService } from '../../services/colaboration/p2p.service';
import { ActivityPanel } from '../activity-panel/activity-panel';
import { HelpPanel } from '../help-panel/help-panel';
import { IaChatPanel } from '../ia-chat-panel/ia-chat-panel';
import { ShareDialog } from '../share-dialog/share-dialog';
import { avatarColor, avatarInitial } from '../participants-panel/avatar';
import { ThemeService } from '../../services/theme.service';

/** Cuántos círculos de personas se ven en la barra superior; el resto se resume en «+N». */
const MAX_AVATARS = 3;

type TopMenu = 'activity' | 'participants';

@Component({
  selector: 'app-diagram',
  standalone: true,
  templateUrl: './diagram.html',
  styleUrls: ['./diagram.css'],
  imports: [SidePanel, CdkDropListGroup, CdkDropList, ParticipantsPanel, ActivityPanel, IaChatPanel, HelpPanel, ShareDialog]
})
export class Diagram implements AfterViewInit, OnDestroy {
  @ViewChild('paperContainer', { static: true }) paperContainer!: ElementRef;
  @ViewChild(SidePanel) sidePanel!: SidePanel;

  readonly theme = inject(ThemeService);

  /** Código de la sala (sale de la dirección): con él se arman los enlaces de «Compartir». */
  readonly roomCode: string;

  /** Panel de herramientas de la izquierda: se puede ocultar para dar más lugar al lienzo. */
  readonly sidebarOpen = signal(true);
  /** Menú de la barra superior que está abierto (solo uno a la vez). */
  readonly menu = signal<TopMenu | null>(null);
  readonly shareOpen = signal(false);
  /** Sin ninguna clase todavía: el lienzo muestra una pista de cómo empezar. */
  readonly isEmpty = signal(true);

  readonly participantList = computed(() => this.p2p.participants());
  readonly visiblePeople = computed(() => this.participantList().slice(0, MAX_AVATARS));
  readonly hiddenPeople = computed(() => Math.max(0, this.participantList().length - MAX_AVATARS));
  readonly avatarColor = avatarColor;
  readonly avatarInitial = avatarInitial;

  /** Último evento de actividad que la persona ya vio: lo que llega después se cuenta como novedad en el botón «Actividad». */
  private readonly seenEventId = signal(0);
  readonly unreadActivity = computed(() =>
    this.menu() === 'activity'
      ? 0
      : this.p2p.liveActivityEvents().filter(event => event.id > this.seenEventId()).length
  );

  private lastMousePos: { x: number; y: number } | null = null;
  private roomId: string | null = null;

  constructor(
    @Inject(PLATFORM_ID) private platformId: Object,
    private ngZone: NgZone,
    private diagramService: DiagramService,
    private fallbackService: FallbackService,
    private relationshipService: RelationshipService,
    private exportService: DiagramExportService,
    private backendGen: BackendGeneratorService,
    private umlValidation: UmlValidationService,
    private route: ActivatedRoute,
    private xmiService: XmiService,
    private p2p: P2PService,
    private router: Router
  ) {
    // El servicio de colaboración vive toda la sesión: si esta persona fue expulsada antes y vuelve a entrar sin recargar la página, su expulsión
    // anterior no cuenta (entra como una persona nueva, CU4).
    this.roomCode = this.route.snapshot.paramMap.get('roomId') ?? '';
    this.p2p.removed.set(false);
    // Si el host expulsa a esta persona, la conexión se cierra: se le avisa y
    // vuelve al inicio en lugar de quedarse con una sala congelada.
    effect(() => {
      if (!this.p2p.removed() || !isPlatformBrowser(this.platformId)) return;
      alert('El host te expulsó de la sala.');
      this.leaveAfterRemoval();
    });
  }

  private leaveAfterRemoval(): void {
    this.diagramService.clearStorage();
    // El respaldo final lo guardan quienes siguen en la sala, no quien fue expulsado.
    if (this.roomId) this.diagramService.closeDiagram(this.roomId, { saveBackup: false });
    this.router.navigate(['/']);
  }
  
  async ngAfterViewInit(): Promise<void> {
    if (isPlatformBrowser(this.platformId)) {
      this.ngZone.run(async () => {
        try {
          const roomId = this.route.snapshot.paramMap.get('roomId') || 'default-room';
          this.roomId = roomId;
          await this.diagramService.initialize(this.paperContainer.nativeElement, roomId);
          this.refreshEmpty();
          this.diagramService.watchGraph(() => this.refreshEmpty());
          
          this.sidePanel.elementDragged.subscribe((event: CdkDragEnd) => {
            this.onDragEnded(event);
          });

          this.sidePanel.saveClicked.subscribe(() => this.saveDiagram());

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
    const json = this.diagramService.exportForGenerators();
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

  @HostListener('document:keydown', ['$event'])
  handleEscape(event: KeyboardEvent) {
    if (event.key === 'Delete' || event.key === 'Backspace') {
      this.diagramService.deleteSelected();
    }
    if (event.key === 'Escape') {
      this.diagramService.clearSelection();
      this.setMenu(null);
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

      if (['association','generalization','aggregation','composition','dependency','association-class'].includes(type)) {
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

  private refreshEmpty(): void {
    this.isEmpty.set(!this.diagramService.hasDiagramElements());
  }

  toggleSidebar(): void {
    this.sidebarOpen.update(open => !open);
  }

  toggleMenu(which: TopMenu): void {
    this.setMenu(this.menu() === which ? null : which);
  }

  openShare(): void {
    this.setMenu(null);
    this.shareOpen.set(true);
  }

  /** Nombre que se muestra de una persona: el que dio o, si no hay, su lugar en la lista. */
  personName(person: { name?: string | null }, index: number): string {
    return person.name || 'Usuario ' + (index + 1);
  }

  /** Tocar fuera de los menús los cierra. */
  @HostListener('document:click', ['$event'])
  closeMenuOnOutsideClick(event: MouseEvent): void {
    if (this.menu() === null) return;
    const target = event.target as HTMLElement | null;
    if (target?.closest?.('[data-menu-root]')) return;
    this.setMenu(null);
  }

  private setMenu(next: TopMenu | null): void {
    // Al abrir o cerrar «Actividad» todo lo que hay hasta ese momento cuenta como visto.
    if (this.menu() === 'activity' || next === 'activity') this.markActivitySeen();
    this.menu.set(next);
  }

  private markActivitySeen(): void {
    const newest = this.p2p.liveActivityEvents().reduce((max, event) => Math.max(max, event.id), this.seenEventId());
    this.seenEventId.set(newest);
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
