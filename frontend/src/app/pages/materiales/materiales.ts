import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-materiales',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './materiales.html',
  styleUrl: './materiales.css'
})
export class MaterialesComponent implements OnInit {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);

  materiales: any[] = [];
  materias: any[] = [];
  cargando = true;
  filtroTipo = '';
  materiaSeleccionadaId: number | null = null;

  // Estado del formulario de carga
  mostrarModal = false;
  nuevoMaterial = {
    titulo: '',
    tipo: 'RESUMEN',
    materia: null,
    archivo: null as File | null
  };

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      const id = params.get('materiaId');
      this.materiaSeleccionadaId = id ? Number(id) : null;
      this.cargarDatos();
    });
  }

  cargarDatos(): void {
    this.cargando = true;
    this.api.getMaterias().subscribe({
      next: (mats) => this.materias = mats,
      error: (e) => console.error(e)
    });

    this.api.getMateriales(this.materiaSeleccionadaId ?? undefined).subscribe({
      next: (data) => {
        this.materiales = data;
        this.cargando = false;
      },
      error: (e) => {
        console.error(e);
        this.cargando = false;
      }
    });
  }

  get materialesFiltrados() {
    if (!this.filtroTipo) return this.materiales;
    return this.materiales.filter(m => m.tipo === this.filtroTipo);
  }

  darLike(item: any): void {
    this.api.darLike(item.id).subscribe({
      next: (res) => {
        item.likes_count = res.likes_count ?? (item.likes_count + 1);
      },
      error: (err) => console.error('Error al ponderar:', err)
    });
  }

  onFileSelected(event: any): void {
    const file: File = event.target.files[0];
    if (file) {
      this.nuevoMaterial.archivo = file;
    }
  }

subiendo = false;

subirRecurso(): void {
  if (!this.nuevoMaterial.titulo || !this.nuevoMaterial.materia || !this.nuevoMaterial.archivo) {
    alert('Completá el título, seleccioná la materia y adjuntá el archivo.');
    return;
  }

  this.subiendo = true;
  const data = new FormData();
  data.append('titulo', this.nuevoMaterial.titulo);
  data.append('tipo', this.nuevoMaterial.tipo);
  data.append('materia', String(this.nuevoMaterial.materia));
  data.append('archivo', this.nuevoMaterial.archivo);

  (this.api as any).subirMaterial(data).subscribe({
    next: () => {
      this.subiendo = false;
      this.mostrarModal = false;
      this.nuevoMaterial = { titulo: '', tipo: 'RESUMEN', materia: null, archivo: null };
      alert('¡Documento enviado con éxito! Queda a la espera de aprobación por un tutor.');
    },
    error: (err: unknown) => {
      console.error('Error al subir:', err);
      this.subiendo = false;
      alert('No se pudo subir el archivo. Verificá haber iniciado sesión.');
    }
  });
}
}