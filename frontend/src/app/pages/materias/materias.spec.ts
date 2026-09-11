import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Materias } from './materias';

describe('Materias', () => {
  let component: Materias;
  let fixture: ComponentFixture<Materias>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Materias]
    })
      .compileComponents();

    fixture = TestBed.createComponent(Materias);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
