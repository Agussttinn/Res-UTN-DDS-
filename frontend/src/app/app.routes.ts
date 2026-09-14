import { Routes } from '@angular/router';
import { MateriasComponent } from './pages/materias/materias'; 
import { MaterialesComponent } from './pages/materiales/materiales';
import * as ClasesApoyoModule from './pages/clases-apoyo/clases-apoyo';
import * as LoginModule from './pages/login/login';
import { AdminPanelComponent } from './pages/admin-panel/admin-panel'; 



const ClasesApoyoComponent = (ClasesApoyoModule as any).ClasesApoyo ?? (ClasesApoyoModule as any).ClasesApoyoComponent;
const LoginComponent = (LoginModule as any).LoginComponent ?? (LoginModule as any).default ?? (LoginModule as any).Login;

export const routes: Routes = [
  { path: '', redirectTo: 'materias', pathMatch: 'full' },
  { path: 'materias', component: MateriasComponent },
  { path: 'materiales', component: MaterialesComponent },
  { path: 'materiales/:materiaId', component: MaterialesComponent },
  { path: 'clases', component: ClasesApoyoComponent },
  { path: 'login', component: LoginComponent },
  { path: '**', redirectTo: 'materias' },
  { path: 'admin', component: AdminPanelComponent },
];