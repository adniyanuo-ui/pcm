"""Opt-in real Chrome test using an isolated Django test database and fictional data.

PCM_BROWSER_TEST=1 enables the browser. PCM_REAL_MODEL_TEST=1 additionally calls the
configured model and real RAG index; otherwise only the model output is stubbed.
PCM_REAL_SPEECH_TEST=1 adds real NLS token/WebSocket/audio capture tests using
Chrome's synthetic microphone. It does not verify a physical microphone's quality.
"""
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.request import urlopen

from django.contrib.auth.models import User
from django.test import LiveServerTestCase

from llm.models import Encounter
from llm.test_encounters import EXAMINATIONS, ANALYSIS


@unittest.skipUnless(os.getenv('PCM_BROWSER_TEST') == '1', 'opt-in Chrome browser test')
class WorkbenchBrowserTests(LiveServerTestCase):
    def test_complete_visit_in_browser(self):
        root = Path(__file__).resolve().parents[2]
        password = secrets.token_urlsafe(24)
        User.objects.create_user('browser-test-doctor', password=password)
        env = dict(os.environ, VITE_API_BASE_URL=self.live_server_url,
                   PCM_BROWSER_PASSWORD=password, PCM_BROWSER_USERNAME='browser-test-doctor')
        with tempfile.TemporaryDirectory(prefix='pcm-browser-') as folder:
            with open(Path(folder) / 'vite.log', 'w') as log:
                vite = subprocess.Popen(['npm', 'run', 'dev', '--', '--host', '127.0.0.1', '--port', '5176', '--strictPort'],
                                        cwd=root / 'pcm_doctor_web', env=env, stdout=log, stderr=log, start_new_session=True)
                try:
                    for attempt in range(60):
                        try:
                            urlopen('http://127.0.0.1:5176', timeout=1).close()
                            break
                        except OSError:
                            time.sleep(.5)
                    else:
                        self.fail('Vite did not start')
                    def fake_model(kind, payload, model):
                        return (EXAMINATIONS if kind == 'examinations' else ANALYSIS), 'browser-fixture-model'
                    from contextlib import nullcontext
                    model_context = nullcontext() if os.getenv('PCM_REAL_MODEL_TEST') == '1' else patch('llm.encounters.generate_json', side_effect=fake_model)
                    with model_context:
                        result = subprocess.run(['node', str(root / 'scripts/test-workbench-browser.mjs')],
                                                env=env, capture_output=True, text=True, timeout=360)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    print(result.stdout)
                    visit = Encounter.objects.get()
                    self.assertTrue(all(visit.state['confirmed']))
                    self.assertTrue(visit.state['candidates'][0]['source']['pdf_pages'])
                    self.assertGreater(visit.revisions.count(), 10)
                finally:
                    import signal
                    os.killpg(vite.pid, signal.SIGTERM)
                    vite.wait(timeout=10)
