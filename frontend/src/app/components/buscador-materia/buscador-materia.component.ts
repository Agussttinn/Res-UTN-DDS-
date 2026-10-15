import { Component, Injector, afterNextRender, computed, effect, inject, input, model, signal, untracked } from '@angular/core';

import { Materia, etiquetaAnio } from '../../models/api.models';

/** Minúsculas y sin acentos: así buscar "algebra" encuentra "Álgebra". */
function normalizar(texto: string): string {
  return texto.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
}

function ordenar(materias: Materia[]): Materia[] {
  return [...materias].sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
}

/**
 * Campo para elegir una materia: se puede escribir para filtrar, o hacer click (o flecha abajo) para ver
 * todas las opciones. Sigue el patrón "combobox" de accesibilidad (se maneja entero con el teclado).
 *
 * `materias` son las que se ofrecen al abrir la lista. Si además se pasa `todas`, lo que se escribe se
 * busca en todas ellas (por ejemplo, en cualquier año aunque la lista muestre solo uno).
 *
 * `valor` es el id de la materia elegida, o null si no hay ninguna (texto a medio escribir que no
 * coincide con una materia también es null). Si la materia elegida deja de estar entre las opciones,
 * se borra sola.
 */
@Component({
  selector: 'app-buscador-materia',
  standalone: true,
  host: { class: 'block relative' },
  template: `
    <div class="relative">
      <input [id]="idCampo()" type="text" role="combobox" autocomplete="off" aria-autocomplete="list"
             [attr.aria-expanded]="abierto()"
             [attr.aria-controls]="idLista()"
             [attr.aria-activedescendant]="idActivo()"
             [attr.aria-invalid]="invalido() || null"
             [attr.aria-describedby]="descripcionId()"
             [attr.aria-required]="true"
             [disabled]="deshabilitado()"
             [placeholder]="deshabilitado() ? 'No hay materias para elegir' : 'Escribí o elegí una materia'"
             [value]="texto()"
             (input)="escribir($any($event.target).value)"
             (click)="abrir()"
             (keydown)="tecla($event)"
             (blur)="alSalir()"
             [class]="invalido()
               ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20'
               : 'border-slate-300 focus:border-brand-500 focus:ring-brand-500/20'"
             class="w-full rounded-lg border bg-white py-2 pl-3 pr-9 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:bg-slate-50" />
      <button type="button" tabindex="-1" aria-label="Mostrar materias"
              [disabled]="deshabilitado()"
              (mousedown)="$event.preventDefault()"
              (click)="alternar()"
              class="absolute inset-y-0 right-0 flex items-center px-2.5 text-slate-400 hover:text-slate-600 disabled:cursor-not-allowed disabled:opacity-50">
        <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true" class="h-4 w-4 transition-transform" [class.rotate-180]="abierto()">
          <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.06l3.71-3.83a.75.75 0 1 1 1.08 1.04l-4.25 4.39a.75.75 0 0 1-1.08 0L5.21 8.27a.75.75 0 0 1 .02-1.06Z" clip-rule="evenodd" />
        </svg>
      </button>
    </div>

    @if (abierto()) {
      <ul [id]="idLista()" role="listbox" aria-label="Materias"
          class="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
        @for (m of opciones(); track m.id; let i = $index) {
          <li [id]="idOpcion(m)" role="option" [attr.aria-selected]="m.id === valor()"
              (mousedown)="$event.preventDefault()"
              (click)="elegir(m)"
              (mouseenter)="activo.set(i)"
              [class]="i === activo() ? 'bg-brand-50 text-brand-900' : 'text-slate-700'"
              class="flex cursor-pointer items-center justify-between gap-3 px-3 py-2 text-sm">
            <span [class.font-semibold]="m.id === valor()">{{ m.nombre }}</span>
            <span class="flex shrink-0 items-center gap-2 text-xs text-slate-400">
              @if (buscando()) {
                {{ etiquetaAnio(m) }}
              }
              @if (m.id === valor()) {
                <span class="text-brand-600" aria-hidden="true">✓</span>
              }
            </span>
          </li>
        } @empty {
          <li class="px-3 py-2 text-sm text-slate-500">No hay materias que coincidan con "{{ texto() }}".</li>
        }
      </ul>
    }
  `
})
export class BuscadorMateriaComponent {
  private readonly injector = inject(Injector);

  readonly materias = input<Materia[]>([]);
  /** Dónde se busca lo que se escribe. Si no se pasa, en `materias`. */
  readonly todas = input<Materia[] | null>(null);
  readonly valor = model<number | null>(null);
  /** id del input, para asociarle su <label for="...">. */
  readonly idCampo = input.required<string>();
  readonly invalido = input(false);
  /** id del texto de ayuda o de error que describe al campo. */
  readonly descripcionId = input<string | null>(null);
  readonly deshabilitado = input(false);

