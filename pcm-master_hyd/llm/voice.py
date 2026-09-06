"""Authenticated, bounded PCM storage and traceable voice summarisation.

There is deliberately no public MEDIA_URL and no token embedded in audio URLs.
"""
import base64
import hashlib
import io
from datetime import timedelta
from pathlib import Path
import wave

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from tools.resp import get_response
from llm.models import EncounterRecording, RecordingChunk

CHUNK_MS = 10000
MAX_RECORDING_MS = 2 * 60 * 60 * 1000


def require(condition, message):
    if not condition:
        raise serializers.ValidationError(message)


def audio_root():
    return Path(settings.PCM_AUDIO_ROOT)


def audio_path(name):
    root = audio_root().resolve()
    path = (root / name).resolve()
    require(path.is_relative_to(root) and path != root, '录音路径无效')
    return path


def purge_expired_recordings(now=None):
    """Only unlink individually identified audio files; never delete clinical history."""
    now = now or timezone.now()
    count = 0
    for chunk in RecordingChunk.objects.filter(recording__expires_at__lte=now, deleted_at=None).iterator():
        audio_path(chunk.file_name).unlink(missing_ok=True)
        RecordingChunk.objects.filter(pk=chunk.pk, deleted_at=None).update(deleted_at=now)
        count += 1
    # A worker crash between file creation and the chunk row insert must not leave audio forever.
    for recording in EncounterRecording.objects.filter(expires_at__lte=now).only('id').iterator():
        directory = audio_path(str(recording.pk))
        if not directory.is_dir():
            continue
        for candidate in directory.glob('*.wav'):
            if candidate.stem.isdigit() and candidate.is_file():
                audio_path(f'{recording.pk}/{candidate.name}').unlink(missing_ok=True)
                count += 1
    return count


def recording_output(recording):
    expired = recording.expires_at <= timezone.now()
    return dict(id=str(recording.pk), sequence=recording.sequence, created_at=recording.created_at.isoformat(),
                expires_at=recording.expires_at.isoformat(), expired=expired, closed=recording.closed,
                segments=recording.segments, chunks=[dict(id=c.pk, index=c.index, start_ms=c.start_ms,
                duration_ms=c.duration_ms, available=not expired and c.deleted_at is None)
                for c in recording.chunks.order_by('index')])


def source_segments(encounter, closed_only=False):
    recordings = list(encounter.recordings.order_by('created_at'))
    if closed_only:
        require(all(r.closed for r in recordings), '请先结束录音并完成音频上传，再整理全文')
    segments = []
    for recording in recordings:
        for segment in recording.segments:
            segments.append(dict(segment, id=f'{recording.pk}:{segment["index"]}', recording_id=str(recording.pk)))
    require(sum(len(s['text']) for s in segments) <= 50000, '本次录音文字过长，请另建就诊记录')
    return segments


class SymptomInput(serializers.Serializer):
    label = serializers.CharField(max_length=160)
    source_ids = serializers.ListField(child=serializers.CharField(max_length=100), allow_empty=False, max_length=20)


class VoiceSummaryInput(serializers.Serializer):
    summary = serializers.CharField(max_length=16000, allow_blank=True)
    symptoms = SymptomInput(many=True, allow_empty=True)
    uncertainty = serializers.CharField(max_length=4000, allow_blank=True)


def validate_sources(summary, segments):
    allowed = {s['id'] for s in segments}
    require(len(summary['symptoms']) <= 80, '症状摘要过长，请重试')
    for symptom in summary['symptoms']:
        require(all(source in allowed for source in symptom['source_ids']), '语音依据定位未通过校验，请重新整理')
    return summary


