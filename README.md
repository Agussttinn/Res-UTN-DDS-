# 📚 RES-UTN — Portal Estudiantes (Primer Año)

Plataforma colaborativa web/PWA diseñada para centralizar, organizar y distribuir material académico y coordinar clases de apoyo para estudiantes de Ingeniería en Sistemas de Información de la **UTN FRD**.

---

## 📑 Tabla de Contenidos
- [Descripción del Proyecto](#-descripción-del-proyecto)
- [Problemática y Dominio](#-problemática-y-dominio)
- [Objetivos](#-objetivos)
  - [Objetivo General](#objetivo-general)
  - [Objetivos Específicos](#objetivos-específicos)
- [Requisitos del Sistema](#️-requisitos-del-sistema)
  - [Requisitos Funcionales (RF)](#requisitos-funcionales-rf)
  - [Requisitos No Funcionales (RNF)](#requisitos-no-funcionales-rnf)
- [Casos de Uso](#-casos-de-uso)
- [Arquitectura y Modelado](#️-arquitectura-y-modelado)
  - [Diagrama de Dominio](#1-diagrama-de-dominio)
  - [Diagrama Entidad-Relación (E-R)](#2-diagrama-entidad-relación-e-r)
  - [Diagrama de Estados (Material)](#3-diagrama-de-estados-entidad-material)
  - [Arquitectura de Software y Despliegue](#4-arquitectura-y-despliegue)
- [Roles de Usuario](#-roles-de-usuario)
- [Stack Tecnológico Sugerido](#-stack-tecnológico-sugerido)
- [Cronograma de Entregas](#-cronograma-de-entregas-académicas)
- [Puesta en Marcha del Entorno de Desarrollo](#-puesta-en-marcha-del-entorno-de-desarrollo)
  - [Requisitos Previos](#requisitos-previos)
  - [1. Clonar el Repositorio](#1-clonar-el-repositorio)
  - [2. Instalar y Configurar MariaDB](#2-instalar-y-configurar-mariadb)
  - [3. Backend: Entorno Virtual y Dependencias](#3-backend-entorno-virtual-y-dependencias)
  - [4. Variables de Entorno (.env)](#4-variables-de-entorno-env)
  - [5. Migraciones y Superusuario](#5-migraciones-y-superusuario)
  - [6. Dependencias del Mock de SySACAD y del Frontend](#6-dependencias-del-mock-de-sysacad-y-del-frontend)
  - [7. Levantar Todo el Entorno](#7-levantar-todo-el-entorno)
  - [8. Cargar los Primeros Datos](#8-cargar-los-primeros-datos)
  - [9. Recorrido de Prueba](#9-recorrido-de-prueba)
- [API REST](#-api-rest)
  - [Autenticación](#autenticación)
  - [Permisos por Rol](#permisos-por-rol)
  - [Endpoints](#endpoints)
  - [Reglas de Negocio](#reglas-de-negocio)
  - [Errores](#errores)
- [Tests](#-tests)
- [Problemas Frecuentes](#-problemas-frecuentes)
- [Consideraciones Importantes](#️-consideraciones-importantes)

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
3. Incorporar un sistema de moderación/validación y un esquema de ponderación comunitaria (estrellas de 1 a 5, con promedio) para destacar el contenido más útil.
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
```

---

## 🚀 Puesta en Marcha del Entorno de Desarrollo

El proyecto tiene tres partes que corren juntas en tu máquina:

| Parte | Tecnología | Carpeta | Puerto |
| :--- | :--- | :--- | :---: |
| **Backend (API)** | Django 5 + Django REST Framework + MariaDB | `backend/` | 8000 |
| **Mock de SySACAD** | Node + Express (simula el sistema académico de la UTN) | `backend/core/mock-sysacad/` | 4000 |
| **Frontend** | Angular + Tailwind CSS (PWA) | `frontend/` | 4200 |

Esta guía funciona en **Linux, macOS y Windows**. Donde los comandos cambian se muestran las versiones de cada sistema.

### Requisitos Previos
- **Python 3.12+**
- **Node.js 22.22.3+** (LTS; también sirve la 24.15+). Incluye `npm`. Lo exige Angular y también lo usan el mock y el script `dev.mjs`.
- **Git**
- **MariaDB Server** (o MySQL, es compatible)
- **Postman** (opcional, para probar la API)

### 1. Clonar el Repositorio
```bash
git clone https://github.com/Agussttinn/Res-UTN-DDS-.git
cd Res-UTN-DDS-
```
El backend vive en `backend/`, separado del frontend (`frontend/`), para que cada parte del equipo trabaje sin pisarse.

### 2. Instalar y Configurar MariaDB

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install mariadb-server mariadb-client
sudo systemctl enable --now mariadb
sudo mysql_secure_installation
```
En Ubuntu/Debian el usuario `root` de MariaDB usa autenticación por `unix_socket` (se valida con tu usuario del sistema, no con contraseña): es normal que `mysql_secure_installation` no te deje ponerle password a `root`. Para entrar a la consola: `sudo mysql -u root`.

**macOS:**
```bash
brew install mariadb
brew services start mariadb
mysql -u root
```

**Windows:** descargá el instalador (MSI) desde [mariadb.org/download](https://mariadb.org/download/). Durante la instalación te pide una contraseña para `root` (anotala). Después abrí **MariaDB Command Prompt** desde el menú Inicio (o HeidiSQL, que viene con el instalador) y entrá con `mysql -u root -p`.

Ya adentro de la consola, en cualquier sistema, crear la base de datos y un usuario propio para la app (no usar `root` desde Django):
```sql
CREATE DATABASE resutn_db CHARACTER SET utf8mb4;
CREATE USER 'resutn_user'@'localhost' IDENTIFIED BY 'tu_password_local';
GRANT ALL PRIVILEGES ON resutn_db.* TO 'resutn_user'@'localhost';
-- Para poder correr los tests: Django crea y borra una base temporal llamada test_resutn_db
GRANT ALL PRIVILEGES ON `test_resutn_db`.* TO 'resutn_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 3. Backend: Entorno Virtual y Dependencias
Cada persona del equipo crea su **propio** entorno virtual local (no se sube a git). El entorno **tiene que llamarse `DSWenv`** y estar dentro de `backend/`.

**Linux / macOS:**
```bash
cd backend
python3 -m venv DSWenv
source DSWenv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**
```powershell
cd backend
python -m venv DSWenv
DSWenv\Scripts\Activate.ps1
pip install -r requirements.txt
```
Si PowerShell no te deja activar el entorno por la política de ejecución, corré una vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. En **cmd** el comando es `DSWenv\Scripts\activate.bat`.

> Activar el entorno solo hace falta para los comandos manuales de `manage.py` (migrar, tests, etc.). El script `dev.mjs` usa directamente el Python de `DSWenv`, así que no necesita que lo actives.

### 4. Variables de Entorno (.env)
Las credenciales de la base de datos **no** están en `settings.py` ni se suben a git: se leen de un archivo `.env` local. Copiá la plantilla y completá tus datos:

```bash
# Linux / macOS (desde la carpeta backend/)
cp .env.example .env
```
```powershell
# Windows (desde la carpeta backend\)
copy .env.example .env
```

Editá `backend/.env` con los valores del paso 2:
```
DB_NAME=resutn_db
DB_USER=resutn_user
DB_PASSWORD=tu_password_local
DB_HOST=localhost
DB_PORT=3306
```
`.env.example` también lista algunas variables **opcionales** (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `SYSACAD_API_URL`) que en desarrollo ya tienen un valor por defecto. `SECRET_KEY` (firma los tokens de login) solo es obligatoria en producción.

### 5. Migraciones y Superusuario
Con el entorno virtual activado, desde `backend/`:
```bash
python manage.py migrate
python manage.py createsuperuser
```
El **superusuario de Django** sirve únicamente para entrar al panel interno `http://127.0.0.1:8000/admin/`. No es un usuario de RES-UTN: los usuarios de la aplicación (alumnos, tutores, administradores) se manejan aparte, como se explica en el paso 8.

### 6. Dependencias del Mock de SySACAD y del Frontend
```bash
cd backend/core/mock-sysacad
npm install
cd ../../../frontend
npm install
```

### 7. Levantar Todo el Entorno
Desde la **raíz del repo**, con un solo comando se levantan los tres servicios:

```bash
node dev.mjs      # Windows, macOS y Linux
./dev.sh          # atajo equivalente en macOS y Linux
```

Cada servicio muestra su salida con un prefijo de color, y al arrancar te avisa las direcciones:
- `[BACKEND]` (azul) → Django en http://127.0.0.1:8000
- `[MOCK]` (amarillo) → mock de SySACAD en http://localhost:4000
- `[FRONTEND]` (verde) → Angular en http://localhost:4200

Esperá unos 15 segundos y abrí **http://localhost:4200**. Para detener los tres juntos: `Ctrl+C` en esa misma terminal.

Antes de arrancar, el script revisa que exista el entorno virtual, el `backend/.env`, las carpetas `node_modules` y que los puertos 8000, 4000 y 4200 estén libres. Si falta algo, te lo lista completo junto con el comando para resolverlo.

<details>
<summary>Levantar cada servicio a mano (útil para depurar)</summary>

En tres terminales distintas:
```bash
# 1) Backend (con el entorno virtual activado)
cd backend && python manage.py runserver

# 2) Mock de SySACAD
cd backend/core/mock-sysacad && npm run start

# 3) Frontend
cd frontend && npm start
```
</details>

**Después de cada `git pull`**, si cambiaron dependencias o el modelo de datos, corré (con el entorno virtual activado): `pip install -r requirements.txt`, `python manage.py migrate` y, en `frontend/`, `npm install`.

### 8. Cargar los Primeros Datos
La base arranca vacía. Para poder probar la aplicación hace falta cargar:

**Usuarios.** Entrá a `http://127.0.0.1:8000/admin/` (con tu superusuario) → **Usuarios** → **Añadir**. Completá legajo, nombre y apellido, correo, rol y contraseña. La contraseña se escribe en texto normal y el panel la guarda **hasheada**.
- Los **alumnos** normalmente no se cargan a mano: se registran solos en `http://localhost:4200/registro` con su legajo, que se valida contra el mock de SySACAD (de ahí salen su nombre y su correo).
- Los **tutores y administradores** los da de alta un administrador. Cargá al menos **un administrador**: es quien modera los apuntes.

**Materias.** Dos caminos:
- **A mano (recomendado para probar):** en `/admin/` creá una **Especialidad** y unas pocas **Materias** de año 1. Los campos *Codigo sysacad* e *Id sysacad* son opcionales. Si querés que la importación de más abajo las reconozca en vez de duplicarlas, completalos con los valores reales: `ISI` para la especialidad y, por ejemplo, `5-2023-101` (Análisis Matemático I), `5-2023-102` (Álgebra y Geometría Analítica) o `5-2023-103` (Física I) para las materias.
- **Importar desde SySACAD:** `POST /api/materias/sincronizar/ISI/` con el token de un administrador (ver [Autenticación](#autenticación)). Las carreras disponibles en el mock son `ISI`, `QUI`, `ELE` y `MEC`. Ojo: el plan de ISI tiene **344 materias** y solo 8 son de primer año.

**Alumnos del mock para registrar:** el listado completo está en `backend/core/mock-sysacad/data/alumnos.json` (11 alumnos). Algunos: `48293` Sofía Martínez, `47110` Nicolás Fernández, `45820` Camila Rodríguez, `44005` Tomás López.

### 9. Recorrido de Prueba
Abrí `http://localhost:4200`. El navegador comparte la sesión entre pestañas: para ser **dos personas a la vez** usá una ventana de incógnito o un segundo navegador.

| # | Quién | Qué hacer | Qué deberías ver |
| :---: | :--- | :--- | :--- |
| 1 | nadie | abrir `/materias` | te manda a `/login` |
| 2 | un alumno | iniciar sesión | vuelve a Materias; arriba figura su nombre y rol; **no** aparece "Moderación" |
| 3 | el alumno | Ver Recursos → **Compartir Apunte** → subir un PDF | aviso verde y el apunte con la etiqueta "Pendiente de revisión" |
| 4 | un administrador (en incógnito) | menú **Moderación** → **Aprobar** | el apunte sale de la cola y ya lo ven todos |
| 5 | un alumno nuevo | `/registro` con un legajo del mock | crea la cuenta y entra solo, con su nombre de SySACAD |
| 6 | el alumno nuevo | tocar las estrellas de un apunte | "Tu voto" y el promedio; el autor no puede puntuar el suyo |
| 7 | un tutor | Clases de Apoyo → **Publicar clase** | aparece la clase; solo su tutor la puede modificar o cancelar |

---

## 🔌 API REST

URL base: `http://127.0.0.1:8000/api`. Toda la API responde JSON y **requiere estar logueado**, salvo `login` y `registro`.

### Autenticación
1. Iniciar sesión: `POST /api/login/` con el cuerpo `{"legajo": "13359", "contraseña": "tu_clave"}`. Responde `{"access": "<token>", "usuario": {...}}`.
2. Mandar el token en cada request: header `Authorization: Bearer <token>`.

En **Postman**: hacé el login, copiá el valor de `access`, y en los demás requests abrí la pestaña **Authorization**, elegí **Bearer Token** y pegalo.
```bash
curl -X POST http://127.0.0.1:8000/api/login/ -H "Content-Type: application/json" \
     -d '{"legajo": "13359", "contraseña": "tu_clave"}'
curl http://127.0.0.1:8000/api/materias/ -H "Authorization: Bearer <token>"
```
- El token dura **8 horas**; después hay que volver a iniciar sesión (responde `401`).
- Login y registro admiten **10 intentos por minuto** por IP (después responden `429`).
- El rol se consulta en la base en cada request: si a alguien le cambian el rol o lo borran, se aplica al instante.

### Permisos por Rol

| Recurso | Alumno | Tutor | Administrador |
| :--- | :--- | :--- | :--- |
| Materias y especialidades | leer | leer | leer y escribir |
| Usuarios | ver el propio | ver el propio | todo (así se dan de alta tutores y administradores) |
| Materiales | ver los validados y los propios; subir; editar sus pendientes; borrar los propios | igual que el alumno | todo, y modera |
| Clases de apoyo | leer | leer; publicar; modificar o cancelar las propias | todo (para crear una necesita indicar el tutor) |
| Ponderaciones (estrellas) | puntuar; ver las propias | igual | puntuar; ver todas |

### Endpoints

| Método y ruta | Quién | Descripción |
| :--- | :--- | :--- |
| `POST /login/` | público | Devuelve el token y los datos del usuario |
| `POST /registro/` | público | Crea la cuenta de un alumno validando el legajo contra SySACAD |
| `GET` `POST /usuarios/` | administrador | Listar / dar de alta usuarios |
| `GET` `PUT` `PATCH` `DELETE /usuarios/{legajo}/` | `GET`: uno mismo o administrador; el resto, administrador | Ver / modificar / borrar |
| `GET` `POST /especialidades/` | `GET`: logueado; `POST`: administrador | Listar / crear |
| `GET` `PUT` `PATCH` `DELETE /especialidades/{id}/` | `GET`: logueado; resto: administrador | Detalle / modificar / borrar |
| `GET` `POST /materias/` | `GET`: logueado; `POST`: administrador | Listar / crear |
| `GET` `PUT` `PATCH` `DELETE /materias/{id}/` | `GET`: logueado; resto: administrador | Detalle / modificar / borrar |
| `POST /materias/sincronizar/{carrera}/` | administrador | Importa el plan de estudio de SySACAD (`ISI`, `QUI`, `ELE`, `MEC`) |
| `GET /materiales/?materia={id}` | logueado | Materiales visibles para quien consulta; el filtro es opcional |
| `POST /materiales/` | logueado | Sube un material (`multipart/form-data`); queda **pendiente** |
| `GET` `PUT` `PATCH` `DELETE /materiales/{id}/` | ver: logueado; modificar: autor (si sigue pendiente) o administrador; borrar: autor o administrador | Detalle / modificar / borrar |
| `GET /materiales/pendientes/` | administrador | Cola de moderación, los más viejos primero |
| `POST /materiales/{id}/moderar/` | administrador | Aprueba o rechaza un material |
| `GET /clases-apoyo/?materia={id}` | logueado | Listar clases; el filtro es opcional |
| `POST /clases-apoyo/` | tutor o administrador | Publicar una clase |
| `GET` `PUT` `PATCH` `DELETE /clases-apoyo/{id}/` | ver: logueado; resto: su tutor o administrador | Detalle / modificar / cancelar |
| `GET /ponderaciones/?material={id}` | logueado | Las estrellas propias (el administrador ve todas) |
| `POST /ponderaciones/` | logueado | Puntuar un material |
| `GET` `PUT` `PATCH` `DELETE /ponderaciones/{id}/` | su dueño o administrador | Detalle / cambiar las estrellas / borrar |

**Cuerpos de ejemplo:**
```jsonc
// POST /registro/  y  POST /login/
{ "legajo": "48293", "contraseña": "miclave123" }

// POST /usuarios/  (administrador)
{ "legajo": "150", "nombre_y_apellido": "Tomás Tutor", "correo": "tomas@utn.edu.ar", "rol": "tutor", "contraseña": "claveSegura123" }

// POST /materiales/  -> multipart/form-data con estos campos (el autor sale del token, no se manda)
//   materia_id=1  titulo="Resumen U1"  tipo=resumen|parcial|final  comentario="(opcional)"  archivo=<el archivo>

// POST /materiales/7/moderar/  (administrador)
{ "accion": "aprobar" }        // o "rechazar"

// POST /clases-apoyo/  (tutor; un administrador debe agregar además "tutor_id": "<legajo del tutor>")
{ "materia_id": 1, "horario": "Lun 14:00-16:00", "aula": "L-203" }

// POST /ponderaciones/  (estrellas de 1 a 5; el usuario sale del token)
{ "material_id": 7, "valor": 4 }
```
Al **leer**, las relaciones vienen anidadas (por ejemplo `material.materia.nombre`); al **escribir** se manda solo el id (`materia_id`, `material_id`).

### Reglas de Negocio
- **Moderación:** un material nace *pendiente* y solo lo ven su autor y los administradores. Un administrador lo **aprueba** (queda visible para todos) o lo **rechaza** (se **elimina** el material y su archivo). Mientras está pendiente el autor puede editarlo; una vez validado solo lo modifica un administrador.
- **Archivos:** `pdf`, `doc`, `docx`, `ppt`, `pptx`, `xls`, `xlsx`, `txt`, `png`, `jpg` y `jpeg`, de hasta **10 MB**. Se guardan en `backend/media/` (no se sube a git) con un nombre aleatorio.
- **Estrellas:** de 1 a 5, un voto por usuario y por material (votar de nuevo cambia el voto). No se puede puntuar el **propio** material ni uno **pendiente**. Cada material trae `promedio_ponderacion` (con un decimal, o `null` si nadie votó) y `cantidad_ponderaciones`.
- **Registro:** el legajo se valida contra SySACAD (de ahí salen el nombre y el correo) y la cuenta siempre queda con rol `alumno`. La contraseña debe tener al menos 8 caracteres, no ser una clave común ni solo números.
- **Clases de apoyo:** las publica un tutor y quedan a su nombre. Un administrador puede modificar o cancelar cualquiera.
- **Borrados protegidos:** si algo tiene otros registros que dependen de él (un usuario con material, una especialidad con materias) el borrado responde `409` en vez de romper.

### Errores
La API responde con estos formatos: `{"error": "..."}` (vistas propias), `{"detail": "..."}` (permisos y token) y `{"campo": ["..."]}` (validación de formularios).

| Código | Significado |
| :---: | :--- |
| `400` | Datos inválidos: el cuerpo explica qué campo falló |
| `401` | Falta el token, está vencido, o las credenciales son incorrectas |
| `403` | Estás logueado pero tu rol no permite esa acción |
| `404` | No existe, o no tenés permiso para verlo (por ejemplo, un material pendiente ajeno) |
| `409` | No se puede borrar: otros registros dependen de este |
| `429` | Demasiados intentos de login o registro |
| `502` | No se pudo consultar a SySACAD |

---

## 🧪 Tests

```bash
# Backend (con el entorno virtual activado, desde backend/)
python manage.py test core

# Frontend (desde frontend/)
npx ng test --watch=false
```
Los tests del backend crean y borran una base temporal (`test_resutn_db`), por eso el usuario de MariaDB necesita el permiso del paso 2. Los del frontend cubren la sesión, el interceptor, las guardas de ruta y cada pantalla, con la API simulada.

---

## 🩺 Problemas Frecuentes

| Síntoma | Causa y solución |
| :--- | :--- |
| Una pantalla queda en "Cargando..." o falla la conexión | El backend no está corriendo, o hay otra cosa usando el puerto 8000 |
| `dev.mjs` dice que un puerto ya está en uso | Ya tenés el entorno corriendo en otra terminal. Cerralo con `Ctrl+C` o liberá el puerto |
| "Legajo o contraseña incorrectos" con un usuario cargado a mano | Se cargó con la contraseña en texto plano. Editalo en `/admin/` y escribí una nueva |
| "No se pudo verificar el legajo con SySACAD" al registrarse | El mock (puerto 4000) no está corriendo |
| "Hiciste demasiados intentos seguidos" | Esperá un minuto: el límite es de 10 intentos por minuto |
| Error de CORS en la consola del navegador | Abriste el front por otra dirección: usá exactamente `http://localhost:4200` |
| Todo devuelve `401` después de un rato | El token venció (dura 8 horas): iniciá sesión de nuevo |
| La pantalla de Materias está vacía | Faltan cargar las materias (paso 8) |
| Los tests del backend fallan con `Access denied ... test_resutn_db` | Falta el `GRANT` sobre `test_resutn_db` del paso 2 |
| Windows: falla `pip install` con `mysqlclient` | Actualizá pip (`python -m pip install --upgrade pip`) y reintentá: las versiones recientes traen instalador precompilado |
| Windows: PowerShell no deja activar el entorno virtual | Ejecutá una vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |

---

## ⚠️ Consideraciones Importantes
- **Nunca commitear** el `.env`, la carpeta `DSWenv/`, `node_modules/`, `media/` ni `db.sqlite3`: ya están excluidos en `.gitignore`.
- Si instalás un paquete de Python con `pip install`, actualizá el archivo de dependencias antes de subir tu commit: `pip freeze > requirements.txt`. Con los paquetes de `npm`, `package.json` y `package-lock.json` se actualizan solos.
- Si cambiás un modelo de Django, generá la migración (`python manage.py makemigrations core`) y **subila al repo** junto con el cambio; el resto del equipo la aplica con `python manage.py migrate`.
- El `.env.example` sí se sube (es solo una plantilla sin datos reales): si agregás una variable de entorno nueva, agregala también ahí para que el equipo sepa que existe.
- Cada uno usa su propia contraseña local de MariaDB en su `.env`; no hace falta que todos coincidan.
- En **producción**: `DEBUG=False`, una `SECRET_KEY` propia (nunca la de desarrollo) y los archivos de `media/` servidos por el servidor web, no por Django.
