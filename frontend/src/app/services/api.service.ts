import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { API_URL } from '../api.config';
import {
  AccionModeracion, ClaseApoyo, EstadoSuscripcion, FiltroAnio, Materia, Material, MensajeClase, Notificacion, Ponderacion
} from '../models/api.models';

/** Datos que hay que mandar para crear o modificar una clase de apoyo. */
export interface DatosClaseApoyo {
  materia_id: number;
  /** 1 = lunes ... 6 = sábado */
  dia: number;
  /** "HH:MM" */
  hora_inicio: string;
  hora_fin: string;
  aula: string;
}

/**
 * Llamadas a la API de datos de RES-UTN. El token de login lo agrega solo el interceptor;
 * la sesión (quién está logueado) vive en AuthService.
 */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  // ---- materias ----
  /**
   * Sin filtros, todas las materias. `anio`: las de ese año (sin electivas) o solo las electivas.
   * `buscar`: las que contienen ese texto en el nombre, de cualquier año. Lo resuelve el backend sobre la base local.
   */
  getMaterias(filtros: { anio?: FiltroAnio; buscar?: string } = {}): Observable<Materia[]> {
    let params = new HttpParams();
    if (filtros.anio === 'electivas') {
      params = params.set('electiva', 'true');
    } else if (filtros.anio !== undefined) {
      params = params.set('anio', String(filtros.anio)).set('electiva', 'false');
    }
    if (filtros.buscar?.trim()) {
      params = params.set('buscar', filtros.buscar.trim());
    }
    return this.http.get<Materia[]>(`${API_URL}/materias/`, { params });
  }

  // ---- materiales (apuntes) ----
  /** Los validados más los propios pendientes. Con `materiaId`, solo los de esa materia. */
  getMateriales(materiaId?: number): Observable<Material[]> {
    return this.http.get<Material[]>(`${API_URL}/materiales/`, { params: this.filtro('materia', materiaId) });
  }

  getMaterial(id: number): Observable<Material> {
    return this.http.get<Material>(`${API_URL}/materiales/${id}/`);
  }

  /** `formData`: materia_id, titulo, tipo, comentario (opcional) y archivo. El autor sale del token. */
  subirMaterial(formData: FormData): Observable<Material> {
    return this.http.post<Material>(`${API_URL}/materiales/`, formData);
  }

  // ---- moderación (solo administradores) ----
  getMaterialesPendientes(): Observable<Material[]> {
    return this.http.get<Material[]>(`${API_URL}/materiales/pendientes/`);
  }

  /** `motivo` solo se usa al rechazar: el autor lo ve para poder corregir el apunte y reenviarlo. */
  moderarMaterial(id: number, accion: AccionModeracion, motivo?: string): Observable<unknown> {
    return this.http.post(`${API_URL}/materiales/${id}/moderar/`, motivo ? { accion, motivo } : { accion });
  }

  // ---- estrellas ----
  /** Las estrellas que puso el usuario logueado (la API solo devuelve las propias). */
  getMisPonderaciones(): Observable<Ponderacion[]> {
    return this.http.get<Ponderacion[]>(`${API_URL}/ponderaciones/`);
  }

  /** Puntúa un material de 1 a 5. Si ya lo había puntuado, cambia su voto. */
  ponderar(materialId: number, valor: number): Observable<Ponderacion> {
    return this.http.post<Ponderacion>(`${API_URL}/ponderaciones/`, { material_id: materialId, valor });
  }

  // ---- clases de apoyo ----
  getClasesApoyo(materiaId?: number): Observable<ClaseApoyo[]> {
    return this.http.get<ClaseApoyo[]>(`${API_URL}/clases-apoyo/`, { params: this.filtro('materia', materiaId) });
  }

  /** Solo tutores: la clase queda a nombre de quien está logueado. */
  crearClaseApoyo(datos: DatosClaseApoyo): Observable<ClaseApoyo> {
    return this.http.post<ClaseApoyo>(`${API_URL}/clases-apoyo/`, datos);
  }

  actualizarClaseApoyo(id: number, datos: DatosClaseApoyo): Observable<ClaseApoyo> {
    return this.http.patch<ClaseApoyo>(`${API_URL}/clases-apoyo/${id}/`, datos);
  }

  eliminarClaseApoyo(id: number): Observable<void> {
    return this.http.delete<void>(`${API_URL}/clases-apoyo/${id}/`);
  }

  // ---- suscripciones y mensajes de una clase ----
  /** Solo alumnos: empiezan a recibir avisos de los cambios y mensajes de la clase. */
  suscribirse(claseId: number): Observable<EstadoSuscripcion> {
    return this.http.post<EstadoSuscripcion>(`${API_URL}/clases-apoyo/${claseId}/suscripcion/`, {});
  }

  desuscribirse(claseId: number): Observable<EstadoSuscripcion> {
    return this.http.delete<EstadoSuscripcion>(`${API_URL}/clases-apoyo/${claseId}/suscripcion/`);
  }

  /** Los más nuevos primero. Los ven sus suscritos, su tutor y los administradores. */
  getMensajes(claseId: number): Observable<MensajeClase[]> {
    return this.http.get<MensajeClase[]>(`${API_URL}/clases-apoyo/${claseId}/mensajes/`);
  }

  /** El tutor de la clase (o un administrador): el mensaje les llega a todos los suscritos. */
  enviarMensaje(claseId: number, texto: string): Observable<MensajeClase> {
    return this.http.post<MensajeClase>(`${API_URL}/clases-apoyo/${claseId}/mensajes/`, { texto });
  }

  // ---- notificaciones ----
  getNotificaciones(): Observable<Notificacion[]> {
    return this.http.get<Notificacion[]>(`${API_URL}/notificaciones/`);
  }

  marcarNotificacionesLeidas(): Observable<{ marcadas: number }> {
    return this.http.post<{ marcadas: number }>(`${API_URL}/notificaciones/marcar-leidas/`, {});
  }

  private filtro(nombre: string, valor: number | undefined): HttpParams {
    return valor === undefined ? new HttpParams() : new HttpParams().set(nombre, String(valor));
  }
}
