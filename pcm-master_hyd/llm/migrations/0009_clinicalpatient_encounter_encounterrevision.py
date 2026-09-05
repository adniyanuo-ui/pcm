import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('llm', '0008_revise_case_revise_revise_case'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(name='ClinicalPatient', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('details', models.JSONField(default=dict)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('owner', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name='Encounter', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('state', models.JSONField(default=dict)),
            ('version', models.PositiveIntegerField(default=1)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('owner', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ('patient', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='llm.clinicalpatient')),
        ]),
        migrations.CreateModel(name='EncounterRevision', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('version', models.PositiveIntegerField()),
            ('action', models.CharField(max_length=40)),
            ('state', models.JSONField()),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('encounter', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='revisions', to='llm.encounter')),
        ], options={'constraints': [models.UniqueConstraint(fields=('encounter', 'version'), name='encounter_revision_unique')]}),
    ]
