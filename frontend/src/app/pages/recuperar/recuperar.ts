import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { LogoComponent } from '../../components/logo/logo.component';
import { AuthService } from '../../services/auth.service';
import { mensajeDeError } from '../../utils/errores';

/** Pide el legajo y la API manda un mail con el link para elegir una contraseña nueva. */
@Component({
  selector: 'app-recuperar',
  standalone: true,
  imports: [FormsModule, RouterLink, LogoComponent],
  templateUrl: './recuperar.html'
})
export class RecuperarComponent {
  private readonly auth = inject(AuthService);

  legajo = '';

  readonly cargando = signal(false);
  readonly error = signal('');
  readonly enviado = signal(false);

  onSubmit(): void {
    const legajo = this.legajo.trim();
    if (!legajo) {
      this.error.set('Ingresá tu legajo.');
      return;
    }

    this.cargando.set(true);
    this.error.set('');

    this.auth.pedirRecuperacion(legajo).subscribe({
      next: () => {
        this.enviado.set(true);
        this.cargando.set(false);
      },
      error: (err: unknown) => {
        this.error.set(mensajeDeError(err, 'No se pudo enviar el mail. Intentá de nuevo.'));
        this.cargando.set(false);
      }
    });
  }
}
