<template>
    <div>
        <el-dialog :visible.sync="dialog_visible" width="80%" top="2vh">
            <iframe :src="pdf_src" width="100%" style="height: 80vh;"></iframe>
        </el-dialog>

        <el-dialog title="模型方案" :visible.sync="llm_visible" width="80%" top="2vh" :before-close="close_llm">
            <el-tabs v-model="tab_active_name" style="padding: 15px;">
                <el-tab-pane label="模型输入" name="inp">
                    <div class="chat-box">
                        <div style="font-weight: 500;">患者资料</div>
                        <div style="margin-bottom: 10px; height: 5%; overflow-y: auto;" class="message">
                            <span>{{ `${cur_llm_data.user.trim()}` }}</span>
                        </div>

                        <div v-if="cur_llm_data.question" style="font-weight: 500;">问卷症状</div>
                        <div v-if="cur_llm_data.question" style="margin-bottom: 10px; height: 20%; overflow-y: auto;"
                             class="message">
                            <span>{{ `${cur_llm_data.question.trim()}` }}</span>
                        </div>

                        <div style="font-weight: 500;">
                            医患对话实时记录
                            <el-button @click="toggleRecording" size="mini" type="text" round>
                                {{ isRecording ? '停止录音' : '开始录音' }}
                            </el-button>
                        </div>
                        <div style="margin-bottom: 10px; height: 20%; white-space: pre-line; text-overflow: ellipsis; overflow-y: auto; position: relative;" class="message">
                            {{ record_text }}
                        </div>

                        <div style="font-weight: 500;">
                            医患对话症状提取
                            <el-button @click="genDialogue" size="mini" type="text" round :disabled="dialogue_loading">
                                {{ '生成医患对话' }}
                            </el-button>

                            <el-button @click="dialogue_edit = !dialogue_edit" size="mini" type="text" round
                                       :disabled="dialogue_loading">
                                {{ '编辑' }}
                            </el-button>
                        </div>
                        <div style="margin-bottom: 10px; height: 24%; overflow-y: auto;" class="message"
                             ref="message_dialogue">
                            <div v-if="!dialogue_edit">
                                <div v-html="renderedMarkdown(dialogue_output)"></div>
                            </div>
                            <div v-else>
                                <el-input type="textarea" v-model="dialogue_output" resize="none" :rows="8"></el-input>
                            </div>
                        </div>

                        <div style="font-weight: 500;">大夫面诊录入症状</div>
                        <div style="margin-bottom: 10px; overflow-y: auto;">
                            <div>
                                <el-input type="textarea" v-model="cur_llm_data.doctor" resize="none"
                                          :rows="3" placeholder="脉诊、舌诊，面部特征、神气光泽等症状记录"></el-input>
                            </div>
                        </div>
                    </div>
                </el-tab-pane>
                <el-tab-pane label="模型输出" name="oup">
                    <div class="chat-box">
                        <el-form :inline="true" class="demo-form-inline" size="mini" style="margin-bottom: 5px;">
                            <el-form-item label="模型选择">
                                <el-select v-model="model_name" placeholder="模型选择" clearable>
                                    <el-option label="豆包" value="doubao-seed-2-0-pro-260215">豆包</el-option>
                                    <el-option label="通义千问-max" value="qwen3-max">通义千问-max</el-option>
                                    <el-option label="通义千问-plus" value="qwen3.5-plus">通义千问-plus</el-option>
                                    <el-option label="通义千问-turbo" value="qwen-turbo">通义千问-turbo</el-option>
                                    <el-option label="deepseek V3" value="deepseek-chat">deepseek V3</el-option>
                                    <el-option label="deepseek R1" value="deepseek-reasoner">deepseek R1</el-option>
                                </el-select>
                            </el-form-item>

                            <el-form-item label="历史">
                                <el-select placeholder="历史" v-model="history_select_id" style="width: 350px;">
                                    <el-option v-for="one_llm_data in llm_data"
                                               v-if="one_llm_data.id"
                                               :label="`${one_llm_data.star_str} ${one_llm_data.created_time} ${one_llm_data.model_name}`"
                                               :value="one_llm_data.id"
                                               @click.native="on_click_history(one_llm_data)"
                                    >
                                        {{
                                            `${one_llm_data.star_str} ${one_llm_data.created_time} ${one_llm_data.model_name}`
                                        }}
                                    </el-option>
                                    <!--							<el-option label="通义千问-push" value="qwen-push">通义千问-push</el-option>-->
                                    <!--							<el-option label="通义千问-turbo" value="qwen-turbo">通义千问-turbo</el-option>-->
                                    <!--							<el-option label="deepseek V3" value="deepseek-chat">deepseek V3</el-option>-->
                                    <!--							<el-option label="deepseek R1" value="deepseek-reasoner">deepseek R1</el-option>-->
                                </el-select>
                            </el-form-item>

                            <el-form-item>
                                <el-button type="primary" @click="get_llm_out" :loading="is_loading">生成</el-button>
                            </el-form-item>

                            <el-form-item>
                                <el-button @click="cur_llm_data.edit = !cur_llm_data.edit"
                                           :disabled="!cur_llm_data.output_over">
                                    {{ cur_llm_data.edit ? `完成编辑` : `编辑` }}
                                </el-button>
                            </el-form-item>

                            <!--						<el-form-item>-->
                            <!--							<el-button @click="on_copy" :disabled="!cur_llm_data.output_over">复制</el-button>-->
                            <!--						</el-form-item>-->
                        </el-form>

                        <div style="display: flex; justify-content: center; align-items: center;">
                            内容为AI生成，仅做辅助，不替代医师决策
                        </div>
                        <div style="height: 88%; overflow-y: auto;" class="message1" ref="message1">
                            <div v-if="cur_llm_data.reasoning" class="reasoner typewriter-container">
                                深度思考：
                                <div v-html="renderedMarkdown(cur_llm_data.reasoning)"></div>
                            </div>
                            <div v-if="cur_llm_data.output" class="typewriter-container">
                                <div v-if="cur_llm_data.edit">
                                    <el-input style="height: 43vh;" type="textarea" v-model="cur_llm_data.output"
                                              resize="none"
                                              :rows="2"></el-input>
                                </div>
                                <div v-else v-html="renderedMarkdown(cur_llm_data.output)"></div>
                                <!--						<span class="cursor"></span>-->
                            </div>
                        </div>

                        <div style="display: flex; justify-content: center; align-items: center;"
                             v-if="cur_llm_data.output_over">
                            <el-rate v-model="cur_llm_data.star" @click.native="on_rate"></el-rate>
                            <el-button @click="on_copy" :disabled="!cur_llm_data.output_over" size="mini">复制
                            </el-button>
                            <!--						<el-button type="primary" size="mini" @click="on_rate">保存</el-button>-->
                        </div>
                    </div>

                </el-tab-pane>
            </el-tabs>

        </el-dialog>

        <el-container>
            <el-header class="header">
                <el-form :inline="true" :model="form" class="demo-form-inline" size="mini">
                    <el-form-item style="width: 150px;">
                        <el-input v-model="form.name" placeholder="姓名"></el-input>
                    </el-form-item>

                    <el-form-item style="width: 80px;">
                        <el-select v-model="form.sex" placeholder="性别" clearable>
                            <el-option label="男" value="男">男</el-option>
                            <el-option label="女" value="女">女</el-option>
                        </el-select>
                    </el-form-item>

                    <el-form-item style="width: 80px;">
                        <el-input v-model="form.age" placeholder="年龄"></el-input>
                    </el-form-item>

                    <!--					<el-form-item style="width: 80px;">-->
                    <!--						<el-select v-model="form.q_type" placeholder="类型">-->
                    <!--							<el-option label="通用" value="common">通用</el-option>-->
                    <!--							<el-option label="学校" value="school">学校</el-option>-->
                    <!--							<el-option label="企业" value="company">企业</el-option>-->
                    <!--							<el-option label="机关单位" value="gov">机关单位</el-option>-->
                    <!--						</el-select>-->
                    <!--					</el-form-item>-->

                    <!--					<el-form-item style="width: 80px;">-->
                    <!--						<el-input v-model="form.company" placeholder="高校/企业"></el-input>-->
                    <!--					</el-form-item>-->

                    <!--					<el-form-item style="width: 80px;">-->
                    <!--						<el-input v-model="form.department" placeholder="院系/部门"></el-input>-->
                    <!--					</el-form-item>-->

                    <el-form-item>
                        <el-date-picker v-model="date_range" type="daterange" range-separator="至"
                                        value-format="yyyy-MM-dd"
                                        start-placeholder="开始日期" end-placeholder="结束日期">
                        </el-date-picker>
                    </el-form-item>

                    <el-form-item>
                        <el-button type="primary" @click="onSearch">查询</el-button>
                    </el-form-item>

                    <el-form-item>
                        <el-button type="success" @click="export_to_excel">导出</el-button>
                    </el-form-item>
                </el-form>
            </el-header>

            <el-main>
                <el-table :data="data.results" style="width: 100%;" border highlight-current-row class="custom-table">
                    "id", "name", "sex", "age", "date", "phone", "marital_status", "job", "origin", "result", "file"
                    "height", "weight", "blood_type", "blood_sugar", "blood_pressure", "q_type", "company", "department"
                    <!--					<el-table-column prop="id" label="id" width="50"/>-->
                    <el-table-column prop="name" label="姓名"/>
                    <el-table-column prop="sex" label="性别" width="60"/>
                    <el-table-column prop="age" label="年龄" width="60"/>
                    <el-table-column prop="height" label="身高(cm)" width="80"/>
                    <el-table-column prop="weight" label="体重(kg)" width="80"/>
                    <el-table-column prop="q_type" label="类型" width="60"/>
                    <!--					<el-table-column prop="company" label="学校企业" width="80"/>-->
                    <!--					<el-table-column prop="department" label="院系部门" width="80"/>-->
                    <!--					<el-table-column prop="blood_type" label="血型" width="60"/>-->
                    <!--					<el-table-column prop="blood_sugar" label="血糖" width="60"/>-->
                    <!--					<el-table-column prop="blood_pressure" label="血压" width="60"/>-->
                    <el-table-column prop="phone" label="联系方式" width="120" show-overflow-tooltip/>
                    <el-table-column prop="marital_status" label="婚姻" width="60"/>
                    <el-table-column prop="job" label="职业" width="100" show-overflow-tooltip/>
                    <el-table-column prop="origin" label="长期居住地" width="100" show-overflow-tooltip/>
                    <el-table-column label="测试结果" width="120" show-overflow-tooltip>
                        <template #default="scope">
                            <div class="ellipsis" style="cursor: pointer;" @click="showFile(scope.row)">
                                {{ scope.row.result }}
                            </div>
                        </template>
                    </el-table-column>
                    <el-table-column label="操作" width="100">
                        <template #default="scope">
                            <el-button round size="mini" @click="on_open_llm(scope.row)">AI辅助</el-button>
                            <!--							<el-button round size="mini" @click="on_open_llm(scope.row)">AI自动推荐</el-button>-->
                        </template>
                    </el-table-column>
                </el-table>
            </el-main>

            <el-footer class="footer">
                <el-pagination layout="prev, pager, next" :total="data.count" :current-page.sync="current_page"
                               :page-size="form.limit"
                               @current-change="handleCurrentChange">
                </el-pagination>
            </el-footer>
        </el-container>
    </div>
