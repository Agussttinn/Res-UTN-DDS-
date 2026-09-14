import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-admin-panel',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './admin-panel.html', // o ./admin-panel.component.html
  styleUrl: './admin-panel.css'       // o ./admin-panel.component.css
})
export class AdminPanelComponent implements OnInit {
  private api = inject(ApiService);

  pendientes: any[] = [];
  cargando = true;

  ngOnInit(): void {
    this.cargarPendientes();
  }

  cargarPendientes(): void {
    this.cargando = true;
    this.api.getMaterialesPendientes().subscribe({
      next: (data) => {
        this.pendientes = data;
        this.cargando = false;
      },
      error: () => {
        this.cargando = false;
      }
    });
  }

  moderar(id: number, accion: 'aprobar' | 'rechazar'): void {
    this.api.moderarMaterial(id, accion).subscribe({
      next: () => {
        this.pendientes = this.pendientes.filter(item => item.id !== id);
      },
      error: (err) => console.error('Error al moderar:', err)
    });
  }
}