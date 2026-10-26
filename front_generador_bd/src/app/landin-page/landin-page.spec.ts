import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { validate as isUuid } from 'uuid';

import { LandinPage } from './landin-page';

describe('LandinPage', () => {
  let component: LandinPage;
  let fixture: ComponentFixture<LandinPage>;

  let navigate: jasmine.Spy;

  function element(selector: string): HTMLElement | null {
    return (fixture.nativeElement as HTMLElement).querySelector(selector);
  }

  function typeCode(code: string): void {
    const input = element('input') as HTMLInputElement;
    input.value = code;
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }

  function clickJoin(): void {
    const buttons = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button')) as HTMLButtonElement[];
    buttons.find(button => button.textContent?.includes('Unirse al Lienzo'))!.click();
    fixture.detectChanges();
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LandinPage],
      providers: [provideZonelessChangeDetection(), provideRouter([]), provideHttpClient(), provideHttpClientTesting()]
    })
    .compileComponents();

    navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
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

  it('creates a new room with a unique code and opens its editor', () => {
    component.crearNuevoLienzo();
    component.crearNuevoLienzo();

    const [first, second] = navigate.calls.allArgs().map(args => args[0] as string[]);
    expect(first[0]).toBe('/diagram');
    expect(isUuid(first[1])).toBeTrue();
    expect(isUuid(second[1])).toBeTrue();
    expect(first[1]).not.toBe(second[1]);
  });

  it('joins the room whose code is typed, ignoring spaces and capital letters', async () => {
    typeCode('  3F2A9C1E-5B7D-4E8A-9C3B-1A2B3C4D5E6F  ');
    await fixture.whenStable();

    clickJoin();

    expect(navigate).toHaveBeenCalledOnceWith(['/diagram', '3f2a9c1e-5b7d-4e8a-9c3b-1a2b3c4d5e6f']);
    expect(element('[data-testid="join-error"]')).toBeNull();
  });

  it('does not join with something that is not a room code and tells the person why', async () => {
    typeCode('mi-sala');
    await fixture.whenStable();

    clickJoin();

    expect(navigate).not.toHaveBeenCalled();
    expect(element('[data-testid="join-error"]')!.textContent).toContain('El código no es válido');
  });

  it('clears the warning when the person edits the code again', async () => {
    typeCode('mi-sala');
    await fixture.whenStable();
    clickJoin();

    typeCode('mi-sala-2');
    await fixture.whenStable();
    fixture.detectChanges();

    expect(element('[data-testid="join-error"]')).toBeNull();
  });

  it('does not let a person join without typing a code', () => {
    const join = (Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button')) as HTMLButtonElement[]).find(button =>
      button.textContent?.includes('Unirse al Lienzo')
    )!;

    expect(join.disabled).toBeTrue();
  });
});
