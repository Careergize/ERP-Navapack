import os
from pathlib import Path
import shutil
import subprocess
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import LiveServerTestCase


class MastersHTTPTransportTests(LiveServerTestCase):
    def test_actual_react_adapters_with_jwt_and_postgresql(self):
        user=get_user_model().objects.create_user('integration@example.test','long-development-password')
        user.user_permissions.add(*Permission.objects.filter(content_type__app_label='masters',codename__in=['view_customer','add_customer','change_customer']))
        env=dict(os.environ,MASTERS_LIVE_URL=self.live_server_url+'/api/v1')
        result=subprocess.run([shutil.which('node'),'scripts/check-masters-api.mjs'],cwd=Path(__file__).resolve().parents[2]/'frontend',env=env,capture_output=True,text=True,timeout=120)
        self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
        self.assertIn('LIVE MASTERS PASS',result.stdout)
