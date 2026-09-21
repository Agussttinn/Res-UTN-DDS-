import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Materia } from '../../models/api.models';
import { ApiService } from '../../services/api.service';
import { mensajeDeError } from '../../utils/errores';

@Component({
  selector: 'app-materias',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './materias.html',
  styleUrls: ['./materias.css']
})
export class MateriasComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly materias = signal<Materia[]>([]);
  readonly cargando = signal(true);
  readonly error = signal('');

  ngOnInit(): void {
    this.cargarMaterias();
  }

  cargarMaterias(): void {
    this.cargando.set(true);
    this.error.set('');

    this.api.getMaterias().subscribe({
      next: (data) => {
        this.materias.set(data);
        this.cargando.set(false);
      },
      error: (err: unknown) => {
        this.error.set(mensajeDeError(err, 'No se pudieron cargar las materias.'));
        this.cargando.set(false);
      }
    });
  }
}
