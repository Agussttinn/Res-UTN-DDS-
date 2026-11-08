import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';

import { AccionModeracion, ETIQUETA_TIPO, Material } from '../../models/api.models';
import { ApiService } from '../../services/api.service';
import { mensajeDeError } from '../../utils/errores';

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
  /** Aprobados que se pueden archivar (fin de ciclo lectivo o cambio de plan de estudio). */
  readonly aprobados = signal<Material[]>([]);
  readonly cargando = signal(true);
  readonly error = signal('');
  readonly aviso = signal('');
  /** Id del apunte que se está aprobando o rechazando (para no permitir un doble clic). */
  readonly procesando = signal<number | null>(null);

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

  moderar(item: Material, accion: AccionModeracion): void {
    let motivo: string | undefined;
    if (accion === 'rechazar') {
      // El apunte no se borra: queda rechazado y el autor ve el motivo para poder corregirlo y reenviarlo.
      const respuesta = prompt(`¿Por qué se rechaza "${item.titulo}"? El autor va a ver este motivo.`);
      if (respuesta === null) {
        return; // canceló
      }
      motivo = respuesta.trim() || undefined;
    } else if (accion === 'archivar' && !confirm(`¿Archivar "${item.titulo}"? Queda solo de lectura y ya no se puede puntuar.`)) {
      return;
    }

    this.procesando.set(item.id);
    this.aviso.set('');
    this.error.set('');

    this.api.moderarMaterial(item.id, accion, motivo).subscribe({
      next: () => {
        this.pendientes.update((lista) => lista.filter((p) => p.id !== item.id));
        this.aprobados.update((lista) => lista.filter((p) => p.id !== item.id));
        if (accion === 'aprobar') {
          this.cargarAprobados(); // el recién aprobado pasa a la lista de archivables
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
      case 'archivar':
        return `"${titulo}" fue archivado.`;
    }
  }
}
