import { DatePipe, isPlatformBrowser } from '@angular/common';
import { Component, DestroyRef, ElementRef, OnInit, PLATFORM_ID, inject, signal } from '@angular/core';
import { Router } from '@angular/router';

import { TipoNotificacion } from '../../models/api.models';
import { NotificacionesService } from '../../services/notificaciones.service';

/** Cada cuánto se consultan avisos nuevos mientras la app está abierta. */
const INTERVALO_MS = 60_000;

/**
 * Campanita de la barra superior: cuántos avisos sin leer hay y el panel con la lista.
 * Los avisos llegan cuando una clase que el alumno sigue cambia, se cancela o su tutor manda un mensaje.
 */
@Component({
  selector: 'app-notificaciones',
  standalone: true,
  imports: [DatePipe],
  host: {
    class: 'relative',
    '(document:click)': 'clickAfuera($event)',
    '(keydown.escape)': 'abierto.set(false)'
  },
  template: `
    <button type="button" (click)="alternar()"
            [attr.aria-expanded]="abierto()" aria-controls="panel-notificaciones"
            [attr.aria-label]="servicio.noLeidas() ? 'Notificaciones: ' + servicio.noLeidas() + ' sin leer' : 'Notificaciones'"
            class="relative rounded-full p-2 hover:bg-white/10 transition-colors">
      <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
      </svg>
      @if (servicio.noLeidas()) {
        <span class="absolute -right-0.5 -top-0.5 min-w-[1.125rem] rounded-full bg-red-500 px-1 text-center text-[10px] font-bold leading-[1.125rem] text-white" aria-hidden="true">
          {{ servicio.noLeidas() > 9 ? '9+' : servicio.noLeidas() }}
        </span>
      }
    </button>

    @if (abierto()) {
      <div id="panel-notificaciones" role="region" aria-label="Notificaciones"
           class="absolute right-0 top-full z-50 mt-2 w-[min(22rem,calc(100vw-2rem))] overflow-hidden rounded-xl border border-slate-200 bg-white text-slate-800 shadow-xl">
        <div class="flex items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
          <h2 class="text-sm font-bold">Notificaciones</h2>
          @if (servicio.noLeidas()) {
            <button type="button" (click)="servicio.marcarTodasLeidas()" class="text-xs font-semibold text-brand-700 hover:underline">
              Marcar todas como leídas
            </button>
          }
        </div>
        <ul class="max-h-96 overflow-y-auto divide-y divide-slate-100">
          @for (aviso of servicio.lista(); track aviso.id) {
            <li>
              <button type="button" (click)="irAClases()"
                      [class]="aviso.leida ? 'bg-white' : 'bg-brand-50/60'"
                      class="flex w-full gap-3 px-4 py-3 text-left hover:bg-slate-50">
                <span class="mt-0.5 text-base" aria-hidden="true">{{ icono[aviso.tipo] }}</span>
                <span class="min-w-0 flex-1">
                  <span class="block text-sm" [class.font-semibold]="!aviso.leida">{{ aviso.titulo }}</span>
                  <span class="mt-0.5 block text-xs text-slate-600 line-clamp-3">{{ aviso.texto }}</span>
                  <span class="mt-1 block text-[11px] text-slate-400">{{ aviso.fecha | date: 'dd/MM HH:mm' }}</span>
                </span>
                @if (!aviso.leida) {
                  <span class="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-brand-600"><span class="sr-only">Sin leer</span></span>
                }
              </button>
            </li>
          } @empty {
            <li class="px-4 py-6 text-center text-sm text-slate-500">
              No tenés notificaciones. Suscribite a una clase de apoyo para enterarte de sus cambios y mensajes.
            </li>
          }
        </ul>
      </div>
    }
  `
})
export class NotificacionesComponent implements OnInit {
  protected readonly servicio = inject(NotificacionesService);
  private readonly router = inject(Router);
  private readonly host = inject(ElementRef<HTMLElement>);
  private readonly destroyRef = inject(DestroyRef);
  private readonly esNavegador = isPlatformBrowser(inject(PLATFORM_ID));

  protected readonly abierto = signal(false);
  protected readonly icono: Record<TipoNotificacion, string> = {
    modificacion: '✏️',
    cancelacion: '🚫',
    mensaje: '💬',
    rechazo: '📄'
  };

  ngOnInit(): void {
    if (!this.esNavegador) {
      return; // en el servidor (SSR) no hay sesión ni tiene sentido consultar
    }
    this.servicio.actualizar();
    const intervalo = setInterval(() => this.servicio.actualizar(), INTERVALO_MS);
    this.destroyRef.onDestroy(() => {
      clearInterval(intervalo);
      this.servicio.vaciar(); // al cerrar sesión no quedan los avisos del usuario anterior
    });
  }

  protected alternar(): void {
    this.abierto.update((abierto) => !abierto);
    if (this.abierto()) {
      this.servicio.actualizar();
    }
  }

  /** Los avisos son de clases de apoyo: llevan al cronograma. */
  protected irAClases(): void {
    this.abierto.set(false);
    this.router.navigate(['/clases']);
  }

  protected clickAfuera(evento: MouseEvent): void {
    if (this.abierto() && !this.host.nativeElement.contains(evento.target as Node)) {
      this.abierto.set(false);
    }
  }
}