</template>

<script>
import {on_get_data, on_token} from "@/api/patient";
import {on_get_llm_data, star} from "@/api/llm";
import store from "@/store";
import "github-markdown-css";
import MarkdownIt from "markdown-it";
import {Message} from "element-ui";
import * as XLSX from "xlsx";
// import { marked } from 'marked';

export default {
    name: 'patientList',
    components: {},
    data() {
        return {
            form: {
                name: "",
                sex: "",
                age: "",
                date: "",
                q_type: "",
                company: "",
                department: "",

                limit: 10,
                offset: 0,
            },
            date_range: [],
            current_page: 1,
            data: {},
            dialog_visible: false,
            pdf_src: "",

            // 大模型相关
            tab_active_name: "inp",
            llm_visible: false,
            llm_data: [],
            cur_llm_data: {
                "id": 0,
                "patient_id": 0,
                "user": "",
                "question": "",
                "doctor": "",
                "output": "",
                "reasoning": "",
                "star": 0,
                "output_over": false,
                "edit": false
            },
            history_select_id: "",
            model_name: "qwen3-max",
            is_loading: false,
            rate: 0,
            record_id: 0,

            // 打字机相关
            typingInterval: null,
            md: new MarkdownIt(),

            // 录音相关
            stream: null,
            mediaRecorder: null,
            isRecording: null,
            pre_record_text: "",
            record_text: "",
            chunks: [],

            websocket: null,
            token: null,
            speech_appkey: null,
            record_text_map: {},
            audioContext: null,
            scriptProcessor: null,
            audioInput: null,
            audioStream: null,

            // 医患对话大模型相关
            dialogue_loading: false,
            dialogue_output: "",
            dialogue_edit: false,
        }
    },
    methods: {
        renderedMarkdown(txt) {
            return this.md.render(txt);
        },
        async get_data() {
            if (!this.date_range) {
                this.form.date = ""
            } else if (this.date_range.length === 2) {
                this.form.date = this.date_range.join("~")
            }
            // console.log(this.form.date)
            this.form["offset"] = (this.current_page - 1) * this.form.limit
            const resp = await on_get_data(this.form)
            this.data = resp.data;
        },
        async onSearch() {
            this.current_page = 1
            this.form["offset"] = 0
            await this.get_data()
        },
        async handleCurrentChange(val) {
            this.current_page = val
            await this.get_data()
        },
        showFile(patient) {
            this.pdf_src = patient.file
            this.dialog_visible = true
        },
        on_open_llm(row) {
            on_get_llm_data({"pid": row.id}).then(res => {
                // this.connectWebSocket()
                this.llm_data = res.data;
                this.cur_llm_data = {...this.llm_data[0]}
                this.llm_visible = true
                this.history_select_id = this.cur_llm_data.id
                this.dialogue_output = this.cur_llm_data.dialogue
            })
        },
        async get_llm_out() {
            // this.cur_llm_data = {...this.llm_data[this.llm_data.length - 1]}
            // this.history_select_id = this.cur_llm_data.id
            this.is_loading = true
            try {
                this.cur_llm_data.id = 0
                this.cur_llm_data.star = 0
                this.cur_llm_data.edit = false
                this.cur_llm_data.output = ""
                this.cur_llm_data.reasoning = ""
                this.cur_llm_data.output_over = false
                this.history_select_id = ""

                const row = JSON.stringify({
                    "model_name": this.model_name, "user": this.cur_llm_data.user, "doctor": this.cur_llm_data.doctor,
                    "patient_id": this.cur_llm_data.patient_id, "question": this.cur_llm_data.question,
                    "dialogue": this.dialogue_output,
                })
                const response = await fetch(
                    `${process.env.VUE_APP_API_ROOT}/api/cms/llm/chat/`,
                    {
                        method: 'POST',
                        headers: {
                            "Content-Type": "application/json",
                            "Authorization": `Token ${store.state.user.token}`
                        },
                        body: row,
                    },
                );
                const reader = response.body.getReader();
                const decoder = new TextDecoder('utf-8');

                while (true) {
                    if (!this.is_loading) break;

                    const {done, value} = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value, {stream: true})
                    console.log('接收到的流式数据：', chunk); // 打印到控制台
                    for (let one_chunk of chunk.split("endendend")) {
                        if (!one_chunk) {
                            continue;
                        }
                        // console.log("pre parse", one_chunk)
                        one_chunk = JSON.parse(one_chunk);
                        // console.log("one_chunk", one_chunk)
                        this.cur_llm_data.output += one_chunk["data"]["output"];
                        this.cur_llm_data.reasoning += one_chunk["data"]["reasoning"];
                        this.cur_llm_data.id = one_chunk["data"]["revise_id"];
                        this.$nextTick(() => {
                            this.$refs.message1.scrollTop = this.$refs.message1.scrollHeight;
                        });
                    }
                }
                this.cur_llm_data.output_over = true
            } catch (error) {
                this.cur_llm_data.output = "请求失败"
                console.error('流式请求失败', error);
            } finally {
                this.is_loading = false
            }
        },
        close_llm() {
            // this.disconnectWebSocket()
            this.stopRecording()
            this.is_loading = false
            this.llm_visible = false
            this.record_text = ""
            this.pre_record_text = ""
            this.record_text_map = {}
        },
        on_rate() {
            star({
                "revise_id": this.cur_llm_data.id,
                "star": this.cur_llm_data.star,
                "revise_output": this.cur_llm_data.output
            }).then(response => {
                this.llm_data.splice(this.llm_data.length - 1, 0, response.data[0]);
                // this.llm_data[this.llm_data.length - 1] = response.data[0]
                // this.llm_data.push(response.data[1])
                this.cur_llm_data = {...response.data[0]}
                this.history_select_id = this.cur_llm_data.id
            })
        },
        on_click_history(one_llm_data) {
            this.cur_llm_data = {...one_llm_data}
            // console.log(this.history_select_id)
        },
        on_copy() {
            this.$copyText(this.cur_llm_data.output).then(() => {
                Message.success("文本已复制到剪贴板！")
            }).catch(err => {
                Message.error(`复制失败：${err}`)
            });
        },
        export_to_excel() {
            let form = JSON.parse(JSON.stringify(this.form));
            delete form.limit;
            delete form.offset;
            on_get_data(form).then(res => {
                let export_data = [];
                for (const obj of res.data) {
                    export_data.push({
                        "姓名": obj.name,
                        "性别": obj.sex,
                        "年龄": obj.age,
                        "身高": obj.height,
                        "体重": obj.weight,
                        "学校企业": obj.company,
                        "院系部门": obj.department,
                        "焦虑等级": obj.jl_level,
                        "抑郁等级": obj.yu_level,
                    });
                }
                // 创建工作表
                const data = XLSX.utils.json_to_sheet(export_data);
                // 创建工作簿
                const wb = XLSX.utils.book_new();
                // 将工作表放入工作簿中
                XLSX.utils.book_append_sheet(wb, data, "data");
                // 生成文件并下载
                XLSX.writeFile(wb, `问卷数据.xlsx`);
            });
        },
        async toggleRecording() {
            if (this.isRecording) {
                this.stopRecording();
            } else {
                await this.startRecording();
            }
        },
        async webmChunkToPCM(webmBlob) {
            // 1. Blob -> ArrayBuffer
            const arrayBuffer = await webmBlob.arrayBuffer();

            // 2. 解码为 AudioBuffer
            const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);

            // 3. 取第一声道
            const float32Array = audioBuffer.getChannelData(0);

            // 4. Float32 -> Int16
            const int16Array = new Int16Array(float32Array.length);
            for (let i = 0; i < float32Array.length; i++) {
                const s = Math.max(-1, Math.min(1, float32Array[i]));
                int16Array[i] = s * 0x7FFF;
            }

            // 5. 转 Base64
            return this.arrayBufferToBase64(int16Array.buffer);
        },
        arrayBufferToBase64(buffer) {
            const bytes = new Uint8Array(buffer);
            let binary = '';
            for (let i = 0; i < bytes.length; i++) {
                binary += String.fromCharCode(bytes[i]);
            }
            return btoa(binary);
        },

        // 开始录音
        async startRecording() {
            await this.connectWebSocket()
            console.log(1111)
            this.isRecording = true;
            try {
                let websocket = this.websocket
                // 获取音频输入设备
                this.audioStream = await navigator.mediaDevices.getUserMedia({audio: true});
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                    sampleRate: 16000
                });
                this.audioInput = this.audioContext.createMediaStreamSource(this.audioStream);

                // 设置缓冲区大小为2048的脚本处理器
                this.scriptProcessor = this.audioContext.createScriptProcessor(2048, 1, 1);

                this.scriptProcessor.onaudioprocess = function (event) {
                    const inputData = event.inputBuffer.getChannelData(0);
                    const inputData16 = new Int16Array(inputData.length);
                    for (let i = 0; i < inputData.length; ++i) {
                        inputData16[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7FFF; // PCM 16-bit
                    }
                    if (websocket && websocket.readyState === WebSocket.OPEN) {
                        websocket.send(inputData16.buffer);
                        console.log('发送音频数据块');
                    }
                };

                this.audioInput.connect(this.scriptProcessor);
                this.scriptProcessor.connect(this.audioContext.destination);
            } catch (e) {
                console.log('录音失败: ' + e);
                this.isRecording = false;
            }
        },
        // 停止录音
        stopRecording() {
            this.isRecording = false;
            if (this.scriptProcessor) {
                this.scriptProcessor.disconnect();
            }
            if (this.audioInput) {
                this.audioInput.disconnect();
            }
            if (this.audioStream) {
                this.audioStream.getTracks().forEach(track => track.stop());
            }
            if (this.audioContext) {
                this.audioContext.close();
            }
            this.disconnectWebSocket()
            this.pre_record_text = this.record_text
            this.record_text_map = {}
            if (this.pre_record_text && !this.pre_record_text.endsWith("\n")) {
                this.pre_record_text += "\n"
            }
        },

        // async startRecording() {
        //     this.isRecording = true;
        //     try {
        //         this.stream = await navigator.mediaDevices.getUserMedia({
        //             audio: {
        //                 sampleRate: 16000,
        //                 channelCount: 1,
        //                 echoCancellation: true,
        //                 noiseSuppression: true
        //             }
        //         });
        //
        //         this.audioContext = new AudioContext({sampleRate: 16000});
        //
        //         this.mediaRecorder = new MediaRecorder(this.stream, {mimeType: 'audio/webm'});
        //         this.mediaRecorder.ondataavailable = async (event) => {
        //             this.chunks.push(event.data); // 累积
        //             const webm = new Blob(this.chunks);
        //
        //             const pcmBase64 = await this.webmChunkToPCM(webm);
        //             on_asp({"audio": pcmBase64, "format": "webm"}).then((res) => {
        //                 this.record_text = res.data.result
        //             })
        //         };
        //
        //         this.mediaRecorder.start(1000);
        //     } catch (error) {
        //         console.error('启动录音失败:', error);
        //         this.isRecording = false;
        //     }
        // },
        // stopRecording() {
        //     this.isRecording = false;
        //     if (this.mediaRecorder) {
        //         this.mediaRecorder.stop();
        //         this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
        //     }
        // },
        async genDialogue() {
            // this.cur_llm_data = {...this.llm_data[this.llm_data.length - 1]}
            // this.history_select_id = this.cur_llm_data.id
            this.dialogue_loading = true
            this.dialogue_output = ""
            this.dialogue_edit = false
            try {
                const row = JSON.stringify({"text": this.record_text})
                const response = await fetch(
                    `${process.env.VUE_APP_API_ROOT}/api/cms/llm/gen/dialogue/`,
                    {
                        method: 'POST',
                        headers: {
                            "Content-Type": "application/json",
                            "Authorization": `Token ${store.state.user.token}`
                        },
                        body: row,
                    },
                );
                const reader = response.body.getReader();
                const decoder = new TextDecoder('utf-8');

                while (true) {
                    if (!this.dialogue_loading) break;

                    const {done, value} = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value, {stream: true})
                    console.log('接收到的流式数据：', chunk); // 打印到控制台
                    for (let one_chunk of chunk.split("endendend")) {
                        if (!one_chunk) {
                            continue;
                        }
                        // console.log("pre parse", one_chunk)
                        one_chunk = JSON.parse(one_chunk);
                        // console.log("one_chunk", one_chunk)
                        this.dialogue_output += one_chunk["data"]["output"];
                        this.$nextTick(() => {
                            this.$refs.message_dialogue.scrollTop = this.$refs.message_dialogue.scrollHeight;
                        });
                    }
                }

                this.dialogue_loading = false
            } catch (error) {
                this.dialogue_output = "请求失败"
                console.error('流式请求失败', error);
            } finally {

            }
        },
        generateUUID() {
            return ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, c =>
                (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
            ).replace(/-/g, '');
        },
        async connectWebSocket() {
            await on_token().then(response => {
                this.token = response.data.token
                this.speech_appkey = response.data.appkey
                // console.log(response.data)
                // console.log("token = " + this.token)
                const socketUrl = `${response.data.gateway}?token=${this.token}`;
                const speechAppkey = this.speech_appkey

                let websocket = new WebSocket(socketUrl);
                this.websocket = websocket
                websocket.onopen = function () {
                    console.log('连接到 WebSocket 服务器');

                    var startTranscriptionMessage = {
                        header: {
                            appkey: speechAppkey,
                            namespace: "SpeechTranscriber",
                            name: "StartTranscription",
                            task_id: ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, c =>
                                (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
                            ).replace(/-/g, ''),
                            message_id: ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, c =>
                                (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
                            ).replace(/-/g, '')
                        },
                        payload: {
                            "format": "pcm",
                            "sample_rate": 16000,
                            "enable_intermediate_result": true,
                            "enable_punctuation_prediction": true,
                            "enable_inverse_text_normalization": true
                        }
                    };

                    websocket.send(JSON.stringify(startTranscriptionMessage));
                };

                websocket.onmessage = (event) => {
                    console.log('服务端: ' + event.data);

                    const message = JSON.parse(event.data);
                    if ("payload" in message) {
                        let index = message.payload.index
                        this.record_text_map[`${index}`] = message.payload.result;
                        this.record_text = this.pre_record_text + Object.values(this.record_text_map).join("")
                    }
                };

                websocket.onerror = function (event) {
                    // updateStatus('错误');
                    console.log('WebSocket 错误: ', event);
                };

                websocket.onclose = function () {
                    // updateStatus('断开连接');
                    console.log('与 WebSocket 服务器断开');
                };
            })
        },
        // 断开WebSocket连接
        disconnectWebSocket() {
            if (this.websocket) {
                this.websocket.close();
            }
        }
    },
    mounted() {
        this.get_data()
    },
}
</script>

