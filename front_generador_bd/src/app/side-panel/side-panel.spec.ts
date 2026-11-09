import { PLATFORM_ID, provideZonelessChangeDetection, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { of, Subject, throwError } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';
import { IaActionsService } from '../../services/IA/ia-actions.service';
import { ChatbotService } from '../../services/IA/chatbot.service';
import { UmlValidationService } from '../../services/colaboration/uml-validation.service';
import { DiagramService } from '../../services/diagram/diagram.service';
import { BackendGeneratorService } from '../../services/exports/backend-generator.service';
import { FrontendGeneratorService } from '../../services/exports/frontend-generator.service';
import { FullProjectGeneratorService } from '../../services/exports/full-project-generator.service';
import { SqlExportService } from '../../services/exports/sql-export.service';
import { UmlImageServiceTs } from '../../services/imports/uml-image.service';
import { ToolService } from '../../services/diagram/tool.service';
import { SidePanel } from './side-panel';

describe('SidePanel image import choices', () => {
  let component: SidePanel;
  let fixture: ComponentFixture<SidePanel>;
  let diagramService: any;
  let imageService: any;
  let iaActions: any;
  let chatbot: any;
  let frontendGenerator: any;
  let fullProjectGenerator: any;
  let diagramClasses: string[];

  const generatedUml = {
    classes: [{ id: 'generated-1', name: 'GeneratedClass' }],
    relationships: []
  };

  function imageEvent() {
    const input = {
      files: [new File(['image'], 'diagram.png', { type: 'image/png' })],
      value: 'selected-image'
    } as any;

    return {
      event: { target: input } as unknown as Event,
      input
    };
  }

  function importGeneratedUml() {
    imageService.analyzeImage.and.returnValue(of({ uml_json: generatedUml }));
    const { event, input } = imageEvent();
    component.onImportImage(event);
    fixture.detectChanges();
    return input;
  }

  beforeEach(async () => {
    diagramClasses = ['ExistingClass'];
    diagramService = {
      hasDiagramElements: jasmine.createSpy('hasDiagramElements')
        .and.callFake(() => diagramClasses.length > 0),
      loadFromJson: jasmine.createSpy('loadFromJson').and.callFake((uml: any) => {
        diagramClasses.push(...uml.classes.map((item: any) => item.name));
      }),
      replaceDiagramFromImage: jasmine.createSpy('replaceDiagramFromImage')
        .and.callFake((uml: any) => {
          diagramClasses = uml.classes.map((item: any) => item.name);
        }),
      exportToJson: jasmine.createSpy('exportToJson').and.returnValue({
        classes: [],
        relationships: []
      }),
      clearStorage: jasmine.createSpy('clearStorage'),
      closeDiagram: jasmine.createSpy('closeDiagram'),
      exportToImage: jasmine.createSpy('exportToImage'),
      exportForGenerators: jasmine.createSpy('exportForGenerators').and.returnValue({
        classes: [{ id: 'a', name: 'Alumno' }],
        relationships: []
      })
    };
    frontendGenerator = { loading: signal(false), generateFrontend: jasmine.createSpy('generateFrontend') };
    fullProjectGenerator = { loading: signal(false), generateAll: jasmine.createSpy('generateAll') };
    imageService = {
      loading: signal(false),
      analyzeImage: jasmine.createSpy('analyzeImage')
    };
    iaActions = { request: jasmine.createSpy('request').and.returnValue(of({ reply: 'Listo' })) };
    chatbot = { isLoading: signal(false), transcribeAudio: jasmine.createSpy('transcribeAudio') };

    await TestBed.configureTestingModule({
      imports: [SidePanel],
      providers: [
        provideZonelessChangeDetection(),
        { provide: DiagramService, useValue: diagramService },
        { provide: UmlImageServiceTs, useValue: imageService },
        { provide: UmlValidationService, useValue: { validateModel: jasmine.createSpy('validateModel') } },
        { provide: Router, useValue: { navigate: jasmine.createSpy('navigate') } },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => 'room-1' } } }
        },
        { provide: SqlExportService, useValue: { downloadSql: jasmine.createSpy('downloadSql'), exportToSql: jasmine.createSpy('exportToSql').and.returnValue('CREATE TABLE alumno();') } },
        { provide: FrontendGeneratorService, useValue: frontendGenerator },
        { provide: FullProjectGeneratorService, useValue: fullProjectGenerator },
        { provide: ChatbotService, useValue: chatbot },
        { provide: IaActionsService, useValue: iaActions },
        { provide: BackendGeneratorService, useValue: { loading: signal(false) } },
        { provide: PLATFORM_ID, useValue: 'browser' }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SidePanel);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  describe('choosing a tool of the palette with a click', () => {
    const tile = (type: string) => fixture.nativeElement.querySelector(`[data-testid="tool-${type}"]`) as HTMLElement;

    it('chooses a class or a relationship with one click, and marks it', () => {
      tile('association').click();
      fixture.detectChanges();

      expect(TestBed.inject(ToolService).armed()).toBe('association');
      expect(tile('association').classList).toContain('palette-armed');
      expect(tile('association').getAttribute('aria-pressed')).toBe('true');
      expect(tile('class').getAttribute('aria-pressed')).toBe('false');
    });

    it('a second click on the same tool lets it go', () => {
      tile('class').click();
      tile('class').click();
      fixture.detectChanges();

      expect(TestBed.inject(ToolService).armed()).toBeNull();
      expect(tile('class').classList).not.toContain('palette-armed');
    });

    it('choosing another tool replaces the first', () => {
      tile('class').click();
      tile('generalization').click();

      expect(TestBed.inject(ToolService).armed()).toBe('generalization');
    });

    it('works from the keyboard with Enter and with Space', () => {
      tile('dependency').dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
      expect(TestBed.inject(ToolService).armed()).toBe('dependency');

      tile('dependency').dispatchEvent(new KeyboardEvent('keydown', { key: ' ' }));
      expect(TestBed.inject(ToolService).armed()).toBeNull();
    });

    it('is a button for the screen readers and can be reached with the keyboard', () => {
      for (const type of ['class', 'association', 'generalization', 'aggregation', 'composition', 'dependency', 'association-class']) {
        expect(tile(type).getAttribute('role')).toBe('button');
        expect(tile(type).getAttribute('tabindex')).toBe('0');
      }
    });

    it('the click some browsers send right after dropping a dragged tile does not count as choosing it', () => {
      component.onDragEnded({ source: { reset: () => undefined } } as any);

      tile('class').click();

      expect(TestBed.inject(ToolService).armed()).toBeNull();
    });

    it('still passes the drag to the canvas', () => {
      const dragged = jasmine.createSpy('dragged');
      component.elementDragged.subscribe(dragged);

      component.onDragEnded({ source: { reset: () => undefined } } as any);

      expect(dragged).toHaveBeenCalled();
    });
  });

  describe('exporting the mobile app and the full project', () => {
    beforeEach(() => localStorage.removeItem('uml-app-name'));

    function typeName(name: string) {
      const input = fixture.nativeElement.querySelector('[data-testid="app-name-input"]') as HTMLInputElement;
      input.value = name;
      input.dispatchEvent(new Event('input'));
      fixture.detectChanges();
    }

    function confirm() {
      (fixture.nativeElement.querySelector('[data-testid="confirm-app-name"]') as HTMLButtonElement).click();
      fixture.detectChanges();
    }

    it('asks for the app name before exporting the Flutter project and sends it with the diagram', () => {
      component.onGenerateFrontend();
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('[data-testid="app-name-dialog"]')).not.toBeNull();
      expect(frontendGenerator.generateFrontend).not.toHaveBeenCalled();

      typeName('Sistema Escolar');
      confirm();

      expect(frontendGenerator.generateFrontend).toHaveBeenCalledOnceWith(
        { classes: [{ id: 'a', name: 'Alumno' }], relationships: [], appName: 'Sistema Escolar' },
        'sistema-escolar-app-movil.zip'
      );
      expect(fixture.nativeElement.querySelector('[data-testid="app-name-dialog"]')).toBeNull();
    });

    it('downloads backend, mobile app, SQL and instructions in a single ZIP', () => {
      component.onGenerateAll();
      fixture.detectChanges();
      typeName('Gestión Contable');
      confirm();

      expect(fullProjectGenerator.generateAll).toHaveBeenCalledOnceWith(
        {
          classes: [{ id: 'a', name: 'Alumno' }],
          relationships: [],
          appName: 'Gestión Contable',
          sqlScript: 'CREATE TABLE alumno();'
        },
        'gestion-contable.zip'
      );
      expect(frontendGenerator.generateFrontend).not.toHaveBeenCalled();
    });

    it('lets the name stay empty (the server then picks a neutral one) and remembers the last name', () => {
      component.onGenerateAll();
      fixture.detectChanges();
      confirm();

      expect(fullProjectGenerator.generateAll.calls.mostRecent().args[0].appName).toBe('');
      expect(fullProjectGenerator.generateAll.calls.mostRecent().args[1]).toBe('mi-aplicacion.zip');

      component.onGenerateFrontend();
      fixture.detectChanges();
      typeName('Mi Tienda');
      confirm();
      component.onGenerateAll();
      expect(component.appNameDraft()).toBe('Mi Tienda');
    });

    it('does not export anything when the dialog is cancelled', () => {
      component.onGenerateAll();
      fixture.detectChanges();
      (fixture.nativeElement.querySelector('[data-testid="cancel-app-name"]') as HTMLButtonElement).click();
      fixture.detectChanges();

      expect(fullProjectGenerator.generateAll).not.toHaveBeenCalled();
      expect(frontendGenerator.generateFrontend).not.toHaveBeenCalled();
      expect(fixture.nativeElement.querySelector('[data-testid="app-name-dialog"]')).toBeNull();
    });

    it('closes the app name dialog with Escape without exporting, and Escape still cancels an image import', () => {
      component.onGenerateAll();
      fixture.detectChanges();
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
      fixture.detectChanges();

      expect(component.appNameDialogOpen()).toBeFalse();
      expect(fullProjectGenerator.generateAll).not.toHaveBeenCalled();

      importGeneratedUml();
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
      expect(component.imageImportDialogOpen()).toBeFalse();
    });

    it('shows the full project button in the export actions', () => {
      component.showActions = true;
      fixture.detectChanges();
      const button = fixture.nativeElement.querySelector('[data-testid="export-all"]') as HTMLButtonElement;
      expect(button?.textContent).toContain('Descargar proyecto completo');
    });
  });

  it('imports immediately without a dialog when the diagram is empty', () => {
    diagramClasses = [];
    const input = importGeneratedUml();

    expect(diagramService.loadFromJson).toHaveBeenCalledOnceWith(generatedUml);
    expect(diagramService.replaceDiagramFromImage).not.toHaveBeenCalled();
    expect(component.imageImportDialogOpen()).toBeFalse();
    expect(fixture.nativeElement.querySelector('[data-testid="image-import-dialog"]')).toBeNull();
    expect(diagramClasses).toEqual(['GeneratedClass']);
    expect(input.value).toBe('');
  });

  it('opens the dialog without applying a valid result to a non-empty diagram', () => {
    importGeneratedUml();

    const dialog = fixture.nativeElement.querySelector(
      '[data-testid="image-import-dialog"]'
    ) as HTMLElement;
    expect(dialog).not.toBeNull();
    expect(dialog.textContent).toContain('El diagrama ya contiene elementos');
    expect(dialog.textContent).toContain('¿Qué deseas hacer con el diagrama generado desde la imagen?');
    expect(diagramService.loadFromJson).not.toHaveBeenCalled();
    expect(diagramService.replaceDiagramFromImage).not.toHaveBeenCalled();
    expect(diagramClasses).toEqual(['ExistingClass']);
  });

  it('replaces the existing diagram and clears the pending result', () => {
    importGeneratedUml();

    const replaceButton = fixture.nativeElement.querySelector(
      '[data-testid="replace-image-import"]'
    ) as HTMLButtonElement;
    replaceButton.click();
    fixture.detectChanges();

    expect(diagramService.replaceDiagramFromImage).toHaveBeenCalledOnceWith(generatedUml);
    expect(diagramService.loadFromJson).not.toHaveBeenCalled();
    expect(diagramClasses).toEqual(['GeneratedClass']);
    expect(component.imageImportDialogOpen()).toBeFalse();
    expect(fixture.nativeElement.querySelector('[data-testid="image-import-dialog"]')).toBeNull();

    component.replaceImageImport();
    expect(diagramService.replaceDiagramFromImage).toHaveBeenCalledTimes(1);
  });

  it('merges into the existing diagram and clears the pending result', () => {
    importGeneratedUml();

    const mergeButton = fixture.nativeElement.querySelector(
      '[data-testid="merge-image-import"]'
    ) as HTMLButtonElement;
    mergeButton.click();
    fixture.detectChanges();

    expect(diagramService.loadFromJson).toHaveBeenCalledOnceWith(generatedUml);
    expect(diagramService.replaceDiagramFromImage).not.toHaveBeenCalled();
    expect(diagramClasses).toEqual(['ExistingClass', 'GeneratedClass']);
    expect(component.imageImportDialogOpen()).toBeFalse();

    component.mergeImageImport();
    expect(diagramService.loadFromJson).toHaveBeenCalledTimes(1);
  });

  it('cancels without changing the graph and clears the pending result', () => {
    importGeneratedUml();

    const cancelButton = fixture.nativeElement.querySelector(
      '[data-testid="cancel-image-import"]'
    ) as HTMLButtonElement;
    cancelButton.click();
    fixture.detectChanges();

    expect(diagramService.loadFromJson).not.toHaveBeenCalled();
    expect(diagramService.replaceDiagramFromImage).not.toHaveBeenCalled();
    expect(diagramClasses).toEqual(['ExistingClass']);
    expect(component.imageImportDialogOpen()).toBeFalse();

    component.mergeImageImport();
    expect(diagramService.loadFromJson).not.toHaveBeenCalled();
  });

  it('cancels the pending import on Escape', () => {
    importGeneratedUml();

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    fixture.detectChanges();

    expect(component.imageImportDialogOpen()).toBeFalse();
    expect(diagramClasses).toEqual(['ExistingClass']);
    expect(diagramService.loadFromJson).not.toHaveBeenCalled();
  });

  it('preserves the existing invalid-response handling', () => {
    const alertSpy = spyOn(window, 'alert');
    imageService.analyzeImage.and.returnValue(of({ error: 'Invalid image result' }));
    const { event, input } = imageEvent();

    component.onImportImage(event);

    expect(alertSpy).toHaveBeenCalledOnceWith('Invalid image result');
    expect(diagramService.loadFromJson).not.toHaveBeenCalled();
    expect(component.imageImportDialogOpen()).toBeFalse();
    expect(component.analyzingModel()).toBeFalse();
    expect(imageService.loading()).toBeFalse();
    expect(input.value).toBe('');
  });

  it('preserves the existing provider-error handling', () => {
    spyOn(console, 'error');
    imageService.analyzeImage.and.returnValue(
      throwError(() => new Error('Provider unavailable'))
    );
    const { event } = imageEvent();

    component.onImportImage(event);

    expect(console.error).toHaveBeenCalled();
    expect(diagramService.loadFromJson).not.toHaveBeenCalled();
    expect(diagramService.replaceDiagramFromImage).not.toHaveBeenCalled();
    expect(component.imageImportDialogOpen()).toBeFalse();
    expect(component.analyzingModel()).toBeFalse();
    expect(imageService.loading()).toBeFalse();
  });

  describe('Generar modelo (C1): la instrucción pasa por el control de la IA de la sala', () => {
    it('sends the instruction to the AI as a change request for this room and clears the box when it works', () => {
      component.prompt = '  agrega la clase Factura  ';

      component.onGenerate();

      expect(iaActions.request).toHaveBeenCalledOnceWith('room-1', 'change', 'agrega la clase Factura');
      expect(component.prompt).toBe('');
      expect(chatbot.isLoading()).toBeFalse();
    });

    it('does nothing with an empty instruction', () => {
      component.prompt = '   ';

      component.onGenerate();

      expect(iaActions.request).not.toHaveBeenCalled();
    });

    it('shows that it is working and ignores a second click while the AI answers', () => {
      const pending = new Subject<any>();
      iaActions.request.and.returnValue(pending);
      component.prompt = 'agrega Factura';

      component.onGenerate();
      component.onGenerate();

      expect(chatbot.isLoading()).toBeTrue();
      expect(iaActions.request).toHaveBeenCalledTimes(1);
      pending.next({ reply: 'Listo' });
      pending.complete();
      expect(chatbot.isLoading()).toBeFalse();
    });

    it('keeps the text and tells the user when the AI fails', () => {
      const alertSpy = spyOn(window, 'alert');
      iaActions.request.and.returnValue(throwError(() => new HttpErrorResponse({ status: 502 })));
      component.prompt = 'agrega Factura';

      component.onGenerate();

      expect(alertSpy).toHaveBeenCalledOnceWith(jasmine.stringContaining('La IA no pudo responder ahora'));
      expect(component.prompt).toBe('agrega Factura');
      expect(chatbot.isLoading()).toBeFalse();
    });

    it('tells who is being served when the AI is busy with someone else', () => {
      const alertSpy = spyOn(window, 'alert');
      iaActions.request.and.returnValue(throwError(() => new HttpErrorResponse({
        status: 409, error: { error: 'La IA está atendiendo a Beto. Espera a que termine.' }
      })));
      component.prompt = 'agrega Factura';

      component.onGenerate();

      expect(alertSpy).toHaveBeenCalledOnceWith('La IA está atendiendo a Beto. Espera a que termine.');
    });

    it('dictation only transcribes and then follows the same path as the typed instruction', () => {
      chatbot.transcribeAudio.and.returnValue(of({ transcript: 'agrega una clase Cliente' }));

      (component as any).processVoiceAudio(new Blob(['audio'], { type: 'audio/webm' }));

      expect(chatbot.transcribeAudio).toHaveBeenCalledTimes(1);
      expect(iaActions.request).toHaveBeenCalledOnceWith('room-1', 'change', 'agrega una clase Cliente');
    });

    it('does not ask the AI when nothing could be understood from the audio', () => {
      const alertSpy = spyOn(window, 'alert');
      chatbot.transcribeAudio.and.returnValue(of({ transcript: '  ' }));

      (component as any).processVoiceAudio(new Blob(['audio'], { type: 'audio/webm' }));

      expect(alertSpy).toHaveBeenCalledTimes(1);
      expect(iaActions.request).not.toHaveBeenCalled();
      expect(chatbot.isLoading()).toBeFalse();
    });

    it('tells the user when the audio cannot be processed', () => {
      const alertSpy = spyOn(window, 'alert');
      spyOn(console, 'error');
      chatbot.transcribeAudio.and.returnValue(throwError(() => new HttpErrorResponse({ status: 502 })));

      (component as any).processVoiceAudio(new Blob(['audio'], { type: 'audio/webm' }));

      expect(alertSpy).toHaveBeenCalledOnceWith('No se pudo procesar la instrucción de voz.');
      expect(iaActions.request).not.toHaveBeenCalled();
      expect(chatbot.isLoading()).toBeFalse();
    });
  });
});
