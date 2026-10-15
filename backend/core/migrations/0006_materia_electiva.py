from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_material_archivo'),
    ]

    operations = [
        migrations.AddField(
            model_name='materia',
            name='electiva',
            field=models.BooleanField(default=False),
        ),
    ]
