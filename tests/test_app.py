import os
os.environ['DATABASE_PATH']='/tmp/hausmonitor-v3-test.db';os.environ['UPLOAD_DIR']='/tmp/hausmonitor-v3-uploads';os.environ['APP_PASSWORD']=''
from fastapi.testclient import TestClient
from app.main import app
from app.database import DB_PATH

def setup_module():
    if DB_PATH.exists():DB_PATH.unlink()
def test_full_flow():
    with TestClient(app) as c:
        assert c.get('/health').json()['version']=='3.0.0'
        r=c.post('/campaigns',data={'measured_at':'2026-10-02T10:00','air_temp':'16','wall_temp_sw':'16.7','wall_temp_so':'17.6'},follow_redirects=False);cid=r.headers['location'].split('/')[2]
        data={'SW':['2.575','2.58','2.58','2.575','2.585'],'SO':['8.27','8.27','8.275','8.28','8.275'],'TSW':['3','3.01','3','3','2.99'],'TSO':['9','9.01','9','9','8.99']}
        c.post(f'/campaigns/{cid}/readings',data=data)
        page=c.get(f'/campaigns/{cid}');assert page.status_code==200 and '5.695' in page.text
        assert c.get('/export.csv').status_code==200
        pdf=c.get('/report.pdf');assert pdf.status_code==200 and pdf.content[:4]==b'%PDF'
