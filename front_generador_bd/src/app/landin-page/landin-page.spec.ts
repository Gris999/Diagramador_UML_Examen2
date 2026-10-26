import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { LandinPage } from './landin-page';

describe('LandinPage', () => {
  let component: LandinPage;
  let fixture: ComponentFixture<LandinPage>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LandinPage],
      providers: [provideZonelessChangeDetection(), provideRouter([]), provideHttpClient(), provideHttpClientTesting()]
    })
    .compileComponents();

    fixture = TestBed.createComponent(LandinPage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('offers the help assistant before entering any room', () => {
    const help = (fixture.nativeElement as HTMLElement).querySelector('app-help-panel [data-testid="help-toggle"]');

    expect(help).not.toBeNull();
    expect(help!.textContent).toContain('Ayuda');
  });
});
