import { AfterViewInit, Component, ElementRef, input, output, viewChild } from '@angular/core';

/**
 * Ventana de confirmación dentro de la app (reemplaza al `confirm()` del navegador, que se ve distinto en
 * cada navegador y puede estar bloqueado). Se muestra con `@if` desde la página que la usa:
 *
 *   @if (pendiente(); as p) {
 *     <app-dialogo-confirmacion [titulo]="p.titulo" [mensaje]="p.mensaje" textoConfirmar="Archivar"
 *                               (confirmado)="..." (cancelado)="pendiente.set(null)" />
 *   }
 *
 * Se cierra con el botón "Volver", con Escape o haciendo clic fuera de la ventana.
 */
@Component({
  selector: 'app-dialogo-confirmacion',
  standalone: true,
  template: `
    <div class="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center sm:p-4"
         (click)="cancelado.emit()">
      <div role="alertdialog" aria-modal="true" aria-labelledby="titulo-confirmacion" aria-describedby="mensaje-confirmacion"
           (click)="$event.stopPropagation()" (keydown.escape)="cancelado.emit()"
           class="bg-white w-full sm:max-w-md rounded-t-2xl sm:rounded-2xl shadow-xl">
        <div class="px-5 sm:px-6 pt-5 pb-4 space-y-2">
          <h2 id="titulo-confirmacion" class="text-lg font-bold text-slate-800">{{ titulo() }}</h2>
          <p id="mensaje-confirmacion" class="text-sm text-slate-600">{{ mensaje() }}</p>
        </div>
        <footer class="flex justify-end gap-2 px-5 sm:px-6 pb-5">
          <button #volver type="button" (click)="cancelado.emit()"
                  class="px-3 py-1.5 text-sm font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700">
            Volver
          </button>
          <button type="button" (click)="confirmado.emit()"
                  [class]="peligro() ? 'bg-rose-600 hover:bg-rose-700' : 'bg-brand-600 hover:bg-brand-700'"
                  class="px-3 py-1.5 text-sm font-semibold rounded-lg text-white">
            {{ textoConfirmar() }}
          </button>
        </footer>
      </div>
    </div>
  `
})
export class DialogoConfirmacionComponent implements AfterViewInit {
  readonly titulo = input.required<string>();
  readonly mensaje = input.required<string>();
  readonly textoConfirmar = input('Confirmar');
  /** Acción destructiva: el botón de confirmar se pinta en rojo. */
  readonly peligro = input(false);

  readonly confirmado = output<void>();
  readonly cancelado = output<void>();

  private readonly volver = viewChild.required<ElementRef<HTMLButtonElement>>('volver');

  /** El foco arranca en "Volver": un Enter apurado no confirma una acción destructiva. */
  ngAfterViewInit(): void {
    this.volver().nativeElement.focus();
  }
}
