from __future__ import annotations
import csv,hmac,io,os,uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI,File,Form,HTTPException,Request,UploadFile
from fastapi.responses import FileResponse,HTMLResponse,RedirectResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from starlette.middleware.sessions import SessionMiddleware
from .analytics import POINTS,campaign_stats,linear_regression
from .database import UPLOAD_DIR,connection,init_db
from .pdf_report import build_report

BASE=Path(__file__).resolve().parent
@asynccontextmanager
async def lifespan(app): init_db(); yield
app=FastAPI(title="Hausmonitor V3",version="3.0.0",lifespan=lifespan)
app.add_middleware(SessionMiddleware,secret_key=os.getenv("SECRET_KEY","change-me"),https_only=os.getenv("COOKIE_SECURE","false").lower()=="true",same_site="lax")
app.mount("/static",StaticFiles(directory=BASE/"static"),name="static")
templates=Jinja2Templates(directory=BASE/"templates")

def guard(req):
    if os.getenv("APP_PASSWORD","") and not req.session.get("authenticated"):return RedirectResponse('/login',303)
def grouped(cid):
    g={p:[] for p in POINTS}
    with connection() as con:
        for r in con.execute("SELECT point,value FROM readings WHERE campaign_id=? ORDER BY sequence",(cid,)):g[r['point']].append(r['value'])
    return g
def campaigns_all():
    with connection() as con: rows=[dict(x) for x in con.execute("SELECT * FROM campaigns ORDER BY measured_at,id")]
    bh=bt=None; out=[]
    for r in rows:
        s=campaign_stats(grouped(r['id']),bh,bt)
        if bh is None and s['house']['value'] is not None:bh=s['house']['value'];s=campaign_stats(grouped(r['id']),bh,bt)
        if bt is None and s['terrace']['value'] is not None:bt=s['terrace']['value'];s=campaign_stats(grouped(r['id']),bh,bt)
        r['stats']=s;out.append(r)
    return out
def analytics(cs):
    deltas=[c['stats']['house']['delta'] for c in cs]
    return {'time':linear_regression(list(range(len(cs))),deltas),'groundwater':linear_regression([c['groundwater'] for c in cs],deltas),'air_temp':linear_regression([c['air_temp'] for c in cs],deltas),'wall_delta':linear_regression([(c['wall_temp_so']-c['wall_temp_sw']) if c['wall_temp_so'] is not None and c['wall_temp_sw'] is not None else None for c in cs],deltas)}

@app.get('/health')
def health():return {'status':'ok','version':'3.0.0'}
@app.get('/login',response_class=HTMLResponse)
def login_page(request:Request):return templates.TemplateResponse(request=request,name='login.html',context={'error':None})
@app.post('/login')
def login(request:Request,password:str=Form(...)):
    if hmac.compare_digest(password,os.getenv('APP_PASSWORD','')):request.session['authenticated']=True;return RedirectResponse('/',303)
    return templates.TemplateResponse(request=request,name='login.html',context={'error':'Passwort ist falsch.'},status_code=401)
@app.post('/logout')
def logout(request:Request):request.session.clear();return RedirectResponse('/login',303)
@app.get('/',response_class=HTMLResponse)
def dashboard(request:Request):
    if (r:=guard(request)):return r
    cs=campaigns_all();an=analytics(cs);latest=cs[-1] if cs else None
    chart=[{'date':c['measured_at'],'delta':c['stats']['house']['delta'],'low':c['stats']['house']['delta']-c['stats']['house']['se'] if c['stats']['house']['delta'] is not None and c['stats']['house']['se'] is not None else None,'high':c['stats']['house']['delta']+c['stats']['house']['se'] if c['stats']['house']['delta'] is not None and c['stats']['house']['se'] is not None else None,'terrace':c['stats']['terrace']['delta'],'groundwater':c['groundwater'],'air_temp':c['air_temp']} for c in cs]
    return templates.TemplateResponse(request=request,name='dashboard.html',context={'campaigns':list(reversed(cs)),'latest':latest,'chart':chart,'analytics':an})
@app.get('/campaigns/new',response_class=HTMLResponse)
def new(request:Request):
    if (r:=guard(request)):return r
    return templates.TemplateResponse(request=request,name='campaign_form.html',context={'now':datetime.now().strftime('%Y-%m-%dT%H:%M')})
@app.post('/campaigns')
def create(request:Request,measured_at:str=Form(...),air_temp:float|None=Form(None),wall_temp_sw:float|None=Form(None),wall_temp_so:float|None=Form(None),groundwater:float|None=Form(None),rainfall_14d:float|None=Form(None),weather:str=Form(''),light_mode:str=Form(''),notes:str=Form('')):
    if (r:=guard(request)):return r
    with connection() as con:cid=con.execute("INSERT INTO campaigns(measured_at,air_temp,wall_temp_sw,wall_temp_so,groundwater,rainfall_14d,weather,light_mode,notes) VALUES(?,?,?,?,?,?,?,?,?)",(measured_at,air_temp,wall_temp_sw,wall_temp_so,groundwater,rainfall_14d,weather,light_mode,notes)).lastrowid
    return RedirectResponse(f'/campaigns/{cid}/readings',303)
