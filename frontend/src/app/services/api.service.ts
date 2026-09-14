import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private http = inject(HttpClient);
  private platformId = inject(PLATFORM_ID);
  private baseUrl = 'http://127.0.0.1:8000/api';

  getMaterias(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/materias/`);
  }

  getMateriales(materiaId?: number): Observable<any[]> {
    const url = materiaId 
      ? `${this.baseUrl}/materiales/?materia=${materiaId}` 
      : `${this.baseUrl}/materiales/`;
    return this.http.get<any[]>(url);
  }

  getClasesApoyo(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/clases/`);
  }

  darLike(materialId: number): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/materiales/${materialId}/like/`, {});
  }

  login(credentials: { username: string; password: string }): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/token/`, credentials);
  }

  setToken(token: string): void {
    if (isPlatformBrowser(this.platformId)) {
      localStorage.setItem('auth_token', token);
    }
  }

  getToken(): string | null {
    if (isPlatformBrowser(this.platformId)) {
      return localStorage.getItem('auth_token');
    }
    return null;
  }

  logout(): void {
    if (isPlatformBrowser(this.platformId)) {
      localStorage.removeItem('auth_token');
    }
  }

  isLoggedIn(): boolean {
    return !!this.getToken();
  }
  // Subida de archivos con FormData
  subirMaterial(formData: FormData): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/materiales/`, formData);
  }

  // Obtener pendientes de moderación (tutores/admin)
  getMaterialesPendientes(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/materiales/pendientes/`);
  }

  // Aprobar o rechazar apunte
  moderarMaterial(id: number, accion: 'aprobar' | 'rechazar'): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/materiales/${id}/moderar/`, { accion });
  }
}