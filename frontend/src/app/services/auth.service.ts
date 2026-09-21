import { HttpClient } from '@angular/common/http';
import { Injectable, PLATFORM_ID, computed, inject, signal } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Router } from '@angular/router';
import { Observable, map, tap } from 'rxjs';

import { API_URL } from '../api.config';
import { RespuestaLogin, Rol, Usuario } from '../models/api.models';

const CLAVE_TOKEN = 'auth_token';
const CLAVE_USUARIO = 'auth_user';

/**
 * Sesión del usuario: quién está logueado, con qué rol y su token.
 * El estado es de tipo signal: las pantallas que lo leen se actualizan solas cuando cambia
 * (la app corre sin zonas, así que los datos "comunes" no refrescan la vista).
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly esNavegador = isPlatformBrowser(inject(PLATFORM_ID));

  private readonly _token = signal<string | null>(null);
  private readonly _usuario = signal<Usuario | null>(null);

  readonly usuario = this._usuario.asReadonly();
  readonly estaLogueado = computed(() => this._token() !== null && this._usuario() !== null);
  readonly rol = computed<Rol | null>(() => this._usuario()?.rol ?? null);
  readonly esAdministrador = computed(() => this.rol() === 'administrador');
  readonly esTutor = computed(() => this.rol() === 'tutor');

  constructor() {
    this.restaurarSesion();
  }

  token(): string | null {
    return this._token();
  }

  login(legajo: string, contrasena: string): Observable<Usuario> {
    return this.http
      .post<RespuestaLogin>(`${API_URL}/login/`, { legajo, contraseña: contrasena })
      .pipe(
        tap((respuesta) => this.guardarSesion(respuesta.access, respuesta.usuario)),
        map((respuesta) => respuesta.usuario),
      );
  }

  /** Da de alta un alumno (la API valida el legajo contra SySACAD). No inicia sesión. */
  registrar(legajo: string, contrasena: string): Observable<unknown> {
    return this.http.post(`${API_URL}/registro/`, { legajo, contraseña: contrasena });
  }

  cerrarSesion(): void {
    this.limpiarSesion();
    void this.router.navigate(['/login']);
  }

  /** El backend respondió 401 a un request con token: venció (dura 8 horas) o ya no es válido. */
  cerrarSesionPorVencimiento(): void {
    if (!this.estaLogueado()) {
      return; // ya se cerró (pasa cuando fallan varios requests a la vez)
    }
    this.limpiarSesion();
    void this.router.navigate(['/login'], { queryParams: { vencida: 1 } });
  }

  private guardarSesion(token: string, usuario: Usuario): void {
    this._token.set(token);
    this._usuario.set(usuario);
    this.escribirAlmacenamiento(CLAVE_TOKEN, token);
    this.escribirAlmacenamiento(CLAVE_USUARIO, JSON.stringify(usuario));
  }

  private limpiarSesion(): void {
    this._token.set(null);
    this._usuario.set(null);
    this.escribirAlmacenamiento(CLAVE_TOKEN, null);
    this.escribirAlmacenamiento(CLAVE_USUARIO, null);
  }

  /** Al abrir/recargar la página: recupera la sesión guardada, salvo que el token ya haya vencido. */
  private restaurarSesion(): void {
    const token = this.leerAlmacenamiento(CLAVE_TOKEN);
    const usuarioGuardado = this.leerAlmacenamiento(CLAVE_USUARIO);
    if (!token || !usuarioGuardado || this.tokenVencido(token)) {
      this.limpiarSesion();
      return;
    }
    try {
      this._usuario.set(JSON.parse(usuarioGuardado) as Usuario);
      this._token.set(token);
    } catch {
      this.limpiarSesion();
    }
  }

  /** Lee la fecha de vencimiento ("exp") que el backend puso dentro del token. */
  private tokenVencido(token: string): boolean {
    try {
      const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
      const { exp } = JSON.parse(atob(payload)) as { exp?: number };
      return typeof exp !== 'number' || exp * 1000 <= Date.now();
    } catch {
      return true;
    }
  }

  // localStorage puede no existir (render en servidor) o estar bloqueado (modo privado): nunca debe romper la app.
  private leerAlmacenamiento(clave: string): string | null {
    if (!this.esNavegador) {
      return null;
    }
    try {
      return localStorage.getItem(clave);
    } catch {
      return null;
    }
  }

  private escribirAlmacenamiento(clave: string, valor: string | null): void {
    if (!this.esNavegador) {
      return;
    }
    try {
      if (valor === null) {
        localStorage.removeItem(clave);
      } else {
        localStorage.setItem(clave, valor);
      }
    } catch {
      // sin almacenamiento: la sesión dura hasta que se cierre la pestaña
    }
  }
}
