import { PLATFORM_ID, provideZonelessChangeDetection, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { ChatbotService } from '../../services/IA/chatbot.service';
import { UmlValidationService } from '../../services/colaboration/uml-validation.service';
import { DiagramService } from '../../services/diagram/diagram.service';
import { BackendGeneratorService } from '../../services/exports/backend-generator.service';
import { FrontendGeneratorService } from '../../services/exports/frontend-generator.service';
import { SqlExportService } from '../../services/exports/sql-export.service';
import { UmlImageServiceTs } from '../../services/imports/uml-image.service';
import { SidePanel } from './side-panel';

describe('SidePanel image import choices', () => {
  let component: SidePanel;
  let fixture: ComponentFixture<SidePanel>;
  let diagramService: any;
  let imageService: any;
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
      exportToImage: jasmine.createSpy('exportToImage')
    };
    imageService = {
      loading: signal(false),
      analyzeImage: jasmine.createSpy('analyzeImage')
    };

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
        { provide: SqlExportService, useValue: { downloadSql: jasmine.createSpy('downloadSql') } },
        { provide: FrontendGeneratorService, useValue: { loading: signal(false), generateFrontend: jasmine.createSpy('generateFrontend') } },
        { provide: ChatbotService, useValue: { isLoading: signal(false) } },
        { provide: BackendGeneratorService, useValue: { loading: signal(false) } },
        { provide: PLATFORM_ID, useValue: 'browser' }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SidePanel);
    component = fixture.componentInstance;
    fixture.detectChanges();
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
});
