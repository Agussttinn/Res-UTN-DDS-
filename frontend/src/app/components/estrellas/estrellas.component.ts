import { Component, computed, input, output, signal } from '@angular/core';

/**
 * Puntuación de un apunte con estrellas (1 a 5).
 * - Si el usuario puede votar: las estrellas muestran SU voto (y se iluminan al pasar el mouse).
 * - Si no puede (es su propio apunte, o todavía está pendiente): muestra el promedio de la comunidad.
 * El promedio y la cantidad de votos se muestran siempre al lado.
 */
@Component({
  selector: 'app-estrellas',
  standalone: true,
  template: `
    <div class="flex items-center gap-2">
      <div class="flex" role="group" aria-label="Puntuación con estrellas">
        @for (n of estrellas; track n) {
          <button type="button"
                  class="text-lg leading-none px-0.5 transition-colors disabled:cursor-default"
                  [class]="n <= llenas() ? 'text-amber-400' : 'text-slate-300'"
                  [disabled]="!puedeVotar() || enviando()"
                  [attr.aria-label]="n === 1 ? 'Puntuar con 1 estrella' : 'Puntuar con ' + n + ' estrellas'"
                  [title]="puedeVotar() ? n + (n === 1 ? ' estrella' : ' estrellas') : motivo()"
                  (mouseenter)="hover.set(n)"
                  (mouseleave)="hover.set(0)"
                  (click)="votar.emit(n)">★</button>
        }
      </div>
      <span class="text-xs text-slate-500">
        @if (cantidad() > 0) {
          <strong class="text-slate-700">{{ promedio() }}</strong>
          ({{ cantidad() }} {{ cantidad() === 1 ? 'voto' : 'votos' }})
        } @else {
          Sin votos
        }
      </span>
    </div>
    @if (puedeVotar() && miVoto()) {
      <p class="text-[10px] text-slate-400 mt-0.5">Tu voto: {{ miVoto() }} ★ · tocá otra estrella para cambiarlo</p>
    } @else if (!puedeVotar() && motivo()) {
      <p class="text-[10px] text-slate-400 mt-0.5">{{ motivo() }}</p>
    }
  `
})
export class EstrellasComponent {
  readonly promedio = input<number | null>(null);
  readonly cantidad = input(0);
  readonly miVoto = input<number | null>(null);
  readonly puedeVotar = input(false);
  /** Por qué no se puede votar (se muestra como ayuda). */
  readonly motivo = input('');
  readonly enviando = input(false);

  /** Emite las estrellas elegidas (1 a 5). */
  readonly votar = output<number>();

  protected readonly estrellas = [1, 2, 3, 4, 5];
  protected readonly hover = signal(0);

  protected readonly llenas = computed(() => {
    if (this.puedeVotar()) {
      return this.hover() || this.miVoto() || 0;
    }
    return Math.round(this.promedio() ?? 0);
  });
}
