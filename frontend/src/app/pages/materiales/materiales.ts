import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { switchMap } from 'rxjs';

import { EstrellasComponent } from '../../components/estrellas/estrellas.component';
import { ETIQUETA_TIPO, ETIQUETA_TIPO_PLURAL, Materia, Material, TipoMaterial } from '../../models/api.models';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { mensajeDeError } from '../../utils/errores';

// Mismas reglas que valida el backend (backend/core/archivos.py); se chequean acá para avisar antes de subir.
const EXTENSIONES_PERMITIDAS = ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'png', 'jpg', 'jpeg'];
const TAMANO_MAXIMO_MB = 10;

@Component({
  selector: 'app-materiales',
  standalone: true,
  imports: [DatePipe, FormsModule, RouterLink, EstrellasComponent],
  templateUrl: './materiales.html',
  styleUrl: './materiales.css'
})
export class MaterialesComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);

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
  readonly errorModal = signal('');
  nuevoMaterial = this.materialVacio();

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
    this.nuevoMaterial = this.materialVacio();
    this.nuevoMaterial.materia = this.materiaSeleccionadaId();
    this.errorModal.set('');
    this.mostrarModal.set(true);
  }

  cerrarModal(): void {
    this.mostrarModal.set(false);
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const archivo = input.files?.[0] ?? null;
    this.errorModal.set('');
    this.nuevoMaterial.archivo = null;
    if (!archivo) {
      return;
    }

    const extension = archivo.name.split('.').pop()?.toLowerCase() ?? '';
    if (!EXTENSIONES_PERMITIDAS.includes(extension)) {
      this.rechazarArchivo(input, `Formato no permitido. Podés subir: ${EXTENSIONES_PERMITIDAS.join(', ')}.`);
      return;
    }
    if (archivo.size > TAMANO_MAXIMO_MB * 1024 * 1024) {
      this.rechazarArchivo(input, `El archivo no puede pesar más de ${TAMANO_MAXIMO_MB} MB.`);
      return;
    }
    this.nuevoMaterial.archivo = archivo;
  }

  private rechazarArchivo(input: HTMLInputElement, mensaje: string): void {
    input.value = '';
    this.errorModal.set(mensaje);
  }

  subirRecurso(): void {
    const { titulo, tipo, materia, comentario, archivo } = this.nuevoMaterial;
    if (!titulo.trim() || materia === null || !archivo) {
      this.errorModal.set('Completá el título, seleccioná la materia y adjuntá el archivo.');
      return;
    }

    this.subiendo.set(true);
    this.errorModal.set('');

    // El autor no se manda: el backend lo toma del token de quien está logueado.
    const datos = new FormData();
    datos.append('titulo', titulo.trim());
    datos.append('tipo', tipo);
    datos.append('materia_id', String(materia));
    if (comentario.trim()) {
      datos.append('comentario', comentario.trim());
    }
    datos.append('archivo', archivo);

    this.api.subirMaterial(datos).subscribe({
      next: () => {
        this.subiendo.set(false);
        this.mostrarModal.set(false);
        this.aviso.set('¡Apunte enviado! Queda pendiente de revisión: cuando un administrador lo apruebe lo van a ver todos.');
        this.cargarMateriales(false); // así el autor ve su apunte pendiente en la lista
      },
      error: (err: unknown) => {
        this.subiendo.set(false);
        this.errorModal.set(mensajeDeError(err, 'No se pudo subir el archivo.'));
      }
    });
  }

  private materialVacio() {
    return {
      titulo: '',
      tipo: 'resumen' as TipoMaterial,
      materia: null as number | null,
      comentario: '',
      archivo: null as File | null
    };
  }
}
