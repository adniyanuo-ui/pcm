import base64
import io
import json
import tempfile
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import wave

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from llm.encounters import generate_json
from llm.models import Encounter, EncounterRecording, RecordingChunk
from llm.voice import purge_expired_recordings


def wav_bytes(frames=32000, channels=1):
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(channels); wav.setsampwidth(2); wav.setframerate(16000)
        wav.writeframes(b'\0\0' * frames * channels)
    return buffer.getvalue()


class VoiceTests(TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix='pcm-audio-test-')
        self.addCleanup(self.folder.cleanup)
        self.setting = self.settings(PCM_AUDIO_ROOT=Path(self.folder.name))
        self.setting.enable(); self.addCleanup(self.setting.disable)
        self.owner = User.objects.create_user('voice-doctor')
        self.other = User.objects.create_user('other-voice-doctor')
        self.client = APIClient(); self.client.force_authenticate(self.owner)
        self.visit = self.client.post('/api/cms/llm/encounters/', {'patient': dict(name='虚构语音患者', sex='男', age=30, allergy='待确认')}, format='json').data['data']
        self.url = f'/api/cms/llm/encounters/{self.visit["id"]}/'
        self.recording = self.post('recordings', {'consent': True}).data['data']

    def post(self, action, data, status=200):
        response = self.client.post(self.url + action + '/', data, format='json')
        self.assertEqual(response.status_code, status, response.data)
        return response

    def upload(self, index=0, raw=None, status=200):
        return self.post('audio_chunk', {'recording_id': self.recording['id'], 'index': index,
            'audio': base64.b64encode(raw if raw is not None else wav_bytes()).decode()}, status)

    def save_segments(self, closed=False, sequence=1, status=200):
        return self.post('voice_snapshot', {'recording_id': self.recording['id'], 'sequence': sequence,
            'segments': [dict(index=1, start_ms=0, end_ms=1500, text='虚构患者：没有发热，食少两周。')], 'closed': closed}, status)

    def summary(self, source=None):
        return dict(summary='虚构患者食少两周，否认发热。', symptoms=[dict(label='否认发热', source_ids=[source or self.recording['id'] + ':1'])], uncertainty='')

    def test_consent_required_and_expiry_fixed(self):
        self.post('recordings', {}, 400)
        r = EncounterRecording.objects.get(pk=self.recording['id'])
        self.assertTrue(r.consented)
        self.assertLess(abs((r.expires_at - r.created_at).total_seconds() - 30 * 86400), 2)

    def test_audio_order_size_format_and_idempotency(self):
        self.upload(index=1, status=400)
        self.upload(raw=b'not audio', status=400)
        self.upload(raw=wav_bytes(channels=2), status=400)
        self.upload(raw=wav_bytes(frames=160001), status=400)
        self.upload(); self.upload()
        self.assertEqual(RecordingChunk.objects.count(), 1)
        self.upload(raw=wav_bytes(frames=16000), status=400)
        self.upload(index=1, status=400)
        self.assertEqual(RecordingChunk.objects.count(), 1)

    def test_owner_isolation_all_voice_routes(self):
        self.upload(); chunk = RecordingChunk.objects.get()
        self.client.force_authenticate(self.other)
        for endpoint in ('recordings/', f'audio/{chunk.pk}/'):
            self.assertEqual(self.client.get(self.url + endpoint).status_code, 404)
        self.post('recordings', {'consent': True}, 404)
        self.upload(status=404); self.save_segments(status=404)
        self.post('voice_preview', {}, 404)
        self.post('recover_recording', {'recording_id': self.recording['id']}, 404)

    def test_audio_requires_auth_and_does_not_use_public_media(self):
        self.upload(); chunk = RecordingChunk.objects.get()
        response = self.client.get(self.url + f'audio/{chunk.pk}/')
        self.assertEqual(b''.join(response.streaming_content), wav_bytes())
        self.assertEqual(response['Cache-Control'], 'no-store, private')
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(self.url + f'audio/{chunk.pk}/').status_code, (401, 403))

    def test_expired_audio_denied_and_purged_without_clinical_loss(self):
        self.upload(); self.save_segments(closed=True)
        chunk = RecordingChunk.objects.get()
        path = Path(self.folder.name) / chunk.file_name
        EncounterRecording.objects.filter(pk=self.recording['id']).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.client.get(self.url + f'audio/{chunk.pk}/').status_code, 410)
        self.assertEqual(purge_expired_recordings(), 1)
        self.assertFalse(path.exists()); self.assertEqual(purge_expired_recordings(), 0)
        self.assertEqual(Encounter.objects.count(), 1)
        self.assertTrue(EncounterRecording.objects.get().segments)
        self.upload(status=400)

    def test_snapshot_version_close_retry_and_no_overwrite(self):
        self.upload(); self.save_segments(sequence=2)
        self.save_segments(sequence=1, status=400)
        self.save_segments(sequence=3, closed=True)
        self.save_segments(sequence=3, closed=True)
        self.save_segments(sequence=4, status=400)
        self.assertEqual(EncounterRecording.objects.get().sequence, 3)

    def test_snapshot_requires_uploaded_audio_on_close(self):
        self.save_segments(closed=True, status=400)
        self.post('audio_chunk', {'recording_id': 'invalid'}, 400)

    def test_preview_is_grounded_and_does_not_mutate_encounter(self):
        self.upload(); self.save_segments()
        with patch('llm.encounters.generate_json', return_value=(self.summary(), 'fixture-flash')) as generate:
            response = self.post('voice_preview', {})
            self.assertEqual(response.data['data']['symptoms'][0]['label'], '否认发热')
            self.assertEqual(generate.call_args.args[2], 'deepseek-v4-flash')
        self.assertEqual(Encounter.objects.get().version, 1)
        with patch('llm.encounters.generate_json', return_value=(self.summary('invented:1'), 'fixture')):
            self.post('voice_preview', {}, 400)

    def test_finalize_pro_restores_summary_and_keeps_audio_trace(self):
        self.upload(); self.save_segments(closed=True)
        with patch('llm.encounters.generate_json', return_value=(self.summary(), 'fixture-pro')) as generate:
            response = self.post('transition', {'version': 1, 'action': 'finalize_voice'})
            self.assertEqual(generate.call_args.args[2], 'deepseek-v4-pro')
        state = response.data['data']['state']
        self.assertEqual(state['transcript'], self.summary()['summary'])
        self.assertIn('没有发热', state['original_transcript'])
        self.assertFalse(any(state['confirmed']))
        self.assertEqual(self.client.get(self.url).data['data']['state']['voice_summary'], self.summary())
        self.assertEqual(Encounter.objects.get().revisions.count(), 2)

    def test_finalize_failure_keeps_audio_and_previous_draft(self):
        self.upload(); self.save_segments(closed=True)
        with patch('llm.encounters.generate_json', side_effect=RuntimeError('private data')):
            response = self.post('transition', {'version': 1, 'action': 'finalize_voice'}, 500)
        self.assertNotIn('private data', str(response.data))
        self.assertEqual(Encounter.objects.get().version, 1)
        self.assertEqual(RecordingChunk.objects.count(), 1)

    def test_finalize_requires_closed_recordings(self):
        self.save_segments()
        self.post('transition', {'version': 1, 'action': 'finalize_voice'}, 400)

    def test_orphan_upload_is_also_removed_at_expiry(self):
        directory = Path(self.folder.name) / self.recording['id']
        directory.mkdir()
        orphan = directory / '0.wav'
        orphan.write_bytes(wav_bytes())
        self.assertEqual(purge_expired_recordings(), 0)
        EncounterRecording.objects.filter(pk=self.recording['id']).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(purge_expired_recordings(), 1)
        self.assertFalse(orphan.exists())

    def test_expired_interrupted_recording_can_be_closed_without_extending_retention(self):
        expiry = timezone.now() - timedelta(seconds=1)
        EncounterRecording.objects.filter(pk=self.recording['id']).update(expires_at=expiry)
        self.post('recover_recording', {'recording_id': self.recording['id']})
        recording = EncounterRecording.objects.get()
        self.assertTrue(recording.closed)
        self.assertEqual(recording.expires_at, expiry)

    def test_final_generation_cannot_overwrite_concurrent_doctor_edit(self):
        self.upload(); self.save_segments(closed=True)
        def compete(*args):
            Encounter.objects.filter(pk=self.visit['id']).update(version=2)
            return self.summary(), 'fixture-pro'
        with patch('llm.encounters.generate_json', side_effect=compete):
            self.post('transition', {'version': 1, 'action': 'finalize_voice'}, 409)
        self.assertEqual(Encounter.objects.get().state['transcript'], '')

    def test_voice_prompt_preserves_negations_and_never_returns_reasoning(self):
        with patch('llm.encounters.model_name2client') as clients:
            completion = SimpleNamespace(model='fixture-pro', choices=[SimpleNamespace(message=SimpleNamespace(
                content=json.dumps(self.summary()), reasoning_content='private reasoning'))])
            client = clients.__getitem__.return_value
            client.with_options.return_value.chat.completions.create.return_value = completion
            result, actual = generate_json('voice_final', {'segments': []}, 'deepseek-v4-pro')
            self.assertEqual(result, self.summary()); self.assertEqual(actual, 'fixture-pro')
            prompt = client.with_options.return_value.chat.completions.create.call_args.kwargs['messages'][0]['content']
            self.assertIn('保留否定', prompt); self.assertIn('禁止猜测', prompt)
            self.assertNotIn('private reasoning', str(result))
            client.with_options.assert_called_once_with(timeout=45, max_retries=0)
            self.assertEqual(client.with_options.return_value.chat.completions.create.call_args.kwargs['extra_body'],
                             {'thinking': {'type': 'disabled'}})

    def test_final_summary_preserves_doctor_supplements(self):
        self.upload(); self.save_segments(closed=True)
        state = Encounter.objects.get().state
        state['examinations'] = dict(inquiry='旧稿', inspection='医师望诊补充', palpation='医师切诊补充', listening='')
        Encounter.objects.update(state=state)
        with patch('llm.encounters.generate_json', return_value=(self.summary(), 'fixture-pro')):
            response = self.post('transition', {'version': 1, 'action': 'finalize_voice'})
        e = response.data['data']['state']['examinations']
        self.assertEqual(e['inspection'], '医师望诊补充')
        self.assertEqual(e['palpation'], '医师切诊补充')
        self.assertEqual(e['inquiry'], self.summary()['summary'])

    def test_repeated_finish_reuses_source_and_never_overwrites_doctor_correction(self):
        self.upload(); self.save_segments(closed=True)
        with patch('llm.encounters.generate_json', return_value=(self.summary(), 'fixture-pro')) as generate:
            self.post('transition', {'version': 1, 'action': 'finalize_voice'})
            self.post('transition', {'version': 2, 'action': 'save_intake', 'data': dict(
                patient=self.visit['state']['patient'], text='医师校对后的最终问诊结果', inspection='望诊补充', palpation='', listening='')})
            result = self.post('transition', {'version': 3, 'action': 'finalize_voice'}).data['data']['state']
            self.assertEqual(generate.call_count, 1)
        self.assertEqual(result['transcript'], '医师校对后的最终问诊结果')
        self.assertEqual(result['examinations']['inspection'], '望诊补充')
