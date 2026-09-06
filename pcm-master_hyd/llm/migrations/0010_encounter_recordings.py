import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('llm', '0009_clinicalpatient_encounter_encounterrevision')]
    operations = [
        migrations.CreateModel(name='EncounterRecording', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('expires_at', models.DateTimeField(db_index=True)),
            ('consented', models.BooleanField(default=False)),
            ('closed', models.BooleanField(default=False)),
            ('sequence', models.PositiveIntegerField(default=0)),
            ('segments', models.JSONField(default=list)),
            ('encounter', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='recordings', to='llm.encounter')),
        ]),
        migrations.CreateModel(name='RecordingChunk', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('index', models.PositiveIntegerField()),
            ('start_ms', models.PositiveIntegerField()),
            ('duration_ms', models.PositiveIntegerField()),
            ('checksum', models.CharField(max_length=64)),
            ('file_name', models.CharField(max_length=200)),
            ('deleted_at', models.DateTimeField(null=True)),
            ('recording', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='chunks', to='llm.encounterrecording')),
        ]),
        migrations.AddConstraint(model_name='recordingchunk', constraint=models.UniqueConstraint(fields=('recording', 'index'), name='recording_chunk_unique')),
    ]
