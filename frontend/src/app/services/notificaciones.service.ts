import { Injectable, computed, inject, signal } from '@angular/core';

import { Notificacion } from '../models/api.models';
import { ApiService } from './api.service';

/**
 * Los avisos del usuario logueado (cambios, cancelaciones y mensajes de las clases que sigue).
 * Los genera el backend con el patrón Observer; acá solo se consultan y se marcan como leídos.
 */
@Injectable({ providedIn: 'root' })
export class NotificacionesService {
  private readonly api = inject(ApiService);

  private readonly _lista = signal<Notificacion[]>([]);
  readonly lista = this._lista.asReadonly();
  readonly noLeidas = computed(() => this._lista().filter((n) => !n.leida).length);

  actualizar(): void {
    this.api.getNotificaciones().subscribe({
      next: (lista) => this._lista.set(lista),
      error: () => {} // si falla, se reintenta en la próxima consulta; la campanita sigue con lo que tenía
    });
  }

  marcarTodasLeidas(): void {
    if (this.noLeidas() === 0) {
      return;
    }
    // Se marca en pantalla enseguida; si el backend falla, se vuelve a pedir el estado real.
    this._lista.update((lista) => lista.map((n) => ({ ...n, leida: true })));
    this.api.marcarNotificacionesLeidas().subscribe({ error: () => this.actualizar() });
  }

  vaciar(): void {
    this._lista.set([]);
  }
}
