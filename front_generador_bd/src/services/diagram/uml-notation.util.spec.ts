import {
  attributeToLine,
  attributesToText,
  isCodeEntity,
  keepVisibility,
  kindOf,
  methodToLine,
  methodsToText,
  nameDisplay,
  parseAttributeLine,
  parseMethodLine,
  splitVisibility,
  stereotypeOf
} from './uml-notation.util';

describe('UML notation: class kind', () => {
  it('treats anything that is not a known kind as a plain class', () => {
    expect(kindOf(undefined)).toBe('class');
    expect(kindOf('otra cosa')).toBe('class');
    expect(kindOf('interface')).toBe('interface');
  });

  it('shows the stereotype on its own line above the name, only for interfaces and enumerations', () => {
    expect(stereotypeOf('interface')).toBe('«interface»');
    expect(stereotypeOf('enumeration')).toBe('«enumeration»');
    expect(stereotypeOf('abstract')).toBe('');
    expect(nameDisplay('Pago', 'interface')).toBe('«interface»\nPago');
    expect(nameDisplay('Pago', 'class')).toBe('Pago');
  });

  it('only classes and abstract classes become code entities', () => {
    expect(isCodeEntity(undefined)).toBeTrue();
    expect(isCodeEntity('abstract')).toBeTrue();
    expect(isCodeEntity('interface')).toBeFalse();
    expect(isCodeEntity('enumeration')).toBeFalse();
  });
});

describe('UML notation: visibility', () => {
  it('splits the sign from the member', () => {
    expect(splitVisibility('+ nombre: string')).toEqual({ visibility: '+', text: 'nombre: string' });
    expect(splitVisibility('-saldo: double')).toEqual({ visibility: '-', text: 'saldo: double' });
    expect(splitVisibility('# x')).toEqual({ visibility: '#', text: 'x' });
    expect(splitVisibility('~y')).toEqual({ visibility: '~', text: 'y' });
    expect(splitVisibility('nombre: string')).toEqual({ text: 'nombre: string' });
  });

  it('writes and reads an attribute line with and without visibility', () => {
    expect(attributeToLine({ name: 'nombre', type: 'string' })).toBe('nombre: string');
    expect(attributeToLine({ name: 'saldo', type: 'double', visibility: '-' })).toBe('- saldo: double');
    expect(parseAttributeLine('- saldo: double')).toEqual({ name: 'saldo', type: 'double', visibility: '-' });
    expect(parseAttributeLine('nombre: string')).toEqual({ name: 'nombre', type: 'string' });
  });

  it('keeps a type that has a colon in it', () => {
    expect(parseAttributeLine('+ mapa: Map<String, int>')).toEqual({ name: 'mapa', type: 'Map<String, int>', visibility: '+' });
  });

  it('an enumeration literal has no type', () => {
    expect(attributeToLine({ name: 'ROJO' })).toBe('ROJO');
    expect(parseAttributeLine('ROJO')).toEqual({ name: 'ROJO', type: '' });
  });

  it('writes and reads a method line with and without visibility', () => {
    expect(methodToLine({ name: 'crear' })).toBe('crear();');
    expect(methodToLine({ name: 'pagar', parameters: 'monto: double', returnType: 'bool', visibility: '+' })).toBe('+ pagar(monto: double): bool;');
    expect(parseMethodLine('+ pagar(monto: double): bool;')).toEqual({ name: 'pagar', parameters: 'monto: double', returnType: 'bool', visibility: '+' });
    expect(parseMethodLine('crear();')).toEqual({ name: 'crear', parameters: '', returnType: '' });
    expect(parseMethodLine('# validar')).toEqual({ name: 'validar', visibility: '#' });
  });

  it('builds the text of the compartments from data and leaves text alone', () => {
    expect(attributesToText([{ name: 'id', type: 'int' }, { name: 'x', type: 'int', visibility: '+' }])).toBe('id: int\n+ x: int');
    expect(attributesToText('id: int')).toBe('id: int');
    expect(methodsToText([{ name: 'a' }, { name: 'b', visibility: '-' }])).toBe('a();\n- b();');
    expect(methodsToText(undefined)).toBe('');
  });
});

describe('UML notation: what the AI does not mention is kept', () => {
  it('keeps the visibility a member already had when the AI sends it without one', () => {
    const result = keepVisibility([{ name: 'saldo', type: 'int' }, { name: 'otro', type: 'int' }, { name: 'x', type: 'int', visibility: '#' }], '- saldo: double\n+ x: int', parseAttributeLine);

    expect(result).toEqual([{ name: 'saldo', type: 'int', visibility: '-' }, { name: 'otro', type: 'int' }, { name: 'x', type: 'int', visibility: '#' }]);
  });

  it('works for methods and leaves text alone', () => {
    expect(keepVisibility([{ name: 'pagar' }], '+ pagar(): void;', parseMethodLine)).toEqual([{ name: 'pagar', visibility: '+' }]);
    expect(keepVisibility('texto', '', parseMethodLine)).toBe('texto');
  });
});
