import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ClasesApoyo } from './clases-apoyo';

describe('ClasesApoyo', () => {
  let component: ClasesApoyo;
  let fixture: ComponentFixture<ClasesApoyo>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ClasesApoyo]
    })
      .compileComponents();

    fixture = TestBed.createComponent(ClasesApoyo);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
