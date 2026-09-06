import time
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from llm.voice import purge_expired_recordings


class Command(BaseCommand):
    help = '清理超过30天的私有录音；保留就诊文字和修改历史。'

    def add_arguments(self, parser):
        parser.add_argument('--watch', action='store_true', help='每60秒检查一次，供受监督的开发/部署进程使用')

    def handle(self, *args, **options):
        while True:
            close_old_connections()
            try:
                count = purge_expired_recordings()
                self.stdout.write(f'已清理到期录音片段：{count}')
            except Exception:
                if not options['watch']:
                    raise
                self.stderr.write('录音清理暂时失败，将在60秒后重试；请检查存储权限及数据库。')
            if not options['watch']:
                return
            time.sleep(60)
