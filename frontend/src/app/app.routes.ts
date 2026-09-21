import { Routes } from '@angular/router';
import { MateriasComponent } from './pages/materias/materias';
import { MaterialesComponent } from './pages/materiales/materiales';
import { ClasesApoyoComponent } from './pages/clases-apoyo/clases-apoyo';
import { LoginComponent } from './pages/login/login';
import { RegistroComponent } from './pages/registro/registro';
import { AdminPanelComponent } from './pages/admin-panel/admin-panel';
import { authGuard, rolGuard } from './guards/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'materias', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'registro', component: RegistroComponent },
  // Toda la API requiere estar logueado, así que estas páginas también.
  { path: 'materias', component: MateriasComponent, canActivate: [authGuard] },
  { path: 'materiales', component: MaterialesComponent, canActivate: [authGuard] },
  { path: 'materiales/:materiaId', component: MaterialesComponent, canActivate: [authGuard] },
  { path: 'clases', component: ClasesApoyoComponent, canActivate: [authGuard] },
  { path: 'admin', component: AdminPanelComponent, canActivate: [rolGuard('administrador')] },
  // Tiene que ir ÚLTIMA: atrapa cualquier ruta que no coincida con las anteriores.
  { path: '**', redirectTo: 'materias' },
];
