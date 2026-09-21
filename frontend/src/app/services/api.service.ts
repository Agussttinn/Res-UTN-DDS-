import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { API_URL } from '../api.config';
import { AccionModeracion, ClaseApoyo, Materia, Material, Ponderacion } from '../models/api.models';

/** Datos que hay que mandar para crear o modificar una clase de apoyo. */
export interface DatosClaseApoyo {
  materia_id: number;
  horario: string;
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
  getMaterias(): Observable<Materia[]> {
    return this.http.get<Materia[]>(`${API_URL}/materias/`);
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

  moderarMaterial(id: number, accion: AccionModeracion): Observable<unknown> {
    return this.http.post(`${API_URL}/materiales/${id}/moderar/`, { accion });
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

  private filtro(nombre: string, valor: number | undefined): HttpParams {
    return valor === undefined ? new HttpParams() : new HttpParams().set(nombre, String(valor));
  }
}
