import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

import { LogoComponent } from '../logo/logo.component';
import { ETIQUETA_ROL } from '../../models/api.models';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, LogoComponent],
  templateUrl: './navbar.component.html',
  styleUrl: './navbar.css'
})
export class NavbarComponent {
  readonly auth = inject(AuthService);
  readonly etiquetaRol = ETIQUETA_ROL;

  cerrarSesion(): void {
    this.auth.cerrarSesion();
  }
}
