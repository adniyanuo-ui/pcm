# MacBook Pro 本地开发与演示

本方案在同一台 Mac 上运行医生工作台、Django、SQLite 和方剂 RAG；实时语音识别与大模型通过在线 API 调用。浏览器访问 localhost 时可直接申请麦克风权限，不需要域名或 HTTPS。

## 一、Mac准备

需要：

- macOS；
- Python 3.12 或 3.13；
- Node.js 22 或 24；
- Git；
- Chrome最新版；
- 可访问阿里云智能语音交互和在线大模型的网络。

首次使用终端时可先安装苹果命令行工具：

~~~bash
xcode-select --install
~~~

## 二、下载与初始化

~~~bash
git clone https://github.com/adniyanuo-ui/pcm.git
cd pcm
chmod +x scripts/mac-bootstrap.sh scripts/run-local-demo.sh
./scripts/mac-bootstrap.sh
~~~

脚本会创建Python虚拟环境、安装依赖、迁移SQLite数据库、构建97MB左右的RAG索引并安装前端依赖。

## 三、配置密钥

编辑：

~~~text
pcm-master_hyd/.env.local
~~~

至少填写：

~~~text
QWEN_API_KEY=
ALIYUN_ACCESS_KEY_ID=
ALIYUN_ACCESS_KEY_SECRET=
ALIYUN_NLS_APPKEY=
~~~

AccessKey只放在后端环境文件。浏览器只能从后端取得短期NLS Token。

## 四、创建医生账号

~~~bash
cd pcm-master_hyd
.venv/bin/python manage.py createsuperuser
cd ..
~~~

## 五、启动

~~~bash
./scripts/run-local-demo.sh
~~~

使用Chrome打开：

~~~text
http://localhost:5174
~~~

首次点击录音时选择“允许麦克风”。暂停和继续会创建独立的语音会话，但已经转写的文字会继续保留。

## 六、演示前检查

1. 连接稳定Wi-Fi，并准备手机热点；
2. Mac接入电源并关闭自动睡眠；
3. Chrome已允许localhost使用麦克风；
4. 登录医生账号；
5. 录制一句话，确认能实时出现文字；
6. 暂停后继续录制，确认前文没有丢失；
7. 确认RAG候选方显示“真实检索”；
8. 全程使用演示病例或去标识信息。

当前程序不保存原始音频，仅在内存中实时发送PCM帧，页面和后端保存的是转写文字。