  protected readonly texto = signal('');
  protected readonly abierto = signal(false);
  /** Posición de la opción resaltada (con el teclado o el mouse), o -1. */
  protected readonly activo = signal(-1);
  /** Nombre de la materia elegida, tal como se muestra en el campo. */
  private readonly textoElegido = signal('');

  protected readonly idLista = computed(() => `${this.idCampo()}-opciones`);

  protected readonly etiquetaAnio = etiquetaAnio;

  private readonly universo = computed(() => this.todas() ?? this.materias());

  /** Hay texto escrito que no es la materia ya elegida (con una elegida, abrir la lista muestra todas, para cambiarla). */
  protected readonly buscando = computed(() => !!normalizar(this.texto()) && this.texto() !== this.textoElegido());

  protected readonly opciones = computed(() => {
    if (!this.buscando()) {
      return ordenar(this.materias());
    }
    const buscado = normalizar(this.texto());
    return ordenar(this.universo().filter((m) => normalizar(m.nombre).includes(buscado)));
  });

  protected readonly idActivo = computed(() => {
    const opcion = this.abierto() ? this.opciones()[this.activo()] : undefined;
    return opcion ? this.idOpcion(opcion) : null;
  });

  constructor() {
    // Mantiene el texto del campo al día cuando el valor cambia desde afuera (materia preseleccionada,
    // formulario que se reinicia, filtro que cambia).
    effect(() => {
      const id = this.valor();
      const materia = this.universo().find((m) => m.id === id);
      untracked(() => {
        if (materia) {
          this.mostrar(materia.nombre);
          return;
        }
        if (id !== null) {
          this.valor.set(null); // ya no está entre las opciones
        }
        if (this.texto() === this.textoElegido()) {
          this.mostrar(''); // se borró la elección; lo que la persona esté escribiendo se respeta
        }
      });
    });
  }

  protected idOpcion(materia: Materia): string {
    return `${this.idCampo()}-opcion-${materia.id}`;
  }

  protected escribir(texto: string): void {
    this.texto.set(texto);
    this.textoElegido.set('');
    this.abierto.set(true);
    this.activo.set(texto.trim() ? 0 : -1);
    if (this.valor() !== null) {
      this.valor.set(null);
    }
  }

  protected elegir(materia: Materia): void {
    this.mostrar(materia.nombre);
    this.valor.set(materia.id);
    this.cerrar();
  }

  protected abrir(): void {
    if (this.abierto() || this.deshabilitado()) {
      return;
    }
    this.abierto.set(true);
    this.resaltar(this.opciones().findIndex((m) => m.id === this.valor()));
  }

  protected alternar(): void {
    if (this.abierto()) {
      this.cerrar();
      return;
    }
    document.getElementById(this.idCampo())?.focus();
    this.abrir();
  }

  protected tecla(evento: KeyboardEvent): void {
    const cantidad = this.opciones().length;
    switch (evento.key) {
      case 'ArrowDown':
        evento.preventDefault();
        if (!this.abierto()) {
          this.abrir();
          if (this.activo() < 0) {
            this.resaltar(0);
          }
        } else {
          this.resaltar(Math.min(this.activo() + 1, cantidad - 1));
        }
        break;
      case 'ArrowUp':
        evento.preventDefault();
        if (this.abierto()) {
          this.resaltar(Math.max(this.activo() - 1, 0));
        }
        break;
      case 'Enter': {
        const opcion = this.abierto() ? this.opciones()[this.activo()] : undefined;
        if (opcion) {
          evento.preventDefault(); // elige la opción en vez de enviar el formulario
          this.elegir(opcion);
        }
        break;
      }
      case 'Escape':
        if (this.abierto()) {
          evento.stopPropagation(); // cierra solo el menú, no el modal que contiene al campo
          this.cerrar();
        }
        break;
    }
  }

  /** Al salir del campo: si lo escrito es exactamente el nombre de una materia, queda elegida. */
  protected alSalir(): void {
    this.cerrar();
    if (this.valor() === null && this.texto().trim()) {
      const buscado = normalizar(this.texto());
      const exacta = this.universo().find((m) => normalizar(m.nombre) === buscado);
      if (exacta) {
        this.elegir(exacta);
      }
    }
  }

  private cerrar(): void {
    this.abierto.set(false);
    this.activo.set(-1);
  }

  private mostrar(nombre: string): void {
    this.texto.set(nombre);
    this.textoElegido.set(nombre);
  }

  private resaltar(indice: number): void {
    this.activo.set(indice);
    const opcion = this.opciones()[indice];
    if (opcion) {
      afterNextRender(
        () => document.getElementById(this.idOpcion(opcion))?.scrollIntoView?.({ block: 'nearest' }),
        { injector: this.injector }
      );
    }
  }
}
