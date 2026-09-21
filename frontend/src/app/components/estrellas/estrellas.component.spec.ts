import { ComponentFixture, TestBed } from '@angular/core/testing';

import { proveedoresDePrueba, textoDe } from '../../testing/pruebas';
import { EstrellasComponent } from './estrellas.component';

describe('EstrellasComponent', () => {
  beforeEach(() => TestBed.configureTestingModule({ imports: [EstrellasComponent], providers: proveedoresDePrueba() }));

  async function montar(entradas: Record<string, unknown> = {}): Promise<ComponentFixture<EstrellasComponent>> {
    const fixture = TestBed.createComponent(EstrellasComponent);
    for (const [nombre, valor] of Object.entries(entradas)) {
      fixture.componentRef.setInput(nombre, valor);
    }
    await fixture.whenStable();
    return fixture;
  }

  const botones = (f: ComponentFixture<unknown>) => Array.from((f.nativeElement as HTMLElement).querySelectorAll('button'));
  const llenas = (f: ComponentFixture<unknown>) => botones(f).filter((b) => b.className.includes('text-amber-400')).length;

  it('muestra 5 estrellas y "Sin votos" si nadie puntuó', async () => {
    const fixture = await montar();

    expect(botones(fixture)).toHaveLength(5);
    expect(textoDe(fixture)).toContain('Sin votos');
    expect(llenas(fixture)).toBe(0);
  });

  it('muestra el promedio y la cantidad de votos (con singular y plural)', async () => {
    const fixture = await montar({ promedio: 3.5, cantidad: 2 });
    expect(textoDe(fixture)).toContain('3.5 (2 votos)');

    fixture.componentRef.setInput('cantidad', 1);
    await fixture.whenStable();
    expect(textoDe(fixture)).toContain('(1 voto)');
  });

  describe('si el usuario puede votar', () => {
    it('las estrellas están habilitadas y al tocar una se emiten sus estrellas', async () => {
      const fixture = await montar({ puedeVotar: true });
      const emitidos: number[] = [];
      fixture.componentInstance.votar.subscribe((valor) => emitidos.push(valor));

      expect(botones(fixture).every((b) => !b.disabled)).toBe(true);
      botones(fixture)[3].click();

      expect(emitidos).toEqual([4]);
    });

    it('resalta SU voto y lo aclara', async () => {
      const fixture = await montar({ puedeVotar: true, miVoto: 3, promedio: 5, cantidad: 10 });

      expect(llenas(fixture)).toBe(3); // su voto, no el promedio
      expect(textoDe(fixture)).toContain('Tu voto: 3');
    });

    it('al pasar el mouse muestra cuántas estrellas daría, y al salir vuelve a su voto', async () => {
      const fixture = await montar({ puedeVotar: true, miVoto: 2 });
      const estrellas = botones(fixture);

      estrellas[4].dispatchEvent(new Event('mouseenter'));
      await fixture.whenStable();
      expect(llenas(fixture)).toBe(5);

      estrellas[4].dispatchEvent(new Event('mouseleave'));
      await fixture.whenStable();
      expect(llenas(fixture)).toBe(2);
    });

    it('mientras se envía el voto están deshabilitadas', async () => {
      const fixture = await montar({ puedeVotar: true, enviando: true });

      expect(botones(fixture).every((b) => b.disabled)).toBe(true);
    });
  });

  describe('si el usuario NO puede votar', () => {
    it('están deshabilitadas, muestran el promedio redondeado y explican el motivo', async () => {
      const fixture = await montar({ puedeVotar: false, promedio: 3.6, cantidad: 4, motivo: 'No podés puntuar tu propio apunte.' });

      expect(botones(fixture).every((b) => b.disabled)).toBe(true);
      expect(llenas(fixture)).toBe(4); // 3.6 redondea a 4
      expect(textoDe(fixture)).toContain('No podés puntuar tu propio apunte.');
    });

    it('tocar una estrella no emite nada', async () => {
      const fixture = await montar({ puedeVotar: false });
      const emitidos: number[] = [];
      fixture.componentInstance.votar.subscribe((valor) => emitidos.push(valor));

      botones(fixture)[2].click(); // un botón deshabilitado ignora el clic

      expect(emitidos).toEqual([]);
    });
  });
});
