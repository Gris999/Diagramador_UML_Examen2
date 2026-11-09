import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { TOOL_NAMES, ToolService, isToolType } from './tool.service';

describe('ToolService', () => {
  let tools: ToolService;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideZonelessChangeDetection()] });
    tools = TestBed.inject(ToolService);
  });

  it('starts with no tool chosen and nothing to say', () => {
    expect(tools.armed()).toBeNull();
    expect(tools.hint()).toBe('');
  });

  it('chooses a tool with one call and says what to do next', () => {
    tools.arm('class');

    expect(tools.armed()).toBe('class');
    expect(tools.hint()).toContain('Haz clic en el lienzo');
    expect(tools.hint()).toContain('Esc');
  });

  it('for a relationship, first asks for the origin class and then for the destination', () => {
    tools.arm('generalization');
    expect(tools.hint()).toContain('origen de la herencia');

    tools.chosen.set(1);

    expect(tools.hint()).toContain('clase de destino');
  });

  it('for an association class, asks for a class or the line, in any order', () => {
    tools.arm('association-class');
    expect(tools.hint()).toContain('una clase o en la línea');

    tools.chosen.set(1);

    expect(tools.hint()).toContain('la otra');
  });

  it('changes the tool when another is chosen and forgets the progress', () => {
    tools.arm('association');
    tools.chosen.set(1);

    tools.arm('composition');

    expect(tools.armed()).toBe('composition');
    expect(tools.chosen()).toBe(0);
  });

  it('toggle drops the tool when the same one is chosen again', () => {
    tools.toggle('dependency');
    expect(tools.armed()).toBe('dependency');

    tools.toggle('dependency');

    expect(tools.armed()).toBeNull();
  });

  it('clear drops the tool and the progress', () => {
    tools.arm('aggregation');
    tools.chosen.set(1);

    tools.clear();

    expect(tools.armed()).toBeNull();
    expect(tools.chosen()).toBe(0);
    expect(tools.hint()).toBe('');
  });

  it('knows which names are tools', () => {
    for (const name of Object.keys(TOOL_NAMES)) expect(isToolType(name)).toBeTrue();
    expect(isToolType('circulo')).toBeFalse();
    expect(isToolType(undefined)).toBeFalse();
  });
});
