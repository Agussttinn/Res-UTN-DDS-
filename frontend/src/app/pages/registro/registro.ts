import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { LogoComponent } from '../../components/logo/logo.component';
import { AuthService } from '../../services/auth.service';
import { mensajeDeError } from '../../utils/errores';

const LARGO_MINIMO_CONTRASENA = 8;

@Component({
  selector: 'app-registro',
  standalone: true,
  imports: [FormsModule, RouterLink, LogoComponent],
  templateUrl: './registro.html'
})
export class RegistroComponent implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly largoMinimo = LARGO_MINIMO_CONTRASENA;

  legajo = '';
  contrasena = '';
  repetir = '';

  readonly cargando = signal(false);
  readonly error = signal('');

  ngOnInit(): void {
    if (this.auth.estaLogueado()) {
      void this.router.navigateByUrl('/materias');
    }
  }

  onSubmit(): void {
    const legajo = this.legajo.trim();
    if (!legajo || !this.contrasena) {
      this.error.set('Completá tu legajo y elegí una contraseña.');
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

    // La API valida el legajo contra SySACAD y toma de ahí tu nombre y correo.
    this.auth.registrar(legajo, this.contrasena).subscribe({
      next: () => this.iniciarSesion(legajo),
      error: (err: unknown) => {
        this.error.set(mensajeDeError(err, 'No se pudo crear la cuenta. Intentá de nuevo.'));
        this.cargando.set(false);
      }
    });
  }

  /** Con la cuenta recién creada, entra directo sin pedir que vuelva a escribir los datos. */
  private iniciarSesion(legajo: string): void {
    this.auth.login(legajo, this.contrasena).subscribe({
      next: () => void this.router.navigateByUrl('/materias'),
      error: () => {
        this.error.set('Tu cuenta se creó, pero no pudimos iniciar sesión automáticamente. Ingresá desde la pantalla de login.');
        this.cargando.set(false);
      }
    });
  }
}
