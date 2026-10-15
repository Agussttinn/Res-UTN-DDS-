import { Component, DestroyRef, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';

import { FILTROS_ANIO, FiltroAnio, Materia, etiquetaAnio } from '../../models/api.models';
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
  private pedido?: Subscription;
  private esperaBusqueda?: ReturnType<typeof setTimeout>;

  readonly filtrosAnio = FILTROS_ANIO;
  readonly etiquetaAnio = etiquetaAnio;
  /** Cuánto se espera a que se deje de escribir antes de buscar (para no consultar con cada tecla). */
  demoraBusquedaMs = 300;

  /** Las materias se piden por año al backend, que las filtra en la base local. */
  readonly anio = signal<FiltroAnio>(1);
  /** Con texto, se busca por nombre en todos los años y el año elegido no se aplica. */
  readonly busqueda = signal('');
  readonly buscando = computed(() => this.busqueda().trim() !== '');

  readonly materias = signal<Materia[]>([]);
  readonly cargando = signal(true);
  readonly error = signal('');

  constructor() {
    inject(DestroyRef).onDestroy(() => clearTimeout(this.esperaBusqueda));
  }

  ngOnInit(): void {
    this.cargarMaterias();
  }

  elegirAnio(anio: FiltroAnio): void {
    if (anio === this.anio() && !this.buscando()) {
      return;
    }
    this.anio.set(anio);
    this.busqueda.set(''); // elegir un año sale de la búsqueda
    this.cargarMaterias();
  }

  buscar(texto: string): void {
    this.busqueda.set(texto);
    clearTimeout(this.esperaBusqueda);
    this.esperaBusqueda = setTimeout(() => this.cargarMaterias(), this.demoraBusquedaMs);
  }

  limpiarBusqueda(): void {
    this.buscar('');
  }

  cargarMaterias(): void {
    this.cargando.set(true);
    this.error.set('');

    // Si se cambia de año o se sigue escribiendo, la respuesta anterior ya no sirve.
    this.pedido?.unsubscribe();
    const filtros = this.buscando() ? { buscar: this.busqueda() } : { anio: this.anio() };
    this.pedido = this.api.getMaterias(filtros).subscribe({
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
