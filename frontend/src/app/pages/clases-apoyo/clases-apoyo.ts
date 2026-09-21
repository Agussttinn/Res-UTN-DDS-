import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ClaseApoyo, Materia } from '../../models/api.models';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { mensajeDeError } from '../../utils/errores';

@Component({
  selector: 'app-clases-apoyo',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './clases-apoyo.html',
  styleUrl: './clases-apoyo.css'
})
export class ClasesApoyoComponent implements OnInit {
  private readonly api = inject(ApiService);
  readonly auth = inject(AuthService);

  readonly clases = signal<ClaseApoyo[]>([]);
  readonly materias = signal<Materia[]>([]);
  readonly cargando = signal(true);
  readonly error = signal('');
  readonly aviso = signal('');
  readonly errorAccion = signal('');
  readonly filtroMateria = signal<number | null>(null);

  // Formulario para publicar / modificar una clase (solo tutores)
  readonly mostrarModal = signal(false);
  readonly guardando = signal(false);
  readonly errorModal = signal('');
  /** Id de la clase que se está modificando, o null si se está publicando una nueva. */
  editandoId: number | null = null;
  form = this.formVacio();

  ngOnInit(): void {
    this.cargarClases();
    this.api.getMaterias().subscribe({
      next: (data) => this.materias.set(data),
      error: () => this.materias.set([]) // sin materias no se puede publicar, pero la lista sigue funcionando
    });
  }

  /** `mostrarSpinner = false` recarga sin tapar la lista con "Buscando..." (por ejemplo, después de guardar). */
  cargarClases(mostrarSpinner = true): void {
    if (mostrarSpinner) {
      this.cargando.set(true);
    }
    this.error.set('');
    this.api.getClasesApoyo(this.filtroMateria() ?? undefined).subscribe({
      next: (data) => {
        this.clases.set(data);
        this.cargando.set(false);
      },
      error: (err: unknown) => {
        this.error.set(mensajeDeError(err, 'No se pudo obtener el cronograma.'));
        this.cargando.set(false);
      }
    });
  }

  filtrarPorMateria(materiaId: number | null): void {
    this.filtroMateria.set(materiaId);
    this.cargarClases();
  }

  /** El tutor a cargo de la clase, o un administrador (la API lo vuelve a verificar). */
  puedeGestionar(clase: ClaseApoyo): boolean {
    return this.auth.esAdministrador() || (this.auth.esTutor() && clase.tutor.legajo === this.auth.usuario()?.legajo);
  }

  abrirModal(clase?: ClaseApoyo): void {
    this.editandoId = clase?.id ?? null;
    this.form = clase
      ? { materia: clase.materia.id, horario: clase.horario, aula: clase.aula }
      : { ...this.formVacio(), materia: this.filtroMateria() };
    this.errorModal.set('');
    this.mostrarModal.set(true);
  }

  cerrarModal(): void {
    this.mostrarModal.set(false);
  }

  guardar(): void {
    const { materia, horario, aula } = this.form;
    if (materia === null || !horario.trim() || !aula.trim()) {
      this.errorModal.set('Completá la materia, el horario y el aula.');
      return;
    }

    this.guardando.set(true);
    this.errorModal.set('');

    // El tutor no se manda: la clase queda a nombre de quien está logueado.
    const datos = { materia_id: materia, horario: horario.trim(), aula: aula.trim() };
    const peticion = this.editandoId === null
      ? this.api.crearClaseApoyo(datos)
      : this.api.actualizarClaseApoyo(this.editandoId, datos);

    peticion.subscribe({
      next: () => {
        this.guardando.set(false);
        this.mostrarModal.set(false);
        this.aviso.set(this.editandoId === null ? 'Clase publicada.' : 'Clase actualizada.');
        this.cargarClases(false);
      },
      error: (err: unknown) => {
        this.guardando.set(false);
        this.errorModal.set(mensajeDeError(err, 'No se pudo guardar la clase.'));
      }
    });
  }

  cancelarClase(clase: ClaseApoyo): void {
    if (!confirm(`¿Cancelar la clase de ${clase.materia.nombre} (${clase.horario})? Esta acción no se puede deshacer.`)) {
      return;
    }
    this.errorAccion.set('');
    this.api.eliminarClaseApoyo(clase.id).subscribe({
      next: () => {
        this.clases.update((lista) => lista.filter((c) => c.id !== clase.id));
        this.aviso.set('Clase cancelada.');
      },
      error: (err: unknown) => this.errorAccion.set(mensajeDeError(err, 'No se pudo cancelar la clase.'))
    });
  }

  private formVacio() {
    return { materia: null as number | null, horario: '', aula: '' };
  }
}
