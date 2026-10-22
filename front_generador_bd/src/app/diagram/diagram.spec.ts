import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { P2PService } from '../../services/colaboration/p2p.service';
import { DiagramService } from '../../services/diagram/diagram.service';

import { Diagram } from './diagram';

describe('Diagram', () => {
  let component: Diagram;
  let fixture: ComponentFixture<Diagram>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Diagram],
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => 'sala-prueba' } } } }
      ]
    })
    .compileComponents();

    // Solo se instancia: detectChanges() arrancaría JointJS y la colaboración
    // (WebSocket), que no son lo que verifica esta prueba de cableado.
    fixture = TestBed.createComponent(Diagram);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('tells an expelled participant and sends them back to the start page', () => {
    const alertSpy = spyOn(window, 'alert');
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    const diagram = TestBed.inject(DiagramService);
    const clearStorage = spyOn(diagram, 'clearStorage');
    const closeDiagram = spyOn(diagram, 'closeDiagram');
    (component as any).roomId = 'sala-prueba';

    TestBed.inject(P2PService).removed.set(true);
    TestBed.tick();

    expect(alertSpy).toHaveBeenCalledOnceWith('El host te expulsó de la sala.');
    expect(clearStorage).toHaveBeenCalled();
    // Su copia puede estar atrasada: no debe guardar un respaldo final.
    expect(closeDiagram).toHaveBeenCalledOnceWith('sala-prueba', { saveBackup: false });
    expect(navigate).toHaveBeenCalledOnceWith(['/']);
  });

  it('does nothing while nobody has been expelled', () => {
    const alertSpy = spyOn(window, 'alert');

    TestBed.tick();

    expect(alertSpy).not.toHaveBeenCalled();
  });
});
