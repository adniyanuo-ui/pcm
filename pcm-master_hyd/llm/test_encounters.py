from unittest.mock import patch
import json
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from llm.models import Encounter, EncounterRevision
from llm.encounters import generate_json


EXAMINATIONS = dict(inspection='舌淡', listening='', inquiry='虚构病例：食少便溏两周', palpation='脉弱')
ANALYSIS = dict(cause='饮食失节', location='脾胃', nature='虚', trend='待确认', syndrome='脾胃气虚',
                mechanism='运化失健', principle='健运中焦', treatment='益气健脾', evidence='食少便溏、舌淡、脉弱', questions='有无畏寒')
CANDIDATE = dict(id='10001', name='测试方', fields={'组成': '药甲 药乙', '主治': '测试原文'},
                 source={'volume': 1, 'pdf_pages': [10], 'book_pages': [2]})
PRESCRIPTION = dict(items=[dict(herb='虚构药甲', dose='1g', note='仅用于软件测试')], count=1,
                    usage='测试用法', advice='测试医嘱')
BASE = '/api/cms/llm/encounters/'


class EncounterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('test-doctor')
        self.other = User.objects.create_user('other-doctor')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        response = self.client.post(BASE, {'patient': dict(name='虚构患者', sex='女', age=30, allergy='待确认')}, format='json')
        self.assertEqual(response.status_code, 200)
        self.visit = response.data['data']
        self.url = BASE + str(self.visit['id']) + '/'

    def transition(self, action, data=None, status=200):
        response = self.client.post(self.url + 'transition/', dict(version=self.visit['version'], action=action, data=data or {}), format='json')
        self.assertEqual(response.status_code, status, response.data)
        if status == 200:
            self.visit = response.data['data']
        return response

    def to_analysis(self):
        self.transition('save_transcript', {'text': '虚构患者：食少便溏两周'})
        with patch('llm.encounters.generate_json', return_value=(EXAMINATIONS, 'test-model')):
            self.transition('organize')
        self.transition('save_examinations', EXAMINATIONS)
        self.transition('confirm_examinations')
        with patch('llm.encounters.generate_json', return_value=(ANALYSIS, 'test-model')):
            self.transition('analyze')
        self.transition('confirm_analysis')

    def complete(self):
        self.to_analysis()
        with patch('llm.encounters.FormulaRetriever') as retriever:
            retriever.return_value.search.return_value = {'candidates': [CANDIDATE]}
            self.transition('retrieve')
        self.transition('select_formula', {'id': '10001'})
        self.transition('save_prescription', PRESCRIPTION)
        self.transition('confirm_prescription')
        self.transition('generate_record')
        self.transition('save_record', {'text': self.visit['state']['record'] + '\n医师已复核'})
        self.transition('confirm_record', {'reviewed': True})

    def test_full_flow_restore_history_and_followup(self):
        self.complete()
        restored = self.client.get(self.url).data['data']
        self.assertEqual(restored, self.visit)
        self.assertTrue(all(restored['state']['confirmed']))
        self.assertIn('待填 / 未提供', restored['state']['record'])
        self.assertNotIn('检查结果正常', restored['state']['record'])
        self.assertEqual(restored['state']['models'][0]['actual'], 'test-model')
        revisions = self.client.get(self.url + 'history/').data['data']
        self.assertEqual(len(revisions), restored['version'])
        self.assertNotEqual(revisions[0]['state']['record'], revisions[2]['state']['record'])
        followup = self.client.post(BASE, {'patient_id': self.visit['patient_id']}, format='json').data['data']
        self.assertEqual(followup['patient_id'], self.visit['patient_id'])
        self.assertEqual(followup['state']['transcript'], '')
        self.assertIsNone(followup['state']['analysis'])

    def test_owner_isolation_all_routes(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(BASE).data['data'], [])
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.get(self.url + 'history/').status_code, 404)
        self.assertEqual(self.client.post(self.url + 'formula_reference/', {'id': '10001'}, format='json').status_code, 404)
        self.transition('save_transcript', {'text': 'illegal'}, status=404)
        self.assertEqual(self.client.post(BASE, {'patient_id': self.visit['patient_id']}, format='json').status_code, 404)

    def test_authentication_required(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(BASE).status_code, (401, 403))

    def test_inactive_doctor_cannot_access(self):
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.client.get(BASE).status_code, 403)

    def test_no_skip_and_invalid_input(self):
        for action in ('analyze', 'retrieve', 'confirm_examinations', 'confirm_analysis', 'confirm_prescription', 'generate_record', 'confirm_record'):
            self.transition(action, status=400)
        self.transition('save_transcript', {'text': []}, status=400)
        self.assertEqual(EncounterRevision.objects.count(), 1)

    def test_stale_version_cannot_overwrite(self):
        old_version = self.visit['version']
        self.transition('save_transcript', {'text': 'new text'})
        response = self.client.post(self.url + 'transition/', dict(version=old_version, action='save_transcript', data={'text': 'stale'}), format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Encounter.objects.get(pk=self.visit['id']).state['transcript'], 'new text')

    def test_upstream_edits_clear_all_downstream_but_keep_history(self):
        self.complete()
        self.transition('save_examinations', dict(EXAMINATIONS, inquiry='虚构修改：新增口渴'))
        s = self.visit['state']
        self.assertEqual(s['confirmed'], [True, False, False, False, False])
        self.assertIsNone(s['analysis'])
        self.assertEqual(s['candidates'], [])
        self.assertIsNone(s['prescription'])
        self.assertEqual(s['record'], '')
        self.assertTrue(EncounterRevision.objects.filter(state__confirmed__4=True).exists())

    def test_analysis_and_prescription_invalidation(self):
        self.complete()
        self.transition('save_prescription', dict(PRESCRIPTION, count=2))
        self.assertEqual(self.visit['state']['confirmed'], [True, True, True, False, False])
        self.assertEqual(self.visit['state']['record'], '')
        self.transition('save_analysis', dict(ANALYSIS, treatment='修改治法'))
        self.assertEqual(self.visit['state']['candidates'], [])
        self.assertIsNone(self.visit['state']['prescription'])

    def test_failed_generation_preserves_saved_state(self):
        self.transition('save_transcript', {'text': 'test'})
        version = self.visit['version']
        with patch('llm.encounters.generate_json', side_effect=RuntimeError('private provider text')):
            response = self.transition('organize', status=500)
        self.assertNotIn('private provider text', str(response.data))
        self.assertEqual(Encounter.objects.get(pk=self.visit['id']).version, version)

    def test_generation_does_not_overwrite_concurrent_edit(self):
        self.transition('save_transcript', {'text': 'before'})
        def concurrent_edit(*args):
            Encounter.objects.filter(pk=self.visit['id']).update(version=self.visit['version'] + 1)
            return EXAMINATIONS, 'test-model'
        with patch('llm.encounters.generate_json', side_effect=concurrent_edit):
            self.transition('organize', status=409)

    def test_retrieval_uses_confirmed_values_and_rejects_invented_formula(self):
        self.to_analysis()
        with patch('llm.encounters.FormulaRetriever') as retriever:
            retriever.return_value.search.return_value = {'candidates': [CANDIDATE]}
            self.transition('retrieve')
        self.assertEqual(self.visit['state']['query']['syndromes'], [ANALYSIS['syndrome']])
        self.assertEqual(self.visit['state']['query']['treatments'], [ANALYSIS['principle'] + '\n' + ANALYSIS['treatment']])
        self.transition('select_formula', {'id': 'invented'}, status=400)

    def test_confirmation_requires_explicit_review(self):
        self.complete()
        self.transition('save_record', {'text': '医生修改病历'})
        self.assertFalse(self.visit['state']['confirmed'][4])
        self.transition('confirm_record', status=400)

    def test_usage_error_uses_chinese_field_label(self):
        self.complete()
        response = self.transition('save_prescription', dict(PRESCRIPTION, usage=''), status=400)
        self.assertIn('煎服方法', response.data['msg'])
        self.assertNotIn('usage', response.data['msg'])

    def test_questions_are_optional_and_prescription_notes_saved(self):
        self.complete()
        self.transition('save_prescription', dict(PRESCRIPTION, adjustment_note='虚构测试：医师调整说明'))
        self.transition('confirm_prescription'); self.transition('generate_record')
        self.assertIn('医师调整说明', self.visit['state']['record'])
        self.transition('save_analysis', {k: v for k, v in ANALYSIS.items() if k != 'questions'})
        self.assertEqual(self.visit['state']['analysis']['questions'], '')

    def test_original_transcript_and_patient_corrections(self):
        self.transition('save_transcript', {'text': '校对文本', 'original': '识别原文'})
        self.transition('save_transcript', {'text': '再次校对'})
        self.assertEqual(self.visit['state']['original_transcript'], '识别原文')
        self.complete()
        patient = dict(self.visit['state']['patient'], allergy='虚构过敏史')
        self.transition('save_patient', patient)
        self.assertEqual(self.visit['state']['confirmed'], [False] * 5)
        self.assertIsNone(self.visit['state']['examinations'])
        self.assertEqual(self.visit['state']['record'], '')

    def test_long_confirmed_text_is_split_without_truncation(self):
        self.to_analysis()
        inquiry = '虚构症状。' * 300
        self.transition('save_examinations', dict(EXAMINATIONS, inquiry=inquiry))
        self.transition('confirm_examinations')
        with patch('llm.encounters.generate_json', return_value=(ANALYSIS, 'test-model')):
            self.transition('analyze')
        self.transition('confirm_analysis')
        with patch('llm.encounters.FormulaRetriever') as retriever:
            retriever.return_value.search.return_value = {'candidates': [CANDIDATE]}
            self.transition('retrieve')
        self.assertEqual(''.join(self.visit['state']['query']['symptoms']), inquiry)

    def test_explicit_provider_keeps_actual_model_and_excludes_reasoning(self):
        with patch('llm.encounters.model_name2client') as clients:
            completion = SimpleNamespace(model='qwen3.7-plus-test-snapshot', choices=[SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(EXAMINATIONS), reasoning_content='never expose this'))])
            client = clients.__getitem__.return_value
            client.with_options.return_value.chat.completions.create.return_value = completion
            result, actual = generate_json('examinations', {'transcript': '虚构'}, 'qwen3.7-plus')
            self.assertEqual(result, EXAMINATIONS)
            self.assertEqual(actual, 'qwen3.7-plus-test-snapshot')
            self.assertNotIn('never expose', str(result))
            self.assertEqual(client.with_options.return_value.chat.completions.create.call_args.kwargs['model'], 'qwen3.7-plus')

    def intake(self, **changes):
        return dict(patient=self.visit['state']['patient'], text='虚构患者：没有发热，食少两周。',
                    inspection='医师望诊', palpation='医师切诊', listening='', **changes)

    def test_combined_intake_confirms_verbatim_without_another_model_call(self):
        data = self.intake(reviewed=True)
        with patch('llm.encounters.generate_json') as generate:
            self.transition('confirm_intake', data)
            generate.assert_not_called()
        state = self.visit['state']
        self.assertEqual(state['confirmed'], [True, True, False, False, False])
        self.assertEqual(state['transcript'], data['text'])
        self.assertEqual(state['examinations']['inquiry'], data['text'])
        self.assertEqual(state['examinations']['inspection'], data['inspection'])
        self.assertEqual(state['examinations']['palpation'], data['palpation'])
        self.assertEqual(state['examinations']['listening'], '')

    def test_combined_intake_requires_review_and_saves_incomplete_draft(self):
        self.transition('confirm_intake', self.intake(), status=400)
        self.transition('save_intake', dict(self.intake(), text=''))
        self.assertFalse(any(self.visit['state']['confirmed']))
        self.transition('confirm_intake', dict(self.intake(reviewed=True), text=''), status=400)

    def test_combined_intake_edits_invalidate_downstream_and_keep_audio_evidence(self):
        self.complete()
        original = self.visit['state']['original_transcript']
        self.transition('save_intake', self.intake())
        state = self.visit['state']
        self.assertEqual(state['confirmed'], [False] * 5)
        self.assertIsNone(state['analysis']); self.assertIsNone(state['prescription'])
        self.assertEqual(state['candidates'], []); self.assertEqual(state['record'], '')
        self.assertEqual(state['original_transcript'], original)
        self.assertTrue(EncounterRevision.objects.filter(state__confirmed__4=True).exists())

    def test_combined_intake_patient_update_is_atomic_and_owned(self):
        data = self.intake()
        data['patient'] = dict(data['patient'], allergy='虚构过敏史')
        self.transition('save_intake', data)
        self.assertEqual(Encounter.objects.get().patient.details['allergy'], '虚构过敏史')
        self.client.force_authenticate(self.other)
        self.transition('confirm_intake', dict(data, reviewed=True), status=404)

    def test_free_text_prescription_prefills_only_rag_facts_and_requires_review(self):
        self.to_analysis()
        with patch('llm.encounters.FormulaRetriever') as retriever:
            retriever.return_value.search.return_value = {'candidates': [CANDIDATE]}
            self.transition('retrieve')
        self.transition('select_formula', {'id': CANDIDATE['id']})
        self.assertEqual(self.visit['state']['prescription'], {'text': CANDIDATE['fields']['组成']})
        self.assertFalse(self.visit['state']['confirmed'][3])
        self.transition('confirm_prescription', status=400)
        self.transition('save_prescription', {'text': ''}, status=400)
        text = '虚构药甲 1g\n医师手写加减与用法（仅软件验证）'
        self.transition('save_prescription', {'text': text})
        self.transition('confirm_prescription', {'reviewed': True})
        self.transition('generate_record')
        self.assertIn(text, self.visit['state']['record'])
        self.assertNotIn('剂数：', self.visit['state']['record'])
        self.transition('save_prescription', {'text': text + ' 修改'})
        self.assertFalse(self.visit['state']['confirmed'][3]); self.assertEqual(self.visit['state']['record'], '')

    def test_missing_composition_does_not_invent_prescription_or_dose(self):
        from llm.encounters import formula_draft
        self.assertEqual(formula_draft(dict(CANDIDATE, fields={'用法': '辞典用法'})), '')
        self.assertEqual(formula_draft(dict(CANDIDATE, fields={'组成': '药甲一两', '用法': '原文用法'})), '药甲一两\n\n原文用法')

    def test_multiple_formulas_append_without_overwriting_doctor_edits(self):
        candidates = [
            dict(CANDIDATE, id='10001', name='测试方一', fields={'组成': '生地1g当归2g', '用法': '测试用法一'}),
            dict(CANDIDATE, id='10002', name='测试方二', fields={'组成': '白芍2g丹皮1g', '用法': '测试用法二'},
                 source={'volume': 2, 'pdf_pages': [20], 'book_pages': [12]}),
            dict(CANDIDATE, id='10003', name='测试方三', fields={'组成': '黄芩1g连翘2g', '用法': '测试用法三'},
                 source={'volume': 3, 'pdf_pages': [30], 'book_pages': [22]}),
        ]
        self.to_analysis()
        with patch('llm.encounters.FormulaRetriever') as retriever:
            retriever.return_value.search.return_value = {'candidates': candidates}
            self.transition('retrieve')
        self.transition('select_formulas', {'ids': ['10001', '10002'], 'conversions': {}})
        state = self.visit['state']
        self.assertEqual(state['selected_ids'], ['10001', '10002'])
        self.assertEqual(state['prescription']['text'].count('【测试方一 · 原方参考】'), 1)
        self.assertIn('生地1g、当归2g', state['prescription']['text'])
        edited = state['prescription']['text'] + '\n\n医师自定义修改，不得覆盖。'
        self.transition('save_prescription', {'text': edited})
        self.transition('select_formulas', {'ids': ['10003'], 'conversions': {}})
        self.assertIn('医师自定义修改，不得覆盖。', self.visit['state']['prescription']['text'])
        self.assertEqual(self.visit['state']['prescription']['text'].count('【测试方三 · 原方参考】'), 1)
        self.transition('select_formulas', {'ids': ['10003'], 'conversions': {}})
        self.assertEqual(self.visit['state']['prescription']['text'].count('【测试方三 · 原方参考】'), 1)
        self.transition('confirm_prescription', {'reviewed': True})
        self.transition('generate_record')
        record = self.visit['state']['record']
        for name in ('测试方一', '测试方二', '测试方三'):
            self.assertIn('参考基础方：' + name, record)
        for volume in (1, 2, 3):
            self.assertIn(f'辞典依据：第{volume}册', record)

    def test_multiple_formula_selection_validates_scope_limit_and_pending_doses(self):
        candidates = [dict(CANDIDATE, id=str(i), name=f'测试方{i}', fields={'组成': '生地'}) for i in range(1, 7)]
        self.to_analysis()
        with patch('llm.encounters.FormulaRetriever') as retriever:
            retriever.return_value.search.return_value = {'candidates': candidates}
            self.transition('retrieve')
        self.transition('select_formulas', {'ids': ['1', '1']}, status=400)
        self.transition('select_formulas', {'ids': [str(i) for i in range(1, 7)]}, status=400)
        self.transition('select_formulas', {'ids': ['outside']}, status=400)
        self.transition('select_formulas', {'ids': ['1'], 'conversions': {}})
        self.assertIn('剂量待核', self.visit['state']['prescription']['text'])
        self.transition('confirm_prescription', {'reviewed': True}, status=400)

    def test_formula_reference_conversion_is_read_only_and_audited_in_record(self):
        historical = dict(CANDIDATE, fields={'组成': '人参一两甘草二钱', '用法': '测试原方用法'})
        self.to_analysis()
        with patch('llm.encounters.FormulaRetriever') as retriever:
            retriever.return_value.search.return_value = {'candidates': [historical]}
            self.transition('retrieve')
        version = self.visit['version']
        conversion = {'confirmed': True, 'basis': '仅供自动化验证的已核定换算表',
                      'grams_per_unit': {'两': '30', '钱': '3'}}
        response = self.client.post(self.url + 'formula_reference/', {'id': '10001', 'conversion': conversion}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['data']['text'], '人参30g、甘草6g')
        self.assertEqual(Encounter.objects.get(pk=self.visit['id']).version, version)
        self.transition('select_formulas', {'ids': ['10001'], 'conversions': {'10001': conversion}})
        self.transition('confirm_prescription', {'reviewed': True})
        self.transition('generate_record')
        self.assertIn('原方重量换算依据（非日服量）', self.visit['state']['record'])
        self.assertIn(conversion['basis'], self.visit['state']['record'])
