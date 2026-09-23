import { Component, input } from '@angular/core';

/**
 * Insignia cuadrada con la marca de la UTN (fondo blanco redondeado + el logo). Se usa en la navbar y
 * en el panel del login/registro. El archivo (public/utn-logo.png, la "flor" institucional sin el texto
 * "UTN" — a este tamaño no se leería) es el único lugar a tocar si algún día cambia el logo.
 */
@Component({
  selector: 'app-logo',
  standalone: true,
  template: `
    <div
      [style.width.px]="tamano()"
      [style.height.px]="tamano()"
      class="shrink-0 rounded-xl bg-white flex items-center justify-center shadow-sm p-1.5 overflow-hidden"
    >
      <img src="/utn-logo.png" alt="UTN" class="w-full h-full object-contain" />
    </div>
  `
})
export class LogoComponent {
  /** Tamaño del cuadrado, en píxeles. */
  readonly tamano = input(40);
}
