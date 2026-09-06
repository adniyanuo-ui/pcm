"""Source-preserving formatting and arithmetic, never clinical dose invention.

The small lexicon only inserts separators in fully recognised compositions. It
does not normalise aliases, resolve OCR, infer missing doses or combine formulas.
Historical mass factors have no defaults: the doctor supplies a cited basis for
each unit, because period, preparation and per-dose use cannot be inferred safely.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from rest_framework import serializers

HERBS = set('''生地 生地黄 熟地 熟地黄 当归 白芍 赤芍 丹皮 牡丹皮 黄芩 连翘 防风 荆芥 木通 银花 金银花
人参 党参 太子参 沙参 北沙参 南沙参 泡参 玄参 丹参 白术 炒白术 苍术 茯苓 白茯苓 茯神 猪苓 泽泻
甘草 炙甘草 生甘草 黄芪 炙黄芪 桂枝 肉桂 官桂 桂心 麻黄 炙麻黄 杏仁 苦杏仁 桃仁 陳皮
生姜 干姜 炮姜 大枣 红枣 半夏 法半夏 姜半夏 清半夏 陈皮 青皮 橘红 竹茹 枳实 枳壳
厚朴 姜厚朴 柴胡 黄连 黄柏 栀子 山栀 石膏 生石膏 知母 麦冬 麦门冬 天冬 天门冬
五味子 吴茱萸 吴茱 细辛 附子 制附子 熟附子 白附子 炮附子 乌头 川乌 草乌 干地黄
大黄 生大黄 熟大黄 芒硝 玄明粉 葛根 升麻 薄荷 牛蒡子 桔梗 前胡 羌活 独活 白芷
川芎 藁本 香附 木香 砂仁 白豆蔻 草豆蔻 草果 小茴香 乌药 高良姜 山药 淮山 扁豆 白扁豆
莲子 薏苡仁 薏仁 山楂 麦芽 神曲 鸡内金 莱菔子 酸枣仁 柏子仁 远志 龙骨 牡蛎 龙齿
磁石 朱砂 琥珀 石菖蒲 阿胶 龟板 龟甲 鳖甲 龟板胶 鹿角胶 鹿茸 鹿角 菟丝子 杜仲
牛膝 川牛膝 怀牛膝 续断 桑寄生 巴戟天 肉苁蓉 锁阳 淫羊藿 补骨脂 益智仁 山茱萸 枸杞子
女贞子 旱莲草 墨旱莲 桑椹 桑叶 菊花 夏枯草 决明子 钩藤 天麻 石决明 珍珠母 蒺藜
栝楼 栝楼根 瓜蒌 瓜蒌皮 瓜蒌仁 天花粉 贝母 川贝 浙贝 川贝母 浙贝母 百部 紫菀 款冬花
桑白皮 葶苈子 苏子 紫苏子 苏叶 紫苏叶 苏梗 白前 旋覆花 代赭石 赭石 竹沥 竹叶 淡竹叶
滑石 车前子 车前草 通草 灯心草 茵陈 茵陈蒿 萹蓄 瞿麦 地肤子 海金沙 金钱草 冬葵子
木瓜 防己 汉防己 五加皮 香加皮 威灵仙 秦艽 桑枝 络石藤 忍冬藤 益母草 泽兰 红花 苏木
三七 蒲黄 五灵脂 延胡索 元胡 郁金 姜黄 三棱 莪术 穿山甲 乳香 没药 灵脂 艾叶 焦艾
白及 白芨 仙鹤草 地榆 槐花 槐米 侧柏叶 小蓟 大蓟 茜草 血余炭 百合 石斛 玉竹 黄精
饴糖 蜂蜜 白蜜 冰糖 粳米 糯米 小麦 浮小麦 胡麻仁 火麻仁 郁李仁 诃子 乌梅 五倍子
赤石脂 禹余粮 肉豆蔻 莲须 芡实 金樱子 覆盆子 海螵蛸 乌贼骨 桑螵蛸 文蛤 海蛤壳'''.split())
NAME = re.compile('|'.join(re.escape(h) for h in sorted(HERBS, key=lambda h: (-len(h), h))))
DOSE = re.compile(r'(?P<number>\d+(?:\.\d+)?|[零〇一二三四五六七八九十百千两半]+)\s*(?P<unit>毫克|mg|克|g|钱匕|两|钱|分|厘|斤|铢|枚|个|片|升|合|盏)(?P<half>半(?!夏))?', re.I)
MASS_UNITS = set('两钱分厘斤铢')
SEPARATORS = ' \t\r\n、，,；;。'


def number(text):
    if text == '半':
        return Decimal('.5')
    if re.fullmatch(r'\d+(?:\.\d+)?', text):
        return Decimal(text)
    digits = dict(zip('零〇一二三四五六七八九两', [0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 2]))
    total, current = 0, 0
    # Fail closed for ambiguous OCR numbers such as "一二" rather than guessing twelve.
    previous_digit = False
    for ch in text:
        if ch in digits:
            if previous_digit:
                raise ValueError('ambiguous number')
            current = digits[ch]; previous_digit = True
        elif ch in '十百千':
            total += (current or 1) * {'十': 10, '百': 100, '千': 1000}[ch]
            current = 0; previous_digit = False
        else:
            raise ValueError('unknown number')
    return Decimal(total + current)


def parse_composition(text):
    items, pending = [], []
    pos = 0
    def skip(p):
        while p < len(text) and text[p] in SEPARATORS:
            p += 1
        return p
    try:
        while (pos := skip(pos)) < len(text):
            match = NAME.match(text, pos)
            if not match:
                return []
            item = dict(herb=match.group(), note='', dose='', quantities=[])
            items.append(item); pending.append(item); pos = skip(match.end())
            if pos < len(text) and text[pos] in '(（':
                end = text.find(')' if text[pos] == '(' else '）', pos)
                if end < 0:
                    return []
                item['note'] = text[pos:end + 1]; pos = skip(end + 1)
            shared = pos < len(text) and text[pos] == '各'
            if shared:
                pos = skip(pos + 1)
            dose_start, quantities = pos, []
            equal_parts = text.startswith('等分', pos)
            if equal_parts:
                pos += 2
            while match := DOSE.match(text, pos):
                amount = number(match['number']) + (Decimal('.5') if match['half'] else 0)
                if amount <= 0:
                    return []
                quantities.append(dict(amount=str(amount), unit=match['unit'].lower()))
                pos = match.end()
            if shared and not quantities and not equal_parts:
                return []
            if quantities or equal_parts:
                for target in pending if shared else [item]:
                    target['dose'] = text[dose_start:pos]; target['quantities'] = quantities
                if equal_parts and not shared:
                    for target in pending:
                        target['dose'] = '等分'; target['quantities'] = []
                pending = []
        return items
    except (ValueError, InvalidOperation):
        return []


def conversion_config(value, units):
    if not value:
        return None
    def require(ok):
        if not ok:
            raise serializers.ValidationError('换算需医师确认每种重量单位的克数及依据；数量、容量不能直接换算为g。')
    require(isinstance(value, dict) and value.get('confirmed') is True)
    basis = value.get('basis')
    require(isinstance(basis, str) and 0 < len(basis.strip()) <= 500)
    factors = value.get('grams_per_unit')
    require(isinstance(factors, dict) and bool(factors) and set(factors) == set(units))
    result = {}
    for unit, factor in factors.items():
        require(unit in MASS_UNITS and isinstance(factor, (str, int, float)) and not isinstance(factor, bool))
        try:
            require(bool(re.fullmatch(r'\d{1,6}(?:\.\d{1,6})?', str(factor))))
            amount = Decimal(str(factor))
            require(amount.is_finite() and 0 < amount <= 100000)
        except InvalidOperation:
            require(False)
        result[unit] = str(amount)
    return dict(basis=basis.strip(), grams_per_unit=result, confirmed=True)


def build_reference(candidate, conversion=None):
    raw = candidate.get('fields', {}).get('组成', '').strip()
    items = parse_composition(raw) if len(raw) <= 20000 else []
    units = sorted({q['unit'] for item in items for q in item['quantities'] if q['unit'] in MASS_UNITS})
    config = conversion_config(conversion, units)
    factors = {'g': Decimal(1), '克': Decimal(1), 'mg': Decimal('.001'), '毫克': Decimal('.001')}
    if config:
        factors.update({u: Decimal(v) for u, v in config['grams_per_unit'].items()})
    for item in items:
        quantities = item['quantities']
        grams = None
        if quantities and all(q['unit'] in factors for q in quantities):
            grams = sum(Decimal(q['amount']) * factors[q['unit']] for q in quantities)
            rounded = grams.quantize(Decimal('.000001'), rounding=ROUND_HALF_UP)
            grams = format(rounded, 'f').rstrip('0').rstrip('.') if rounded else None
        item['grams'] = grams
        item['display'] = item['herb'] + ((grams + 'g') if grams is not None else item['dose'] or '（剂量待核）') + item['note']
    text = '、'.join(item['display'] for item in items) if items else raw
    warnings = []
    if raw and not items:
        warnings.append('原文未能可靠分隔，保留原文；请核对药名、炮制、剂量。')
    if any(not item['dose'] for item in items) or not raw:
        warnings.append('原文缺少剂量或组成，不能据此补造建议克数。')
    if units:
        warnings.append('历史衡制须逐方核定；换算是原方重量参考，不是当前患者的日服量。')
    if any(q['unit'] not in MASS_UNITS and q['unit'] not in factors for i in items for q in i['quantities']):
        warnings.append('枚、片、升等数量或容量保留原单位，不按重量换算。')
    return dict(id=candidate['id'], name=candidate['name'], original=raw, text=text,
                items=items, convertible_units=units, conversion=config, warnings=warnings,
                source=candidate['source'], usage=candidate.get('fields', {}).get('用法', ''))


def reference_draft(reference):
    if not reference['original']:
        return '（组成及剂量待核）'
    verification = '（药名与剂量待核）' if not reference['items'] else ''
    return '\n\n'.join(filter(None, [reference['text'], verification, reference['usage']]))
