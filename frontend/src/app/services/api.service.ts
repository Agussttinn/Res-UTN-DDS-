// @ts-ignore: Angular dependencies are resolved by the Angular build environment.
import { Injectable } from '@angular/core';
// @ts-ignore: Angular dependencies are resolved by the Angular build environment.
import { HttpClient } from '@angular/common/http';
// @ts-ignore: Angular dependencies are resolved by the Angular build environment.
import { Observable } from 'rxjs';

// @ts-ignore: tslib is provided by the Angular build environment.
@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = 'http://127.0.0.1:8000/api';

  constructor(private http: HttpClient) {}

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
}