@app.get('/campaigns/{cid}/readings',response_class=HTMLResponse)
def readings_page(request:Request,cid:int):
    if (r:=guard(request)):return r
    with connection() as con:c=con.execute('SELECT * FROM campaigns WHERE id=?',(cid,)).fetchone()
    if not c:raise HTTPException(404)
    return templates.TemplateResponse(request=request,name='readings_form.html',context={'campaign':dict(c),'points':POINTS,'existing':grouped(cid)})
@app.post('/campaigns/{cid}/readings')
async def readings_save(request:Request,cid:int):
    if (r:=guard(request)):return r
    form=await request.form()
    with connection() as con:
        con.execute('DELETE FROM readings WHERE campaign_id=?',(cid,))
        for p in POINTS:
            seq=0
            for raw in form.getlist(p):
                raw=str(raw).strip().replace(',','.')
                if raw:seq+=1;con.execute('INSERT INTO readings(campaign_id,point,sequence,value) VALUES(?,?,?,?)',(cid,p,seq,float(raw)))
    return RedirectResponse(f'/campaigns/{cid}',303)
@app.get('/campaigns/{cid}',response_class=HTMLResponse)
def detail(request:Request,cid:int):
    if (r:=guard(request)):return r
    c=next((x for x in campaigns_all() if x['id']==cid),None)
    if not c:raise HTTPException(404)
    with connection() as con:photos=[dict(x) for x in con.execute('SELECT * FROM photos WHERE campaign_id=? ORDER BY id',(cid,))]
    return templates.TemplateResponse(request=request,name='campaign_detail.html',context={'campaign':c,'readings':grouped(cid),'photos':photos})
@app.post('/campaigns/{cid}/photos')
async def upload_photo(request:Request,cid:int,point:str=Form(...),caption:str=Form(''),photo:UploadFile=File(...)):
    if (r:=guard(request)):return r
    if photo.content_type not in {'image/jpeg','image/png','image/webp'}:raise HTTPException(400,'Nur JPG, PNG oder WebP')
    raw=await photo.read(); ext={'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp'}[photo.content_type]; name=f'{cid}-{uuid.uuid4().hex}{ext}'; path=UPLOAD_DIR/name
    Image.open(io.BytesIO(raw)).verify(); path.write_bytes(raw)
    with connection() as con:con.execute('INSERT INTO photos(campaign_id,point,filename,caption) VALUES(?,?,?,?)',(cid,point,name,caption))
    return RedirectResponse(f'/campaigns/{cid}',303)
@app.get('/uploads/{name}')
def get_photo(request:Request,name:str):
    if (r:=guard(request)):return r
    path=UPLOAD_DIR/Path(name).name
    if not path.exists():raise HTTPException(404)
    return FileResponse(path)
@app.post('/campaigns/{cid}/delete')
def delete(request:Request,cid:int):
    if (r:=guard(request)):return r
    with connection() as con:
        files=[x['filename'] for x in con.execute('SELECT filename FROM photos WHERE campaign_id=?',(cid,))];con.execute('DELETE FROM campaigns WHERE id=?',(cid,))
    for f in files:(UPLOAD_DIR/f).unlink(missing_ok=True)
    return RedirectResponse('/',303)
@app.get('/export.csv')
def export(request:Request):
    if (r:=guard(request)):return r
    out=io.StringIO();w=csv.writer(out,delimiter=';');w.writerow(['ID','Zeitpunkt','Luft °C','Wand SW °C','Wand SO °C','Grundwasser','Regen 14d','Hausdifferenz','Haus Δ','Haus SE','Terrassendifferenz','Terrasse Δ','Bewertung'])
    for c in campaigns_all():s=c['stats'];w.writerow([c['id'],c['measured_at'],c['air_temp'],c['wall_temp_sw'],c['wall_temp_so'],c['groundwater'],c['rainfall_14d'],s['house']['value'],s['house']['delta'],s['house']['se'],s['terrace']['value'],s['terrace']['delta'],s['house']['quality']])
    return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=hausmonitor-v3.csv'})
@app.post('/import.csv')
async def import_csv(request:Request,file:UploadFile=File(...)):
    if (r:=guard(request)):return r
    text=(await file.read()).decode('utf-8-sig');reader=csv.DictReader(io.StringIO(text),delimiter=';')
    with connection() as con:
        for x in reader:
            if not x.get('Zeitpunkt'):continue
            con.execute('INSERT INTO campaigns(measured_at,air_temp,wall_temp_sw,wall_temp_so,groundwater,rainfall_14d,notes) VALUES(?,?,?,?,?,?,?)',(x['Zeitpunkt'],x.get('Luft °C') or None,x.get('Wand SW °C') or None,x.get('Wand SO °C') or None,x.get('Grundwasser') or None,x.get('Regen 14d') or None,'CSV-Import; nur Kampagnenmetadaten'))
    return RedirectResponse('/',303)
@app.get('/report.pdf')
def pdf(request:Request):
    if (r:=guard(request)):return r
    cs=campaigns_all();return StreamingResponse(build_report(cs,analytics(cs)),media_type='application/pdf',headers={'Content-Disposition':'attachment; filename=hausmonitor-bericht.pdf'})
