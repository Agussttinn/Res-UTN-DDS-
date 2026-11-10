import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { LogoComponent } from '../../components/logo/logo.component';
import { AuthService } from '../../services/auth.service';
import { mensajeDeError } from '../../utils/errores';

const LARGO_MINIMO_CONTRASENA = 8;

/** Destino del link del mail (/restablecer?token=...): elige la contraseña nueva. */
@Component({
  selector: 'app-restablecer',
  standalone: true,
  imports: [FormsModule, RouterLink, LogoComponent],
  templateUrl: './restablecer.html'
})
export class RestablecerComponent {
  private readonly auth = inject(AuthService);
  private readonly token = inject(ActivatedRoute).snapshot.queryParamMap.get('token') ?? '';

  readonly largoMinimo = LARGO_MINIMO_CONTRASENA;
  readonly sinToken = this.token === '';

  contrasena = '';
  repetir = '';

  readonly cargando = signal(false);
  readonly error = signal('');
  readonly listo = signal(false);

  onSubmit(): void {
    if (!this.contrasena) {
      this.error.set('Elegí una contraseña nueva.');
      return;
    }
    if (this.contrasena.length < LARGO_MINIMO_CONTRASENA) {
      this.error.set(`La contraseña tiene que tener al menos ${LARGO_MINIMO_CONTRASENA} caracteres.`);
      return;
    }
    if (this.contrasena !== this.repetir) {
      this.error.set('Las contraseñas no coinciden.');
      return;
    }

    this.cargando.set(true);
    this.error.set('');

    this.auth.restablecerContrasena(this.token, this.contrasena).subscribe({
      next: () => {
        this.listo.set(true);
        this.cargando.set(false);
      },
      error: (err: unknown) => {
        this.error.set(mensajeDeError(err, 'No se pudo cambiar la contraseña. Intentá de nuevo.'));
        this.cargando.set(false);
      }
    });
  }
}
