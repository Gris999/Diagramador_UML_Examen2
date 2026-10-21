import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';

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
});
