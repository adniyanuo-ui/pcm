docker run --name mysql \
--restart=always \
-p 3306:3306 \
-v ~/docker_data/mysql/data:/var/lib/mysql \
-v ~/docker_data/mysql/conf:/etc/mysql/conf.d \
    -e MYSQL_ROOT_PASSWORD="${PCM_MYSQL_ROOT_PASSWORD:?set PCM_MYSQL_ROOT_PASSWORD}" \
-d mysql:8.0


docker run --restart=always --name redis \
-p 6379:6379 \
-v ~/docker_data/redis/data:/data \
-d redis:6.2

docker run --restart=always --name pcm \
-p 8000:8000 \
-w /opt \
-v ~/pcm:/opt/data \
-d python:3.12-bullseye


env CURRANT_ENV=prod gunicorn -c deploy/gunicorn/conf.py pcm.wsgi

celery -A pcm worker -c 4 --queues=default --loglevel=info -n celery@local -f "logs/celery.log" -D
celery -A pcm worker -c 16 --queues=default -n celery@local -f "logs/celery.log"

celery -A pcm inspect registered
