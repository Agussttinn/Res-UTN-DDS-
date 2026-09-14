import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-materias',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './materias.html',
  styleUrls: ['./materias.css']
})
export class MateriasComponent implements OnInit {
  private readonly api = inject(ApiService);

  materias: any[] = [];
  cargando = true;
  error = false;

  ngOnInit(): void {
    this.cargarMaterias();
  }

  cargarMaterias(): void {
    this.cargando = true;
    this.error = false;

    this.api.getMaterias().subscribe({
      next: (data: any[]) => {
        this.materias = data;
        this.cargando = false;
      },
      error: (err) => {
        console.error('Error cargando materias:', err);
        this.error = true;
        this.cargando = false;
      }
    });
  }
}