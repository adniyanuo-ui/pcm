import type {
  AnalysisItem,
  ExaminationSection,
  FormulaCandidate,
  PrescriptionItem,
  StageDefinition,
  TranscriptLine,
} from '../types/consultation'

export const stages: StageDefinition[] = [
  { key: 'intake', shortLabel: '记', label: '问诊记录', hint: '语音与原文' },
  { key: 'examination', shortLabel: '诊', label: '四诊合参', hint: '补充并确认' },
  { key: 'analysis', shortLabel: '辨', label: '辨证治法', hint: '病机与治法' },
  { key: 'formula', shortLabel: '方', label: '选方遣药', hint: '有据可查' },
  { key: 'record', shortLabel: '案', label: '病历确认', hint: '编辑与存档' },
]

export const initialTranscript: TranscriptLine[] = [
  { id: 1, role: '患者', time: '09:42', content: '最近两个多月总觉得没力气，吃饭也没什么胃口。' },
  { id: 2, role: '医生', time: '09:43', content: '大便情况怎么样？一天几次？' },
  { id: 3, role: '患者', time: '09:43', content: '一天两三次，比较稀，吃凉的会更明显。' },
  { id: 4, role: '医生', time: '09:44', content: '有没有腹痛、腹胀，或者口渴？' },
  { id: 5, role: '患者', time: '09:44', content: '饭后会有点胀，喝水正常，手脚偶尔有点凉。' },
]

export const initialExaminations: ExaminationSection[] = [
  {
    key: '望',
    title: '神色·舌象',
    value: '神情清，面色少华；舌质淡，舌体略胖有齿痕，苔薄白。',
    placeholder: '记录神色、形态、舌质、舌苔……',
    source: '大夫面诊',
  },
  {
    key: '闻',
    title: '语声·气息',
    value: '语声偏低，气息平，未闻及异常气味。',
    placeholder: '记录语声、呼吸、气味……',
    source: '大夫面诊',
  },
  {
    key: '问',
    title: '主要症状',
    value: '乏力、纳差两月余；大便溏，日行2—3次，食凉加重；饭后腹胀，偶有手足凉。',
    placeholder: '记录寒热、饮食、二便、睡眠等……',
    source: '对话整理',
  },
  {
    key: '切',
    title: '脉象·按诊',
    value: '脉细弱，右关尤甚；腹部柔软，无明显压痛。',
    placeholder: '记录脉象及其他按诊发现……',
    source: '大夫面诊',
  },
]

export const analysisItems: AnalysisItem[] = [
  { label: '八纲', value: '里·虚，偏寒', evidence: '病程缠绵、乏力脉弱为虚；食凉加重、手足凉为寒象线索。' },
  { label: '脏腑', value: '脾胃气虚', evidence: '纳差、饭后腹胀、便溏与右关脉弱指向脾失健运。' },
  { label: '气血津液', value: '气虚，清阳不振', evidence: '乏力、语声低、面色少华、舌淡脉细弱。' },
]

export const formulaCandidates: FormulaCandidate[] = [
  {
    id: '22393',
    name: '四君子汤',
    source: '《鸡峰》卷十二',
    match: 92,
    summary: '益气健脾，与“脾胃气虚、食少便溏”主证最直接。',
    supports: ['食少便溏', '体倦乏力', '面色少华', '脉细弱'],
    cautions: ['偶有手足凉，尚需判断是否已至阳虚'],
    composition: '人参、白术、茯苓、甘草各一两',
    original: '主治：脾肺气虚，中土衰弱，食少便溏，体瘦神倦，或气短息微。',
    citation: { volume: 3, pdfPage: 554, bookPage: 449 },
  },
  {
    id: '17964',
    name: '六君子汤',
    source: '《医学正传》卷三引《局方》',
    match: 78,
    summary: '益气健脾，兼理气化痰；腹胀时可作备选。',
    supports: ['脾胃虚弱', '食少便溏', '饭后腹胀', '面色少华'],
    cautions: ['当前痰湿、呕恶等证据不足'],
    composition: '陈皮、半夏、茯苓、甘草、人参、白术',
    original: '功用：益气健脾，理气降逆。主治：脾胃虚弱，气逆痰滞，食少便溏。',
    citation: { volume: 2, pdfPage: 1144, bookPage: 1060 },
  },
  {
    id: '47002',
    name: '附子理中丸',
    source: '《局方》卷五',
    match: 61,
    summary: '温脾散寒，适合脾胃虚寒较明显者。',
    supports: ['食凉加重', '便溏', '手足凉'],
    cautions: ['未见明显腹痛、呕吐、脉微肢厥', '温阳药使用需由大夫审慎确认'],
    composition: '附子、人参、干姜、甘草、白术各三两',
    original: '功用：温脾散寒，止泻止痛。主治：脾胃虚寒，食少满闷，腹痛吐利。',
    citation: { volume: 5, pdfPage: 1155, bookPage: 1067 },
  },
]

export const initialPrescription: PrescriptionItem[] = [
  { id: 1, herb: '党参', dose: '12g', note: '补中益气' },
  { id: 2, herb: '炒白术', dose: '12g', note: '健脾燥湿' },
  { id: 3, herb: '茯苓', dose: '12g', note: '健脾渗湿' },
  { id: 4, herb: '炙甘草', dose: '6g', note: '益气和中' },
  { id: 5, herb: '陈皮', dose: '6g', note: '理气和胃，针对饭后腹胀' },
]
