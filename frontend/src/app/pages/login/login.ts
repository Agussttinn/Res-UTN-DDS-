import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { LogoComponent } from '../../components/logo/logo.component';
import { AuthService } from '../../services/auth.service';
import { mensajeDeError } from '../../utils/errores';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, RouterLink, LogoComponent],
  templateUrl: './login.html',
  styleUrl: './login.css'
})
export class LoginComponent implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  legajo = '';
  contrasena = '';

  readonly cargando = signal(false);
  readonly error = signal('');
  /** El backend respondió 401 a una página que ya estaba abierta: el token dura 8 horas. */
  readonly sesionVencida = this.route.snapshot.queryParamMap.has('vencida');

  ngOnInit(): void {
    if (this.auth.estaLogueado()) {
      void this.router.navigateByUrl(this.destino());
    }
  }

  onSubmit(): void {
    const legajo = this.legajo.trim();
    if (!legajo || !this.contrasena) {
      this.error.set('Ingresá tu legajo y tu contraseña.');
      return;
    }

    this.cargando.set(true);
    this.error.set('');

    this.auth.login(legajo, this.contrasena).subscribe({
      next: () => void this.router.navigateByUrl(this.destino()),
      error: (err: unknown) => {
        this.error.set(mensajeDeError(err, 'No se pudo iniciar sesión. Intentá de nuevo.'));
        this.cargando.set(false);
      }
    });
  }

  /** Página a la que quería entrar antes de que lo mandaran al login (solo rutas internas). */
  private destino(): string {
    const returnUrl = this.route.snapshot.queryParamMap.get('returnUrl');
    return returnUrl && returnUrl.startsWith('/') && !returnUrl.startsWith('//') ? returnUrl : '/materias';
  }
}
