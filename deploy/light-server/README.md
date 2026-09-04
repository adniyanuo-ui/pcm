# 香港轻量服务器部署

该配置面向1—2位医生的早期试用，目标规格为Ubuntu 24.04、2核2GB、40GB。运行时只保留Caddy和一个Django容器，不运行本地MySQL、Redis或Celery。

## 服务器准备

防火墙只开放22、80、443。域名添加A记录并指向服务器固定IPv4。

安装基础软件：

~~~bash
sudo apt update
sudo apt install -y git docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
~~~

退出SSH并重新登录，使docker用户组生效。

2GB服务器建议准备2GB交换空间，避免首次构建镜像时内存不足：

~~~bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
~~~

## 首次部署

使用GitHub只读Deploy Key克隆仓库后：

~~~bash
cd pcm/deploy/light-server
cp .env.example .env
nano .env
~~~

至少修改：

- PCM_DOMAIN；
- DJANGO_SECRET_KEY；
- 一个在线大模型API Key；
- ALIYUN_ACCESS_KEY_ID；
- ALIYUN_ACCESS_KEY_SECRET；
- ALIYUN_NLS_APPKEY。

生成随机Django密钥：

~~~bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
~~~

确认域名A记录已生效、80和443端口已开放，然后启动：

~~~bash
docker compose up -d --build
docker compose ps
~~~

Caddy会为PCM_DOMAIN自动申请并续期HTTPS证书。首次构建会生成RAG索引并迁移SQLite数据库。

创建第一个医生账号：

~~~bash
docker compose exec api python manage.py createsuperuser
~~~

检查：

~~~bash
curl "https://你的域名/api/health/"
docker compose logs --tail=100 api
docker compose logs --tail=100 web
~~~

健康检查正常时返回database和rag均为true。

## 更新

~~~bash
git pull --ff-only origin main
cd deploy/light-server
docker compose up -d --build
~~~

服务器首次部署完成后会安装 `pcm-auto-update.timer`。它每10分钟检查一次GitHub
main分支；没有新提交时不执行任何构建，有新提交时才进行快进更新、构建、健康
检查并记录已部署版本。常规更新不需要再登录服务器。

数据保存在Docker命名卷pcm_data中，重新构建镜像不会删除。不要执行带有volumes参数的down命令。

## 备份

轻量服务器控制台至少每日创建一次自动快照。SQLite数据库还应定期导出到服务器以外的位置；正式试用规模扩大后迁移到RDS。

当前部署不会持久化原始音频。浏览器直接将内存中的PCM音频帧发送至阿里云实时语音识别，服务器只签发短期Token。
