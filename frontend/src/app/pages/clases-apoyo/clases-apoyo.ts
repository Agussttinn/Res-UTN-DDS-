import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-clases-apoyo',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './clases-apoyo.html',
  styleUrl: './clases-apoyo.css'       
})
export class ClasesApoyoComponent implements OnInit {
  private api = inject(ApiService);

  clases: any[] = [];
  cargando = true;
  error = false;

  ngOnInit(): void {
    this.cargarClases();
  }

  cargarClases(): void {
    this.cargando = true;
    this.api.getClasesApoyo().subscribe({
      next: (data) => {
        this.clases = data;
        this.cargando = false;
      },
      error: (err) => {
        console.error('Error cargando clases:', err);
        this.error = true;
        this.cargando = false;
      }
    });
  }

  getEstadoBadge(estado: string): string {
    switch (estado?.toUpperCase()) {
      case 'CONFIRMADA':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'CANCELADA':
        return 'bg-rose-100 text-rose-800 border-rose-200';
      default:
        return 'bg-amber-100 text-amber-800 border-amber-200';
    }
  }
}