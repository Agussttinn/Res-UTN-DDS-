readme_content = """# 📚 RES-UTN — Portal Estudiantes (Primer Año)

Plataforma colaborativa web/PWA diseñada para centralizar, organizar y distribuir material académico y coordinar clases de apoyo para estudiantes de Ingeniería en Sistemas de Información de la **UTN FRD**.

---

## 📑 Tabla de Contenidos
- [Descripción del Proyecto](#-descripción-del-proyecto)
- [Problemática y Dominio](#-problemática-y-dominio)
- [Objetivos](#-objetivos)
  - [Objetivo General](#objetivo-general)
  - [Objetivos Específicos](#objetivos-específicos)
- [Requisitos del Sistema](#-requisitos-del-sistema)
  - [Requisitos Funcionales (RF)](#requisitos-funcionales-rf)
  - [Requisitos No Funcionales (RNF)](#requisitos-no-funcionales-rnf)
- [Casos de Uso](#-casos-de-uso)
- [Arquitectura y Modelado](#-arquitectura-y-modelado)
  - [Diagrama de Dominio](#1-diagrama-de-dominio)
  - [Diagrama Entidad-Relación (E-R)](#2-diagrama-entidad-relación-e-r)
  - [Diagrama de Estados (Material)](#3-diagrama-de-estados-entidad-material)
  - [Arquitectura de Software y Despliegue](#4-arquitectura-y-despliegue)
- [Roles de Usuario](#-roles-de-usuario)
- [Stack Tecnológico Sugerido](#-stack-tecnológico-sugerido)
- [Cronograma de Entregas](#-cronograma-de-entregas-académicas)

---

## 📌 Descripción del Proyecto

En el ámbito universitario, el rendimiento de los estudiantes depende en gran medida del acceso oportuno a material de estudio de calidad (resúmenes, parciales, finales) y a clases de consulta. **RES-UTN** busca resolver la brecha de comunicación y la dispersión de información, funcionando como un nexo horizontal entre los propios estudiantes (*"de alumnos para alumnos"*), tutores y administradores.

---

## 🔍 Problemática y Dominio

- **Dispersión de la Información (Pérdida de Trazabilidad):** Los recursos clave y fe de erratas suelen perderse en grupos no estructurados de mensajería (ej. WhatsApp) o carteleras físicas.
- **Pérdida de Integridad:** La información fragmentada entre distintas fuentes provoca apuntes incompletos o desactualizados.
- **Baja Disponibilidad:** Dificultad para encontrar exámenes anteriores o resúmenes acordes al programa vigente de cada cátedra/materia.
- **Falta de Difusión en Clases de Apoyo:** Clases de consulta subaprovechadas debido a la falta de un canal unificado y dinámico donde consultar días, horarios y aulas.

---

## 🎯 Objetivos

### Objetivo General
Desarrollar un sistema de información que centralice, valide y organice recursos académicos y horarios de clases de apoyo de las distintas materias de primer año de **Ingeniería en Sistemas de Información (UTN FRD)**.

### Objetivos Específicos
1. Centralizar resúmenes, parciales y finales por materia en una única plataforma accesible.
2. Facilitar la consulta y actualización en tiempo real de días, horarios y aulas de clases de apoyo.
3. Incorporar un sistema de moderación/validación y un esquema de ponderación comunitaria (likes/estrellas) para destacar el contenido más útil.
4. Diseñar con enfoque **Mobile-First** e implementar formato **PWA** instalable desde el navegador.

---

## ⚙️ Requisitos del Sistema

### Requisitos Funcionales (RF)
- **RF01:** Iniciar sesión con autenticación y permisos según rol.
- **RF02:** Consultar listado de materias de primer año.
- **RF03:** Visualizar y descargar resúmenes y apuntes validados.
- **RF04:** Consultar y descargar parciales y exámenes finales.
- **RF05:** Buscar y filtrar material académico por materia, tipo o tema.
- **RF06:** Publicar horarios, días y aulas de clases de apoyo (Tutores).
- **RF07:** Modificar o suspender clases de apoyo con notificación/actualización en tiempo real.
- **RF08:** Administrar, revisar y validar el contenido académico subido antes de su publicación general.

### Requisitos No Funcionales (RNF)
- **RNF01 (Usabilidad):** Interfaz clara, simple y adaptada a dispositivos móviles (*Mobile-First*).
- **RNF02 (Seguridad):** Acceso protegido mediante autenticación y control de acceso basado en roles (RBAC).
- **RNF03 (Consistencia):** Roles estrictamente definidos: *Alumno*, *Tutor* y *Administrador*.
- **RNF04 (Integridad):** Proceso de revisión y verificación previa del material académico.
- **RNF05 (Disponibilidad):** Alta disponibilidad en la entrega y descarga de archivos.
- **RNF06 (Rendimiento):** Tiempos de respuesta rápidos en búsquedas y consultas frecuentes.
- **RNF07 (Mantenibilidad):** Arquitectura modular y desacoplada para futuras extensiones.

---

## 👥 Casos de Uso

| Código | Caso de Uso | Actor | Descripción |
| :--- | :--- | :--- | :--- |
| **CU01** | Iniciar sesión | Todos | Autenticación en el sistema según rol asignado. |
| **CU02** | Consultar materias | Alumno | Navegación por la lista de materias de 1° año. |
| **CU03** | Consultar material validado | Alumno | Visualización y descarga de material académico autorizado. |
| **CU04** | Cargar material al sistema | Alumno | Carga de resúmenes, parciales o finales (quedan en estado *Pendiente*). |
| **CU05** | Filtrar material | Alumno | Búsqueda por materia, tipo de recurso o fecha. |
| **CU06** | Consultar clases de apoyo | Alumno | Visualización de grilla horaria semanal con aula y tutor a cargo. |
| **CU07** | Publicar clase de apoyo | Tutor | Carga de una nueva sesión de consulta (día, horario, aula, materia). |
| **CU08** | Modificar clase de apoyo | Tutor | Actualización inmediata de datos de una clase existente. |
| **CU09** | Suspender clase de apoyo | Tutor | Aviso masivo por cancelación o fuerza mayor. |
| **CU10** | Cargar material al sistema | Administrador | Subida directa de recursos institucionales o recopilados. |
| **CU11** | Validar contenido académico | Administrador | Revisión, aprobación o rechazo de archivos subidos por alumnos. |
| **CU12** | Editar contenido académico | Administrador | Modificación de metadatos o corrección de material en plataforma. |
| **CU13** | Gestionar usuarios y roles | Administrador | Asignación de permisos y gestión de cuentas. |

---

## 🏗️ Arquitectura y Modelado

### 1. Diagrama de Dominio
Representa las entidades del negocio:
- **Usuario** (Especializaciones: *Alumno*, *Tutor*, *Administrador*).
- **Material** (relacionado con Materia, Usuario y evaluado mediante Ponderaciones).
- **ClaseApoyo** (asignada a una Materia y dictada por un Tutor).
- **Materia** y **Especialidad**.

### 2. Diagrama Entidad-Relación (E-R)
- **`USUARIO`**: `(PK: legajo, nombre, correo, contraseña, rol)`
- **`ESPECIALIDAD`**: `(PK: idEspecialidad, nombre)`
- **`MATERIA`**: `(PK: idMateria, FK: idEspecialidad, nombre, año)`
- **`MATERIAL`**: `(PK: idMaterial, FK: idMateria, FK: legajoUsuario, titulo, fechaCarga, tipo, validacion, comentario)`
- **`CLASE_APOYO`**: `(PK: idClase, FK: idMateria, FK: legajoTutor, horario, aula)`
- **`PONDERACION`**: `(PK: idPonderacion, FK: idMaterial, FK: legajoUsuario, valor, fecha)`

### 3. Diagrama de Estados (Entidad: Material)
```text
  [ Subida por Alumno ]
           │
           ▼
 ┌───────────────────┐        Rechazado (Ilegible/Erróneo)
 │   PENDIENTE DE    │ ────────────────────────────────────────► [ Rechazado ]
 │     REVISIÓN      │                                                 │
 └─────────┬─────────┘                                                 │ (Reenvío)
           │ Aprobado por Admin                                        │
           ▼                                                           ▼
 ┌───────────────────┐ ◄───────────────────────────────────────────────┘
 │     APROBADO      │ ◄─── (Likes / Ponderación de Alumnos)
 │ (Visible en PWA)  │
 └─────────┬─────────┘
           │ Fin de ciclo lectivo / Cambio de plan
           ▼
 ┌───────────────────┐
 │    ARCHIVADO      │
 └───────────────────┘
