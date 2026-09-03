<template>
    <div class="one-sentence-asr">
        <!-- 录音按钮 -->
        <el-button
            :type="isRecording ? 'danger' : 'primary'"
            :icon="isRecording ? 'el-icon-turn-off-microphone' : 'el-icon-microphone'"
            size="medium"
            @click="toggleRecording"
            :disabled="isUploading"
        >
            {{ isRecording ? '停止录音' : '开始录音' }}
        </el-button>

        <!-- 上传识别 -->
        <el-button
            type="success"
            icon="el-icon-upload"
            size="medium"
            @click="uploadAudio"
            :disabled="!audioBlob || isRecording"
            :loading="isUploading"
        >
            {{ isUploading ? '识别中...' : '上传识别' }}
        </el-button>

        <!-- 录音时长 -->
        <span class="duration" v-show="duration > 0">
      {{ formatTime(duration) }}
    </span>

        <!-- 识别结果 -->
        <el-input
            v-model="resultText"
            type="textarea"
            :rows="4"
            placeholder="识别结果..."
            readonly
            class="result-area"
        ></el-input>

        <!-- 错误提示 -->
        <el-alert
            v-if="errorMsg"
            :title="errorMsg"
            type="error"
            :closable="false"
            show-icon
            style="margin-top: 15px;"
        ></el-alert>
    </div>
</template>

<script>
export default {
    name: 'OneSentenceASR',
    data() {
        return {
            isRecording: false,
            isUploading: false,
            audioBlob: null,
            audioUrl: null,
            duration: 0,
            resultText: '',
            errorMsg: '',
            mediaRecorder: null,
            timer: null,
            stream: null
        }
    },
    methods: {
        async toggleRecording() {
            if (this.isRecording) {
                this.stopRecording();
            } else {
                await this.startRecording();
            }
        },

        async startRecording() {
            try {
                this.errorMsg = '';
                this.resultText = '';

                // 请求麦克风权限
                this.stream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        sampleRate: 16000,
                        channelCount: 1,
                        echoCancellation: true
                    }
                });

                // 创建MediaRecorder
                const options = { mimeType: 'audio/pcm' };
                this.mediaRecorder = new MediaRecorder(this.stream, options);
                const chunks = [];

                this.mediaRecorder.ondataavailable = (e) => {
                    if (e.data.size > 0) chunks.push(e.data);
                };

                this.mediaRecorder.onstop = () => {
                    this.audioBlob = new Blob(chunks, { type: 'audio/webm' });
                    this.audioUrl = URL.createObjectURL(this.audioBlob);
                };

                // 开始录制
                this.mediaRecorder.start();
                this.isRecording = true;
                this.duration = 0;

                // 计时器
                this.timer = setInterval(() => {
                    this.duration++;
                }, 1000);

            } catch (error) {
                this.errorMsg = `录音失败: ${error.message}`;
                if (error.name === 'NotAllowedError') {
                    this.errorMsg = '请授权使用麦克风！';
                }
            }
        },

        stopRecording() {
            if (this.mediaRecorder && this.isRecording) {
                this.mediaRecorder.stop();
                this.isRecording = false;
                clearInterval(this.timer);

                // 停止媒体流
                if (this.stream) {
                    this.stream.getTracks().forEach(track => track.stop());
                }
            }
        },

        async uploadAudio() {
            if (!this.audioBlob) {
                this.errorMsg = '请先录音！';
                return;
            }

            this.isUploading = true;
            this.errorMsg = '';

            const formData = new FormData();
            formData.append('audio', this.audioBlob, 'recording.webm');
            formData.append('format', 'webm');

            try {
                const response = await this.$axios.post('/api/asr/onesentence/', formData, {
                    timeout: 30000
            });

                if (response.data.success) {
                    this.resultText = response.data.result.text;
                    this.$message.success('识别成功！');
                } else {
                    this.errorMsg = `识别失败: ${response.data.message}`;
                }
            } catch (error) {
                this.errorMsg = `上传失败: ${error.message}`;
                console.error(error);
            } finally {
                this.isUploading = false;
            }
        },

        formatTime(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
    },

    beforeDestroy() {
        this.stopRecording();
        if (this.audioUrl) {
            URL.revokeObjectURL(this.audioUrl);
        }
    }
}
</script>

<style scoped>
.one-sentence-asr {
    padding: 20px;
    background: #f5f7fa;
    border-radius: 8px;
}
.duration {
    margin-left: 15px;
    font-size: 18px;
    color: #606266;
    font-weight: bold;
}
.result-area {
    margin-top: 20px;
}
</style>
