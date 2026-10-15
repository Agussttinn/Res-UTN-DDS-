import { DatePipe, NgTemplateOutlet } from '@angular/common';
import { Component, Injector, OnInit, afterNextRender, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { switchMap } from 'rxjs';

import { BuscadorMateriaComponent } from '../../components/buscador-materia/buscador-materia.component';
import { EstrellasComponent } from '../../components/estrellas/estrellas.component';
import {
  ETIQUETA_TIPO, ETIQUETA_TIPO_PLURAL, FILTROS_ANIO, FiltroAnio, Materia, Material, TipoMaterial, esDelFiltro, filtroAnioDe
} from '../../models/api.models';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { erroresPorCampo, mensajeDeError } from '../../utils/errores';

// Mismas reglas que valida el backend (backend/core/archivos.py y models.py); se chequean acá para avisar antes de subir.
const EXTENSIONES_PERMITIDAS = ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'png', 'jpg', 'jpeg'];
const TAMANO_MAXIMO_MB = 10;
const LARGO_MAXIMO_TITULO = 100;

type CampoFormulario = 'materia' | 'tipo' | 'titulo' | 'archivo' | 'comentario';
type ErroresFormulario = Partial<Record<CampoFormulario, string>>;

/** id del control de cada campo, en el orden en que aparecen (se enfoca el primero con error). */
const ID_CAMPO: Record<CampoFormulario, string> = {
  materia: 'nueva-materia',
  tipo: 'nuevo-tipo-resumen',
  titulo: 'nuevo-titulo',
  archivo: 'nuevo-archivo',
  comentario: 'nuevo-comentario'
};

/** Campo del formulario al que corresponde cada campo que valida la API, para marcar ahí su error. */
const CAMPO_DE_LA_API: Record<string, CampoFormulario> = {
  materia_id: 'materia',
  tipo: 'tipo',
  titulo: 'titulo',
  archivo: 'archivo',
  comentario: 'comentario'
};

