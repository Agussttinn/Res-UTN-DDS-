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
  readonly cargando = signal(true);
  readonly error = signal('');
  readonly aviso = signal('');
  /** Id del apunte que se está aprobando o rechazando (para no permitir un doble clic). */
  readonly procesando = signal<number | null>(null);

  ngOnInit(): void {
    this.cargarPendientes();
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
    // Rechazar elimina el apunte y su archivo: no se puede deshacer.
    if (accion === 'rechazar' && !confirm(`¿Rechazar "${item.titulo}"? Se eliminará el apunte y su archivo.`)) {
      return;
    }

    this.procesando.set(item.id);
    this.aviso.set('');
    this.error.set('');

    this.api.moderarMaterial(item.id, accion).subscribe({
      next: () => {
        this.pendientes.update((lista) => lista.filter((p) => p.id !== item.id));
        this.aviso.set(accion === 'aprobar' ? `"${item.titulo}" fue aprobado y ya lo ven todos.` : `"${item.titulo}" fue rechazado y eliminado.`);
        this.procesando.set(null);
      },
      error: (err: unknown) => {
        this.error.set(mensajeDeError(err, 'No se pudo completar la acción.'));
        this.procesando.set(null);
      }
    });
  }
}
