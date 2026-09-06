from django.test import SimpleTestCase
from rest_framework import serializers

from llm.formula_references import build_reference, parse_composition, reference_draft


def candidate(composition):
    return {
        'id': '1', 'name': '虚构测试方', 'fields': {'组成': composition, '用法': '原方用法'},
        'source': {'volume': 1, 'pdf_pages': [10], 'book_pages': [2], 'citation': '测试出处'},
    }


class FormulaReferenceTests(SimpleTestCase):
    def test_concatenated_known_herbs_get_separators_without_inventing_doses(self):
        raw = '生地当归白芍丹皮黄芩连翘防风荆芥木通银花'
        result = build_reference(candidate(raw))
        self.assertEqual([item['herb'] for item in result['items']],
                         ['生地', '当归', '白芍', '丹皮', '黄芩', '连翘', '防风', '荆芥', '木通', '银花'])
        self.assertEqual(result['text'].count('、'), 9)
        self.assertTrue(all('剂量待核' in item['display'] for item in result['items']))

    def test_existing_metric_doses_are_formatted_but_not_changed(self):
        result = build_reference(candidate('生地1g当归2克白芍500mg'))
        self.assertEqual(result['text'], '生地1g、当归2g、白芍0.5g')
        self.assertEqual([item['grams'] for item in result['items']], ['1', '2', '0.5'])

    def test_banxia_after_a_dose_is_not_mistaken_for_half_a_unit(self):
        result = build_reference(candidate('陈皮一钱半夏一钱五分茯苓一钱甘草一钱'))
        self.assertEqual(result['text'], '陈皮一钱、半夏一钱五分、茯苓一钱、甘草一钱')

    def test_equal_parts_and_parenthetical_processing_are_preserved(self):
        result = build_reference(candidate('人参（切去顶）白茯苓（去皮）白术陳皮（锉）甘草等分'))
        self.assertEqual(result['text'], '人参等分（切去顶）、白茯苓等分（去皮）、白术等分、陳皮等分（锉）、甘草等分')

    def test_historical_mass_conversion_requires_all_units_and_a_basis(self):
        original = build_reference(candidate('人参一两甘草二钱'))
        self.assertEqual(original['text'], '人参一两、甘草二钱')
        self.assertEqual(original['convertible_units'], ['两', '钱'])
        conversion = {'confirmed': True, 'basis': '仅供自动化验证的已核定换算表',
                      'grams_per_unit': {'两': '30', '钱': '3'}}
        converted = build_reference(candidate('人参一两甘草二钱'), conversion)
        self.assertEqual(converted['text'], '人参30g、甘草6g')
        self.assertEqual(converted['conversion'], conversion)
        with self.assertRaises(serializers.ValidationError):
            build_reference(candidate('人参一两甘草二钱'),
                            {'confirmed': True, 'basis': '不完整', 'grams_per_unit': {'两': '30'}})

    def test_unknown_or_ambiguous_content_is_preserved_verbatim(self):
        raw = 'OCR未知药甲6～9g（另研）'
        result = build_reference(candidate(raw))
        self.assertEqual(result['items'], [])
        self.assertEqual(result['text'], raw)
        self.assertIn('保留原文', result['warnings'][0])
        self.assertIn('剂量待核', reference_draft(result))
        self.assertEqual(parse_composition('人参一二两'), [])

    def test_count_and_volume_units_are_never_converted_to_weight(self):
        result = build_reference(candidate('大枣三枚生姜二片'))
        self.assertEqual(result['text'], '大枣三枚、生姜二片')
        self.assertEqual(result['convertible_units'], [])
        self.assertTrue(any('不按重量换算' in warning for warning in result['warnings']))