@Component({
  selector: 'app-materiales',
  standalone: true,
  imports: [DatePipe, NgTemplateOutlet, FormsModule, RouterLink, BuscadorMateriaComponent, EstrellasComponent],
  templateUrl: './materiales.html',
  styleUrl: './materiales.css'
})
export class MaterialesComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly injector = inject(Injector);

  readonly tipos: TipoMaterial[] = ['resumen', 'parcial', 'final'];
  readonly etiquetaTipo = ETIQUETA_TIPO;
  readonly etiquetaTipoPlural = ETIQUETA_TIPO_PLURAL;
  readonly colorTipo: Record<TipoMaterial, string> = {
    resumen: 'bg-brand-600 text-white',
    parcial: 'bg-amber-600 text-white',
    final: 'bg-purple-600 text-white'
  };
  readonly extensionesAceptadas = EXTENSIONES_PERMITIDAS.map((e) => `.${e}`).join(',');
  readonly tamanoMaximoMb = TAMANO_MAXIMO_MB;
  readonly largoMaximoTitulo = LARGO_MAXIMO_TITULO;

  readonly materiales = signal<Material[]>([]);
  readonly materias = signal<Materia[]>([]);
  /** Estrellas que puso el usuario logueado, por id de material. */
  readonly misVotos = signal<Record<number, number>>({});
  readonly cargando = signal(true);
  readonly error = signal('');
  /** Mensaje de éxito (por ejemplo, después de subir un apunte). */
  readonly aviso = signal('');
  readonly errorVoto = signal('');
  /** Id del apunte cuyo voto se está enviando. */
  readonly votando = signal<number | null>(null);

  readonly filtroTipo = signal<TipoMaterial | ''>('');
  readonly materiaSeleccionadaId = signal<number | null>(null);
  readonly materiaSeleccionada = computed(
    () => this.materias().find((m) => m.id === this.materiaSeleccionadaId()) ?? null
  );
  readonly materialesFiltrados = computed(() => {
    const tipo = this.filtroTipo();
    return tipo ? this.materiales().filter((m) => m.tipo === tipo) : this.materiales();
  });

  // Formulario de carga
  readonly mostrarModal = signal(false);
  readonly subiendo = signal(false);
  /** Error de cada campo: se muestra debajo de ese campo, que queda marcado en rojo. */
  readonly errores = signal<ErroresFormulario>({});
  /** Error del envío que no es de ningún campo (sin conexión, error del servidor...). */
  readonly errorEnvio = signal('');
  /** Hay un archivo arrastrado encima de la zona de carga. */
  readonly arrastrando = signal(false);
  /** Año de las materias que ofrece el buscador (las electivas van aparte). */
  readonly anioElegido = signal<FiltroAnio>(1);
  readonly materiaElegida = signal<number | null>(null);
  readonly archivoElegido = signal<File | null>(null);
  nuevoMaterial = this.materialVacio();

  readonly filtrosAnio = FILTROS_ANIO;
  /** Las materias del año elegido, que salen de la base local (GET /materias/). */
  readonly materiasDelAnio = computed(() => {
    const anio = this.anioElegido();
    return this.materias().filter((m) => esDelFiltro(m, anio));
  });

  ngOnInit(): void {
    this.cargarMaterias();
    this.cargarMisVotos();
    this.route.paramMap.subscribe((params) => {
      const id = params.get('materiaId');
      this.materiaSeleccionadaId.set(id ? Number(id) : null);
      this.cargarMateriales();
    });
  }

  /** `mostrarSpinner = false` recarga sin tapar la lista con "Buscando..." (por ejemplo, después de subir un apunte). */
  cargarMateriales(mostrarSpinner = true): void {
    if (mostrarSpinner) {
      this.cargando.set(true);
    }
    this.error.set('');
    this.api.getMateriales(this.materiaSeleccionadaId() ?? undefined).subscribe({
      next: (data) => {
        this.materiales.set(data);
        this.cargando.set(false);
      },
      error: (err: unknown) => {
        this.error.set(mensajeDeError(err, 'No se pudieron cargar los apuntes.'));
        this.cargando.set(false);
      }
    });
  }

  private cargarMaterias(): void {
    this.api.getMaterias().subscribe({
      next: (data) => this.materias.set(data),
      error: () => this.materias.set([]) // sin materias no se puede subir, pero la lista sigue funcionando
    });
  }

  private cargarMisVotos(): void {
    this.api.getMisPonderaciones().subscribe({
      next: (votos) => {
        const porMaterial: Record<number, number> = {};
        for (const voto of votos) {
          porMaterial[voto.material.id] = voto.valor;
        }
        this.misVotos.set(porMaterial);
      },
      error: () => this.misVotos.set({}) // sin esto solo no se resalta "tu voto"
    });
  }

  // ---- estrellas ----

  /** Solo se puntúan apuntes ya validados y que no sean propios (la API lo vuelve a verificar). */
  puedeVotar(item: Material): boolean {
    return item.validacion && item.usuario.legajo !== this.auth.usuario()?.legajo;
  }

  motivoSinVoto(item: Material): string {
    if (!item.validacion) {
      return 'Todavía está pendiente de revisión.';
    }
    return item.usuario.legajo === this.auth.usuario()?.legajo ? 'No podés puntuar tu propio apunte.' : '';
  }

  votar(item: Material, valor: number): void {
    this.votando.set(item.id);
    this.errorVoto.set('');

    // Guarda el voto y vuelve a pedir el apunte para traer el promedio nuevo, que calcula el backend.
    this.api
      .ponderar(item.id, valor)
      .pipe(switchMap(() => this.api.getMaterial(item.id)))
      .subscribe({
        next: (actualizado) => {
          this.misVotos.update((votos) => ({ ...votos, [item.id]: valor }));
          this.materiales.update((lista) => lista.map((m) => (m.id === actualizado.id ? actualizado : m)));
          this.votando.set(null);
        },
        error: (err: unknown) => {
          this.errorVoto.set(mensajeDeError(err, 'No se pudo registrar tu voto.'));
          this.votando.set(null);
        }
      });
  }

  // ---- carga de apuntes ----

  abrirModal(): void {
    const materia = this.materiaSeleccionada();
    this.nuevoMaterial = this.materialVacio();
    this.anioElegido.set(materia ? filtroAnioDe(materia) : 1);
    this.materiaElegida.set(materia?.id ?? null);
    this.archivoElegido.set(null);
    this.errores.set({});
    this.errorEnvio.set('');
    this.mostrarModal.set(true);

    // Arranca en el primer campo que falta completar.
    const primero: CampoFormulario = this.materiaElegida() === null ? 'materia' : 'titulo';
    afterNextRender(() => this.enfocar(primero), { injector: this.injector });
  }

  cerrarModal(): void {
    if (!this.subiendo()) {
      this.mostrarModal.set(false);
    }
  }

  errorDe(campo: CampoFormulario): string {
    return this.errores()[campo] ?? '';
  }

  /** Clases de un campo de texto o select: borde rojo si tiene error. */
  claseCampo(campo: CampoFormulario): string {
    const base =
      'w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2';
    return this.errorDe(campo)
      ? `${base} border-red-500 focus:border-red-500 focus:ring-red-500/20`
      : `${base} border-slate-300 focus:border-brand-500 focus:ring-brand-500/20`;
  }

  limpiarError(campo: CampoFormulario): void {
    if (this.errores()[campo]) {
      this.errores.update((errores) => {
        const resto = { ...errores };
        delete resto[campo];
        return resto;
      });
    }
  }

  elegirAnio(anio: FiltroAnio): void {
    this.anioElegido.set(anio);
    const elegida = this.materias().find((m) => m.id === this.materiaElegida());
    if (elegida && !esDelFiltro(elegida, anio)) {
      this.materiaElegida.set(null);
    }
  }

  /** Elegir una materia (también buscándola por nombre, de cualquier año) marca solo su año. */
  elegirMateria(id: number | null): void {
    this.materiaElegida.set(id);
    const materia = this.materias().find((m) => m.id === id);
    if (materia) {
      this.anioElegido.set(filtroAnioDe(materia));
      this.limpiarError('materia');
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.procesarArchivo(input.files?.[0] ?? null);
  }

  soltarArchivo(event: DragEvent): void {
    event.preventDefault();
    this.arrastrando.set(false);
    const archivo = event.dataTransfer?.files?.[0];
    if (archivo) {
      this.procesarArchivo(archivo);
    }
  }

  quitarArchivo(): void {
    this.procesarArchivo(null);
  }

  /** "850 KB", "2.4 MB". */
  tamanoLegible(bytes: number): string {
    return bytes < 1024 * 1024
      ? `${Math.max(1, Math.round(bytes / 1024))} KB`
      : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  private procesarArchivo(archivo: File | null): void {
    this.archivoElegido.set(null);
    this.limpiarError('archivo');
    if (!archivo) {
      this.vaciarInputArchivo();
      return;
    }

    const extension = archivo.name.split('.').pop()?.toLowerCase() ?? '';
    if (!EXTENSIONES_PERMITIDAS.includes(extension)) {
      this.rechazarArchivo(`Formato no permitido. Podés subir: ${EXTENSIONES_PERMITIDAS.join(', ')}.`);
      return;
    }
    if (archivo.size > TAMANO_MAXIMO_MB * 1024 * 1024) {
      this.rechazarArchivo(`El archivo no puede pesar más de ${TAMANO_MAXIMO_MB} MB.`);
      return;
    }
    this.archivoElegido.set(archivo);
  }

  private rechazarArchivo(mensaje: string): void {
    this.vaciarInputArchivo();
    this.errores.update((errores) => ({ ...errores, archivo: mensaje }));
  }

  private vaciarInputArchivo(): void {
    const input = document.getElementById(ID_CAMPO.archivo) as HTMLInputElement | null;
    if (input) {
      input.value = '';
    }
  }

  /** Lo que se puede revisar antes de enviar (el backend lo vuelve a validar). */
  private validar(): ErroresFormulario {
    const errores: ErroresFormulario = {};
    if (this.materiaElegida() === null) {
      errores.materia = 'Elegí una materia de la lista.';
    }
    if (!this.nuevoMaterial.titulo.trim()) {
      errores.titulo = 'Escribí un título para el apunte.';
    }
    if (!this.archivoElegido()) {
      // Si se rechazó el archivo elegido, se mantiene el motivo.
      errores.archivo = this.errorDe('archivo') || 'Adjuntá el archivo del apunte.';
    }
    return errores;
  }

  /** Marca los errores en sus campos y lleva el foco al primero. */
  private marcarErrores(errores: ErroresFormulario): void {
    this.errores.set(errores);
    const primero = (Object.keys(ID_CAMPO) as CampoFormulario[]).find((campo) => errores[campo]);
    if (primero) {
      this.enfocar(primero);
    }
  }

  private enfocar(campo: CampoFormulario): void {
    document.getElementById(ID_CAMPO[campo])?.focus();
  }

  subirRecurso(): void {
    if (this.subiendo()) {
      return;
    }
    this.errorEnvio.set('');
    const errores = this.validar();
    if (Object.keys(errores).length > 0) {
      this.marcarErrores(errores);
      return;
    }

    this.subiendo.set(true);
    const { titulo, tipo, comentario } = this.nuevoMaterial;

    // El autor no se manda: el backend lo toma del token de quien está logueado.
    const datos = new FormData();
    datos.append('titulo', titulo.trim());
    datos.append('tipo', tipo);
    datos.append('materia_id', String(this.materiaElegida()));
    if (comentario.trim()) {
      datos.append('comentario', comentario.trim());
    }
    datos.append('archivo', this.archivoElegido()!);

    this.api.subirMaterial(datos).subscribe({
      next: () => {
        this.subiendo.set(false);
        this.mostrarModal.set(false);
        this.aviso.set('¡Apunte enviado! Queda pendiente de revisión: cuando un administrador lo apruebe lo van a ver todos.');
        this.cargarMateriales(false); // así el autor ve su apunte pendiente en la lista
      },
      error: (err: unknown) => {
        this.subiendo.set(false);
        const porCampo: ErroresFormulario = {};
        for (const [campoApi, mensaje] of Object.entries(erroresPorCampo(err))) {
          const campo = CAMPO_DE_LA_API[campoApi];
          if (campo) {
            porCampo[campo] = mensaje;
          }
        }
        if (Object.keys(porCampo).length > 0) {
          this.marcarErrores(porCampo);
        } else {
          this.errorEnvio.set(mensajeDeError(err, 'No se pudo subir el archivo.'));
        }
      }
    });
  }

  private materialVacio() {
    return {
      titulo: '',
      tipo: 'resumen' as TipoMaterial,
      comentario: ''
    };
  }
}
