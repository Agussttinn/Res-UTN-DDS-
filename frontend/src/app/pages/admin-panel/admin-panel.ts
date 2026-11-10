import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';

import { AccionModeracion, ETIQUETA_TIPO, Material } from '../../models/api.models';
import { ApiService } from '../../services/api.service';
import { mensajeDeError } from '../../utils/errores';

const DIA_MS = 24 * 60 * 60 * 1000;

export type Antiguedad = 'todas' | 'semana' | 'mes' | 'mas-mes' | 'mas-6-meses';

/** Rangos en días desde que se subió el apunte: [desde, hasta). */
const RANGOS: Record<Antiguedad, { desde: number; hasta: number }> = {
  todas: { desde: -Infinity, hasta: Infinity },
  semana: { desde: -Infinity, hasta: 7 },
  mes: { desde: -Infinity, hasta: 30 },
  'mas-mes': { desde: 30, hasta: Infinity },
  'mas-6-meses': { desde: 180, hasta: Infinity }
};

const ANTIGUEDADES: { valor: Antiguedad; etiqueta: string }[] = [
  { valor: 'todas', etiqueta: 'Cualquier antigüedad' },
  { valor: 'semana', etiqueta: 'Últimos 7 días' },
  { valor: 'mes', etiqueta: 'Últimos 30 días' },
  { valor: 'mas-mes', etiqueta: 'Más de 30 días' },
  { valor: 'mas-6-meses', etiqueta: 'Más de 6 meses' }
];

@Component({
  selector: 'app-admin-panel',
  standalone: true,
  imports: [DatePipe],
  templateUrl: './admin-panel.html',
  styleUrl: './admin-panel.css'
})
export class AdminPanelComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly etiquetaTipo = ETIQUETA_TIPO;

  readonly pendientes = signal<Material[]>([]);
  /** Aprobados: se pueden desaprobar (si se aprobaron sin querer), rechazar o archivar (fin de ciclo o cambio de plan). */
  readonly aprobados = signal<Material[]>([]);
  readonly cargando = signal(true);
  readonly error = signal('');
  readonly aviso = signal('');
  /** Id del apunte que se está aprobando o rechazando (para no permitir un doble clic). */
  readonly procesando = signal<number | null>(null);
  /** Apunte que se está por rechazar: mientras tiene valor se muestra la ventana para escribir el motivo. */
  readonly rechazando = signal<Material | null>(null);

  /** Filtro por antigüedad (cuánto hace que se subió el apunte) y orden de las listas. */
  readonly antiguedades = ANTIGUEDADES;
  readonly antiguedad = signal<Antiguedad>('todas');
  readonly orden = signal<'antiguos' | 'recientes'>('antiguos');
  readonly pendientesFiltrados = computed(() => this.aplicar(this.pendientes()));
  readonly aprobadosFiltrados = computed(() => this.aplicar(this.aprobados()));
  readonly motivo = signal('');

  ngOnInit(): void {
    this.cargarPendientes();
    this.cargarAprobados();
  }

  cargarAprobados(): void {
    this.api.getMateriales().subscribe({
      next: (data) => this.aprobados.set(data.filter((m) => m.estado === 'aprobado')),
      error: () => this.aprobados.set([]) // la cola de pendientes sigue funcionando sin esta lista
    });
  }

  cargarPendientes(): void {
    this.cargando.set(true);
    this.error.set('');
    this.api.getMaterialesPendientes().subscribe({
      next: (data) => {
        this.pendientes.set(data);
        this.cargando.set(false);
      },
      error: (err: unknown) => {
        this.error.set(mensajeDeError(err, 'No se pudieron cargar los apuntes pendientes.'));
        this.cargando.set(false);
      }
    });
  }

  /** Aplica el filtro de antigüedad y el orden (por fecha de carga). */
  private aplicar(lista: Material[]): Material[] {
    const { desde, hasta } = RANGOS[this.antiguedad()];
    const ahora = Date.now();
    const filtrada = lista.filter((m) => {
      const dias = (ahora - new Date(m.fecha_de_carga).getTime()) / DIA_MS;
      return dias >= desde && dias < hasta;
    });
    const signo = this.orden() === 'antiguos' ? 1 : -1;
    return [...filtrada].sort((a, b) => signo * (new Date(a.fecha_de_carga).getTime() - new Date(b.fecha_de_carga).getTime()));
  }

  moderar(item: Material, accion: AccionModeracion): void {
    if (accion === 'rechazar') {
      // El apunte no se borra: queda rechazado y el autor ve el motivo para poder corregirlo y reenviarlo.
      this.motivo.set('');
      this.rechazando.set(item);
      return;
    }
    if (accion === 'archivar' && !confirm(`¿Archivar "${item.titulo}"? Queda solo de lectura y ya no se puede puntuar.`)) {
      return;
    }
    this.ejecutar(item, accion);
  }

  cancelarRechazo(): void {
    this.rechazando.set(null);
  }

  confirmarRechazo(): void {
    const item = this.rechazando();
    if (!item) {
      return;
    }
    this.rechazando.set(null);
    this.ejecutar(item, 'rechazar', this.motivo().trim() || undefined);
  }

  private ejecutar(item: Material, accion: AccionModeracion, motivo?: string): void {
    this.procesando.set(item.id);
    this.aviso.set('');
    this.error.set('');

    this.api.moderarMaterial(item.id, accion, motivo).subscribe({
      next: () => {
        this.pendientes.update((lista) => lista.filter((p) => p.id !== item.id));
        this.aprobados.update((lista) => lista.filter((p) => p.id !== item.id));
        if (accion === 'aprobar') {
          this.cargarAprobados(); // el recién aprobado pasa a la lista de aprobados
        }
        if (accion === 'desaprobar') {
          this.cargarPendientes(); // el que volvió a pendiente reaparece en la cola
        }
        this.aviso.set(this.mensajeDe(accion, item.titulo));
        this.procesando.set(null);
      },
      error: (err: unknown) => {
        this.error.set(mensajeDeError(err, 'No se pudo completar la acción.'));
        this.procesando.set(null);
      }
    });
  }

  private mensajeDe(accion: AccionModeracion, titulo: string): string {
    switch (accion) {
      case 'aprobar':
        return `"${titulo}" fue aprobado y ya lo ven todos.`;
      case 'rechazar':
        return `"${titulo}" fue rechazado. El autor puede corregirlo y reenviarlo.`;
      case 'desaprobar':
        return `"${titulo}" volvió a pendiente: ya no lo ven los demás hasta que lo apruebes de nuevo.`;
      case 'archivar':
        return `"${titulo}" fue archivado.`;
    }
  }
}
