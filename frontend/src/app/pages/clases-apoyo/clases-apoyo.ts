import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { BuscadorMateriaComponent } from '../../components/buscador-materia/buscador-materia.component';
import { ClaseApoyo, EstadoSuscripcion, Materia, MensajeClase } from '../../models/api.models';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { mensajeDeError } from '../../utils/errores';

const LARGO_MAXIMO_MENSAJE = 1000;

@Component({
  selector: 'app-clases-apoyo',
  standalone: true,
  imports: [DatePipe, FormsModule, BuscadorMateriaComponent],
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

  /** Id de la clase cuya suscripción se está cambiando. */
  readonly suscribiendo = signal<number | null>(null);

  // Mensajes de una clase (los lee el que la sigue; los escribe su tutor)
  readonly largoMaximoMensaje = LARGO_MAXIMO_MENSAJE;
  readonly claseMensajes = signal<ClaseApoyo | null>(null);
  readonly mensajes = signal<MensajeClase[]>([]);
  readonly cargandoMensajes = signal(false);
  readonly errorMensajes = signal('');
  readonly enviandoMensaje = signal(false);
  readonly errorEnvioMensaje = signal('');
  readonly nuevoMensaje = signal('');

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

  /** Los mensajes los ven sus suscritos, su tutor y los administradores. */
  puedeVerMensajes(clase: ClaseApoyo): boolean {
    return clase.suscrito || this.puedeGestionar(clase);
  }

  // ---- suscripción (el alumno pasa a ser observador de la clase) ----

  alternarSuscripcion(clase: ClaseApoyo): void {
    this.suscribiendo.set(clase.id);
    this.errorAccion.set('');
    const peticion = clase.suscrito ? this.api.desuscribirse(clase.id) : this.api.suscribirse(clase.id);
    peticion.subscribe({
      next: (estado) => {
        this.actualizarSuscripcion(clase.id, estado);
        this.aviso.set(
          estado.suscrito
            ? `Te suscribiste a ${clase.materia.nombre}: te vamos a avisar si cambia, se cancela o el tutor manda un mensaje.`
            : `Dejaste de seguir la clase de ${clase.materia.nombre}.`
        );
        this.suscribiendo.set(null);
      },
      error: (err: unknown) => {
        this.errorAccion.set(mensajeDeError(err, 'No se pudo cambiar la suscripción.'));
        this.suscribiendo.set(null);
      }
    });
  }

  private actualizarSuscripcion(claseId: number, estado: EstadoSuscripcion): void {
    this.clases.update((lista) => lista.map((c) => (c.id === claseId ? { ...c, ...estado } : c)));
  }

  // ---- mensajes ----

  abrirMensajes(clase: ClaseApoyo): void {
    this.claseMensajes.set(clase);
    this.mensajes.set([]);
    this.nuevoMensaje.set('');
    this.errorEnvioMensaje.set('');
    this.cargarMensajes();
  }

  cerrarMensajes(): void {
    if (!this.enviandoMensaje()) {
      this.claseMensajes.set(null);
    }
  }

  cargarMensajes(): void {
    const clase = this.claseMensajes();
    if (!clase) {
      return;
    }
    this.cargandoMensajes.set(true);
    this.errorMensajes.set('');
    this.api.getMensajes(clase.id).subscribe({
      next: (lista) => {
        this.mensajes.set(lista);
        this.cargandoMensajes.set(false);
      },
      error: (err: unknown) => {
        this.errorMensajes.set(mensajeDeError(err, 'No se pudieron cargar los mensajes.'));
        this.cargandoMensajes.set(false);
      }
    });
  }

  enviarMensaje(): void {
    const clase = this.claseMensajes();
    const texto = this.nuevoMensaje().trim();
    if (!clase || this.enviandoMensaje()) {
      return;
    }
    if (!texto) {
      this.errorEnvioMensaje.set('Escribí el mensaje.');
      document.getElementById('nuevo-mensaje')?.focus();
      return;
    }

    this.enviandoMensaje.set(true);
    this.errorEnvioMensaje.set('');
    this.api.enviarMensaje(clase.id, texto).subscribe({
      next: (mensaje) => {
        this.mensajes.update((lista) => [mensaje, ...lista]);
        this.nuevoMensaje.set('');
        this.enviandoMensaje.set(false);
        const n = clase.cantidad_suscritos;
        this.aviso.set(n === 1 ? 'Mensaje enviado al alumno suscrito.' : `Mensaje enviado a los ${n} alumnos suscritos.`);
      },
      error: (err: unknown) => {
        this.errorEnvioMensaje.set(mensajeDeError(err, 'No se pudo enviar el mensaje.'));
        this.enviandoMensaje.set(false);
      }
    });
  }

  // ---- publicar / modificar / cancelar ----

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
        this.aviso.set(this.editandoId === null ? 'Clase publicada.' : 'Clase actualizada. Los alumnos suscritos reciben un aviso con los cambios.');
        this.cargarClases(false);
      },
      error: (err: unknown) => {
        this.guardando.set(false);
        this.errorModal.set(mensajeDeError(err, 'No se pudo guardar la clase.'));
      }
    });
  }

  cancelarClase(clase: ClaseApoyo): void {
    const aviso = clase.cantidad_suscritos > 0 ? ` Se les va a avisar a los ${clase.cantidad_suscritos} alumnos suscritos.` : '';
    if (!confirm(`¿Cancelar la clase de ${clase.materia.nombre} (${clase.horario})? Esta acción no se puede deshacer.${aviso}`)) {
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