class VoiceMixin:
    def owned_recording(self, request, pk, recording_id):
        encounter = self.get_encounter(request, pk)
        try:
            return get_object_or_404(EncounterRecording, pk=recording_id, encounter=encounter)
        except (ValueError, TypeError, DjangoValidationError):
            raise serializers.ValidationError('录音编号无效')

    @action(detail=True, methods=['get', 'post'])
    def recordings(self, request, pk=None):
        encounter = self.get_encounter(request, pk)
        if request.method == 'GET':
            return get_response([recording_output(r) for r in encounter.recordings.order_by('created_at')])
        require(request.data.get('consent') is True, '请先确认已告知患者并取得录音同意')
        require(encounter.recordings.count() < 100, '本次就诊录音段数已达上限')
        recording = EncounterRecording.objects.create(encounter=encounter, consented=True,
                                                      expires_at=timezone.now() + timedelta(days=30))
        return get_response(recording_output(recording))

    @action(detail=True, methods=['post'])
    def audio_chunk(self, request, pk=None):
        r = self.owned_recording(request, pk, request.data.get('recording_id'))
        require(r.expires_at > timezone.now(), '录音已到期，不能再上传')
        index = request.data.get('index')
        require(type(index) is int and 0 <= index < MAX_RECORDING_MS // CHUNK_MS, '录音片段序号无效')
        encoded = request.data.get('audio')
        require(isinstance(encoded, str) and len(encoded) <= 430000, '录音片段过大')
        try:
            raw = base64.b64decode(encoded, validate=True)
            with wave.open(io.BytesIO(raw), 'rb') as wav:
                require(wav.getnchannels() == 1 and wav.getframerate() == 16000 and wav.getsampwidth() == 2
                        and wav.getcomptype() == 'NONE', '仅接受16kHz单声道PCM录音')
                frames = wav.getnframes()
                require(0 < frames <= 160000, '录音片段超过10秒或为空')
                pcm = wav.readframes(frames)
                require(0 < frames <= 160000 and len(pcm) == frames * 2, '录音片段不完整或超过10秒')
        except (ValueError, EOFError, wave.Error):
            raise serializers.ValidationError('录音文件格式无效')
        checksum = hashlib.sha256(raw).hexdigest()
        existing = r.chunks.filter(index=index).first()
        if existing:
            require(existing.checksum == checksum, '同一录音片段不能被不同内容覆盖')
            return get_response({'saved': True})
        require(not r.closed, '录音已结束，不能追加音频')
        require(index == r.chunks.count(), '录音片段顺序不连续，请重试上传')
        previous = r.chunks.order_by('-index').first()
        require(previous is None or previous.duration_ms == CHUNK_MS, '不能在不完整片段后追加音频')
        name = f'{r.pk}/{index}.wav'
        path = audio_path(name)
        audio_root().mkdir(parents=True, exist_ok=True, mode=0o700)
        audio_root().chmod(0o700)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Exclusive create plus checksum makes a retried upload idempotent even after a DB failure.
        try:
            with path.open('xb') as handle:
                handle.write(raw)
            path.chmod(0o600)
        except FileExistsError:
            require(hashlib.sha256(path.read_bytes()).hexdigest() == checksum, '录音文件冲突，请联系管理员')
        RecordingChunk.objects.get_or_create(recording=r, index=index, defaults=dict(
            start_ms=index * CHUNK_MS, duration_ms=round(frames / 16), checksum=checksum, file_name=name))
        return get_response({'saved': True})

    @action(detail=True, methods=['post'])
    def voice_snapshot(self, request, pk=None):
        r = self.owned_recording(request, pk, request.data.get('recording_id'))
        require(r.expires_at > timezone.now(), '录音已到期')
        segments, sequence = request.data.get('segments'), request.data.get('sequence')
        require(isinstance(segments, list) and len(segments) <= 1000, '录音文字格式无效')
        require(type(sequence) is int and sequence > 0, '录音版本无效')
        cleaned, seen = [], set()
        for s in segments:
            require(isinstance(s, dict), '语音片段格式无效')
            index, start, end, text = (s.get(k) for k in ('index', 'start_ms', 'end_ms', 'text'))
            require(type(index) is int and index > 0 and index not in seen, '语音句子序号无效')
            require(type(start) is int and type(end) is int and 0 <= start < end <= MAX_RECORDING_MS, '语音时间范围无效')
            require(isinstance(text, str) and 0 < len(text) <= 4000, '语音句子为空或过长')
            seen.add(index)
            cleaned.append(dict(index=index, start_ms=start, end_ms=end, text=text))
        require(sum(len(s['text']) for s in cleaned) <= 50000, '语音文本过长')
        close = request.data.get('closed') is True
        if close:
            tail = r.chunks.order_by('-index').first()
            duration = tail.start_ms + tail.duration_ms if tail else 0
            require(not cleaned or duration > 0, '音频尚未上传完成，请重试')
            for segment in cleaned:
                require(segment['start_ms'] < duration, '语音时间与录音不匹配，请重试')
                segment['end_ms'] = min(segment['end_ms'], duration)
        if r.closed:
            require(close and r.segments == sorted(cleaned, key=lambda s: s['index']), '录音已结束，不能覆盖原始识别依据')
            return get_response({'saved': True})
        updated = EncounterRecording.objects.filter(pk=r.pk, closed=False, sequence__lt=sequence).update(
            segments=sorted(cleaned, key=lambda s: s['index']), sequence=sequence, closed=close)
        require(bool(updated), '录音快照已更新，请勿覆盖较新的内容')
        return get_response({'saved': True})

    @action(detail=True, methods=['post'])
    def recover_recording(self, request, pk=None):
        r = self.owned_recording(request, pk, request.data.get('recording_id'))
        # Explicit recovery never invents missing audio or discards already saved text.
        EncounterRecording.objects.filter(pk=r.pk).update(closed=True)
        return get_response({'saved': True, 'warning': '仅保留服务器已收到的录音；中断前未上传的片段无法恢复。'})

    @action(detail=True, methods=['post'])
    def voice_preview(self, request, pk=None):
        encounter = self.get_encounter(request, pk)
        segments = source_segments(encounter)
        if not segments:
            return get_response(dict(summary='', symptoms=[], uncertainty=''))
        # No generation result is written into the encounter while a doctor is recording/editing.
        from llm.encounters import EncounterView
        state = {'models': []}
        lock = f'voice-preview:{encounter.pk}'
        require(cache.add(lock, True, timeout=110), '正在提取症状，请等待本次处理完成')
        try:
            summary = EncounterView.generate(state, 'voice_preview', {'segments': segments}, {'model': 'deepseek-v4-flash'})
            return get_response(validate_sources(summary, segments))
        finally:
            cache.delete(lock)

    @action(detail=True, methods=['get'], url_path=r'audio/(?P<chunk_id>[0-9]+)')
    def audio(self, request, pk=None, chunk_id=None):
        encounter = self.get_encounter(request, pk)
        chunk = get_object_or_404(RecordingChunk, pk=chunk_id, recording__encounter=encounter)
        if chunk.deleted_at or chunk.recording.expires_at <= timezone.now():
            return get_response(code=410, msg='录音已超过30天保留期，无法回放；文字记录仍保留。', status_code=410)
        path = audio_path(chunk.file_name)
        if not path.is_file():
            return get_response(code=410, msg='录音文件不可用，文字记录仍保留。', status_code=410)
        try:
            handle = path.open('rb')
        except FileNotFoundError:
            return get_response(code=410, msg='录音已清理，文字记录仍保留。', status_code=410)
        response = FileResponse(handle, content_type='audio/wav')
        response['Cache-Control'] = 'no-store, private'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
