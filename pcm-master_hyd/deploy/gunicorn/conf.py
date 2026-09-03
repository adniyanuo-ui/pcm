# _*_coding:utf-8_*_
# __author: g
import os

# import gevent.monkey

# gevent.monkey.patch_all()

# import multiprocessing

os.makedirs("logs", exist_ok=True)

# debug = True
loglevel = 'info'
bind = "0.0.0.0:9999"
pidfile = "logs/gunicorn.pid"
accesslog = "logs/access.log"
errorlog = "logs/debug.log"

daemon = True
# spew = True

# 启动的进程数
# workers = multiprocessing.cpu_count() * 2 + 1
workers = 6
worker_class = 'gevent'
timeout = 3000
# worker_connections = 2000
# x_forwarded_for_header = 'X-FORWARDED-FOR'

# thrift_protocol_factory = "thriftpy2.protocol:TCompactProtocolFactory"  # 客户端生成的时候要和这个对应，传输协议， 高效率的、密集的二进制编码格式进行数据传输，推荐使用
# thrift_transport_factory = "thriftpy2.transport:TBufferedTransportFactory"  # 加了缓存的传输控制，推荐方式
# gunicorn label_studio_expand.wsgi:application -c deploy/gunicorn/conf.py
# gunicorn -c deploy/gunicorn/conf.py label_studio_expand.wsgi
# /opt/label_studio_expand