<style lang="scss" scoped>
::v-deep .el-form-item {
    margin-bottom: 0;
}
::v-deep .el-form--inline .el-form-item {
    margin-right: 20px;
}
::v-deep .el-table .el-table__cell {
    text-align: center;
}
::v-deep .el-textarea__inner {
    height: 100%;
}
::v-deep .el-dialog__body {
    padding: 10px 5px;
}
.header {
    display: flex;
    align-items: center;
}
.footer {
    display: flex;
    justify-content: center;
}
.ellipsis {
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
}
.chat-box {
    height: 80vh;
    overflow-y: auto;
    padding: 10px;
}
.message {
    width: 100%;
    display: inline-block;
    padding: 5px 10px;
    border-radius: 5px;
    background-color: #f0f0f0;
    white-space: pre;
}
.message1 {
    width: 100%;
    display: inline-block;
    padding: 5px 10px;
    border-radius: 5px;
    background-color: #f0f0f0;
}
.textarea {
    width: 100%;
    height: 14vh;
}
.reasoner {
    border-radius: 5px;
    background-color: rgb(255, 255, 255);
    padding: 5px;
}
.typewriter-container * {
    font-family: monospace;
    position: relative;
    //width: auto;
}
.cursor {
    display: inline-block;
    width: 2px;
    height: 1em;
    background-color: black;
    animation: blink 1s step-end infinite;
}
@keyframes blink {
    from,
    to {
        opacity: 1;
    }
    50% {
        opacity: 0;
    }
}
</style>
