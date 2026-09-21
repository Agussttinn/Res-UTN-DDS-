import { TestBed } from '@angular/core/testing';

import { AppComponent } from './app.component';
import { proveedoresDePrueba, textoDe } from './testing/pruebas';

describe('AppComponent', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ imports: [AppComponent], providers: proveedoresDePrueba() });
  });

  it('arma la página: barra de navegación arriba y el lugar donde se muestran las pantallas', async () => {
    const fixture = TestBed.createComponent(AppComponent);
    await fixture.whenStable();
    const pagina = fixture.nativeElement as HTMLElement;

    expect(pagina.querySelector('app-navbar')).toBeTruthy();
    expect(pagina.querySelector('main router-outlet')).toBeTruthy();
    expect(textoDe(fixture)).toContain('RES-UTN');
  });
});
