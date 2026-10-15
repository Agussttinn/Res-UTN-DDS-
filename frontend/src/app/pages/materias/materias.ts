import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';

import { FILTROS_ANIO, FiltroAnio, Materia } from '../../models/api.models';
import { ApiService } from '../../services/api.service';
import { mensajeDeError } from '../../utils/errores';

/** Minúsculas y sin acentos: así buscar "algebra" encuentra "Álgebra". */
function normalizar(texto: string): string {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
}

@Component({
  selector: 'app-materias',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './materias.html',
  styleUrls: ['./materias.css']
})
export class MateriasComponent implements OnInit {
  private readonly api = inject(ApiService);
  private pedido?: Subscription;

  readonly filtrosAnio = FILTROS_ANIO;
  /** Las materias se piden por año al backend, que las filtra en la base local. */
  readonly anio = signal<FiltroAnio>(1);
  readonly busqueda = signal('');

  readonly materias = signal<Materia[]>([]);
  readonly cargando = signal(true);
  readonly error = signal('');

  readonly materiasVisibles = computed(() => {
    const buscado = normalizar(this.busqueda());
    return buscado ? this.materias().filter((m) => normalizar(m.nombre).includes(buscado)) : this.materias();
  });

  ngOnInit(): void {
    this.cargarMaterias();
  }

  elegirAnio(anio: FiltroAnio): void {
    if (anio !== this.anio()) {
      this.anio.set(anio);
      this.cargarMaterias();
    }
  }

  cargarMaterias(): void {
    this.cargando.set(true);
    this.error.set('');

    // Si se cambia de año rápido, la respuesta del año anterior ya no sirve.
    this.pedido?.unsubscribe();
    this.pedido = this.api.getMaterias(this.anio()).subscribe({
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
