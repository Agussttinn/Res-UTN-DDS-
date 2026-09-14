import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.html', 
  styleUrl: './login.css'       
})
export class LoginComponent {
  private api = inject(ApiService);
  private router = inject(Router);

  credenciales = {
    username: '',
    password: ''
  };

  cargando = false;
  errorMensaje = '';

  onSubmit(): void {
    if (!this.credenciales.username || !this.credenciales.password) {
      this.errorMensaje = 'Por favor ingresá tu legajo/usuario y contraseña.';
      return;
    }

    this.cargando = true;
    this.errorMensaje = '';

    this.api.login(this.credenciales).subscribe({
      next: (res) => {
        const token = res.access || res.token;
        if (token) {
          this.api.setToken(token);
          this.router.navigate(['/materias']);
        }
        this.cargando = false;
      },
      error: (err) => {
        console.error(err);
        this.errorMensaje = 'Credenciales inválidas o servidor no disponible.';
        this.cargando = false;
      }
    });
  }
}