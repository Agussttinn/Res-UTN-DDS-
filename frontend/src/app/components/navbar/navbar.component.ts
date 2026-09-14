import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  templateUrl: './navbar.component.html', 
  styleUrl: './navbar.css'      
})
export class NavbarComponent {
  api = inject(ApiService);
  private router = inject(Router);

  cerrarSesion(): void {
    this.api.logout();
    this.router.navigate(['/login']);
  }
}