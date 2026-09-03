# 医生坐诊工作台

面向年轻中医大夫的 Vue 3 交互原型。该项目独立于原有患者填报端和 CMS，当前用于先验证一次坐诊的核心体验，再逐步接入现有 Django API、语音转写和方剂 RAG。

## 本地运行

```bash
cd pcm_doctor_web
npm install
npm run dev
```

默认地址为 `http://127.0.0.1:5174`。

生产构建：

```bash
npm run build
```

## 当前原型范围

- 真实麦克风采集、阿里云NLS实时转写、暂停/继续及医患对话校对；
- 四诊信息分区编辑和信息缺口提醒；
- 辨证、病机、治法证据链；
- 带方号、匹配点、不匹配点和原文页码的候选基础方；
- 可增减药味与剂量的处方草稿；
- 不虚构缺失字段的门诊病历草稿与完整性检查；
- 所有阶段均保留“AI 草稿、医师确认”的状态边界。

页面中的胡女士资料及诊疗内容均为演示数据，不对应真实患者，也不构成医疗建议。

## 接入真实方剂检索

未配置 API 地址时，页面明确显示“演示数据”。需要连接本地 Django 时：

1. 将 .env.example 复制为 .env.local；
2. 启动后端并确认 http://127.0.0.1:8000 可访问；
3. 重新执行 npm run dev；
4. 使用后端已创建的医生账号登录。

本地后端首次启动：

~~~bash
cd ../pcm-master_hyd
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python -m llm_utils.rag build
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
~~~

真实检索结果会显示“真实检索”标志，并使用后端返回的方号、辞典字段和原书页码。

## 真实语音转写

连接后端时，录音按钮会进入“实时转写”模式：

- 后端使用AccessKey动态签发短期NLS Token；
- 浏览器只接收Token、AppKey和固定网关，不接触AccessKey Secret；
- 浏览器以AudioWorklet采集音频，并转为16kHz、16bit、单声道PCM；
- 收到阿里云TranscriptionStarted事件后才发送音频帧；
- 支持中间识别结果、完整句子、暂停、继续和断线错误提示；
- 暂停不会丢失已经转写的内容；
- 当前不保存原始音频。

后端语音配置参见 pcm-master_hyd/.env.example。Mac完整运行方式参见项目根目录的《Mac本地演示说明》。
