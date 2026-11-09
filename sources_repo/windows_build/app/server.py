"""Application ML locale : prédictions ML et illustration potentielle, édition partage."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
import argparse,csv,hashlib,json,math,re,threading,webbrowser
import os
os.environ.setdefault('LOKY_MAX_CPU_COUNT','8')
import joblib,pandas as pd
from threadpoolctl import threadpool_limits
from potential_flow import compute as compute_flow
from optimizer import Optimizer
APP=Path(__file__).resolve().parent
ROOT=APP.parent
def geometry(value):
    """NACA 4 chiffres, espacement cosinus, corde unitaire, bord de fuite ouvert."""
    code = re.sub(r'\s+', '', str(value)).upper().removeprefix('NACA')
    if not re.fullmatch(r'\d{4}', code):
        raise ValueError('Saisir quatre chiffres, par exemple NACA 0012 ou 2412.')
    m, p, t = int(code[0])/100, int(code[1])/10, int(code[2:])/100
    if t == 0:
        raise ValueError('L’épaisseur doit être supérieure à zéro.')
    if m > 0 and p == 0:
        raise ValueError('Un profil cambré doit avoir une position de cambrure non nulle.')
    if m == 0 and p != 0:
        raise ValueError('Pour un profil symétrique, utiliser 00 comme deux premiers chiffres.')
    upper, lower, mean = [], [], []
    for i in range(241):
        x = (1-math.cos(math.pi*i/240))/2
        yt = 5*t*(.2969*math.sqrt(x)-.126*x-.3516*x*x+.2843*x**3-.1015*x**4)
        if m == 0:
            yc, slope = 0., 0.
        elif x < p:
            yc = m/p**2*(2*p*x-x*x); slope=2*m/p**2*(p-x)
        else:
            yc = m/(1-p)**2*((1-2*p)+2*p*x-x*x); slope=2*m/(1-p)**2*(p-x)
        theta=math.atan(slope)
        upper.append([x-yt*math.sin(theta),yc+yt*math.cos(theta)])
        lower.append([x+yt*math.sin(theta),yc-yt*math.cos(theta)])
        mean.append([x,yc])
    return dict(code=code,profile='NACA '+code,m=m,p=p,t=t,upper=upper,lower=lower,mean=mean)

class Predictor:
    def __init__(self,pointer=None):
        self.pointer=pointer or json.loads((ROOT/'modeles/MODELE_ACTUEL.json').read_text(encoding='utf8'))
        model=ROOT/self.pointer['model_file']
        if hashlib.sha256(model.read_bytes()).hexdigest()!=self.pointer['model_sha256']:raise RuntimeError('Empreinte du modèle incompatible.')
        self.bundle=joblib.load(model)
        assert self.bundle['entrees']==['m','p','t','alpha_deg','Re']
        self.coverage=json.loads((ROOT/self.pointer['domain_file']).read_text(encoding='utf8'))
        exclusions=APP/'case_exclusions.json'
        self.additional_exclusions=json.loads(exclusions.read_text(encoding='utf8')) if exclusions.exists() else []
        existing={(r['profile_id'],int(r['Re']),float(r['alpha_deg'])) for r in self.coverage.get('unqualified_cases',[])}
        for row in self.additional_exclusions:
            if (row['profile_id'],int(row['Re']),float(row['alpha_deg'])) not in existing:
                self.coverage.setdefault('unqualified_cases',[]).append(row)
        self.lock=threading.Lock()
    def evaluate(self,naca,alpha,reynolds):
        g=geometry(naca);alpha=float(alpha);reynolds=float(reynolds)
        if not math.isfinite(alpha) or not math.isfinite(reynolds):raise ValueError('Les conditions doivent être des nombres finis.')
        d=self.coverage['domain'];reasons=[]
        if not d['m'][0]<=g['m']<=d['m'][1] or not d['t'][0]<=g['t']<=d['t'][1] or (g['m']>0 and not d['p_cambered'][0]<=g['p']<=d['p_cambered'][1]):reasons.append('Géométrie hors du domaine ML : cambrure '+str(round(d['m'][1]*100))+' % au maximum, position '+str(round(d['p_cambered'][0]*100))+' à '+str(round(d['p_cambered'][1]*100))+' %, épaisseur '+str(round(d['t'][0]*100))+' à '+str(round(d['t'][1]*100))+' %.')
        conditions_ok=d['alpha_deg'][0]<=alpha<=d['alpha_deg'][1] and abs(alpha*2-round(alpha*2))<1e-8 and reynolds in d['Re']
        if not conditions_ok:reasons.append('Choisir une incidence de −4° à 8° par pas de 0,5° et un Reynolds de 1, 2 ou 3 millions.')
        flags=[g['m']>.060000001,g['m']>0 and g['p']>.700000001,g['t']>.240000001]
        region='original' if not any(flags) else 'combined' if sum(flags)>1 else 'high_camber' if flags[0] else 'rear_camber' if flags[1] else 'thick'
        extension=region!='original'
        if extension and 'supported_extension_regions' in self.coverage:
            if region not in self.coverage['supported_extension_regions']:reasons.append('Cette famille de profils reste exclue : précision ML ou couverture des contrôles insuffisante dans l’extension.')
            if g['m']>.06 and g['p']<.2:reasons.append('Cambrure élevée très en avant : domaine exclu faute de références numériques suffisantes.')
        indata=g['code'] in self.coverage['dataset_codes'];intrain=g['code'] in self.coverage['training_codes']
        result=dict(geometry=g,conditions=dict(alpha_deg=alpha,Re=int(reynolds),Mach=0,Ncrit=9),prediction=None,available=not reasons,reasons=reasons,geometry_in_dataset=indata,geometry_in_training=intrain,prediction_kind='profil_appris' if intrain else ('profil_hors_apprentissage' if indata else 'nouvelle_geometrie'),coverage=self.coverage['domain'],dataset_profile_count=len(self.coverage['dataset_codes']),source='Modèles ML entraînés sur des références XFOIL qualifiées',model_sha256=self.pointer['model_sha256'],model_id=self.pointer['identifiant'])
        unqualified=any(r['profile_id']=='NACA'+g['code'] and int(r['Re'])==int(reynolds) and float(r['alpha_deg'])==alpha for r in self.coverage.get('unqualified_cases',[]))
        additional=next((r for r in self.additional_exclusions if r['profile_id']=='NACA'+g['code'] and int(r['Re'])==int(reynolds) and float(r['alpha_deg'])==alpha),None)
        if additional:
            reasons.append('Cas non qualifié par le dernier contrôle XFOIL : '+additional['reason'])
            result['available']=False
        result['domain_region']=region
        result['extension_prediction']=extension
        result['support_label']='Domaine initial' if not extension else 'Extension contrôlée' if not reasons else 'Hors domaine retenu'
        if extension and unqualified:
            reasons.append('Ce cas de l’extension a échoué aux contrôles numériques XFOIL ; prédiction désactivée pour ces conditions.')
            result['available']=False
        result['accuracy_context']=self.coverage.get('regional_test_metrics',{}).get(region)
        result['numerical_warning']='Ce cas a été exclu de la campagne XFOIL pour qualification insuffisante. La prédiction ML reste non confirmée.' if unqualified else ''
        if not reasons:
            frame=pd.DataFrame([[g['m'],g['p'],g['t'],alpha,reynolds]],columns=self.bundle['entrees'])
            with self.lock,threadpool_limits(limits=2):
                cl=float(self.bundle['modeles']['CL'].predict(frame)[0]);cd=float(self.bundle['modeles']['CD'].predict(frame)[0])
            if not math.isfinite(cl) or not math.isfinite(cd) or cd<=0:raise ValueError('La prédiction n’est pas exploitable.')
            result['prediction']=dict(CL=cl,CD=cd,finesse=cl/cd)
        return result

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url=urlsplit(self.path)
        try:
            if url.path=='/api/evaluate':
                q=parse_qs(url.query);self.json(200,self.server.predictor.evaluate(q.get('naca',['0012'])[0],q.get('alpha',['0'])[0],q.get('re',['1000000'])[0]))
            elif url.path=='/api/optimize':
                q=parse_qs(url.query,keep_blank_values=True)
                if not hasattr(self.server,'optimizer'):self.server.optimizer=Optimizer(self.server.predictor)
                self.json(200,self.server.optimizer.search(q.get('objective',['max_finesse'])[0],q.get('alpha',['4'])[0],q.get('re',['1000000'])[0],q.get('cl_min',['0.6'])[0],q.get('thickness_min',['12'])[0],q.get('reference',['2412'])[0]))
            elif url.path=='/api/flow':
                q=parse_qs(url.query);g=geometry(q.get('naca',['0012'])[0]);self.json(200,compute_flow(g['code'],float(q.get('alpha',['0'])[0])))
            elif url.path in ('/','/app.js','/flow.js','/optimize.js','/style.css'):
                name,kind={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/flow.js':('flow.js','text/javascript'),'/optimize.js':('optimize.js','text/javascript'),'/style.css':('style.css','text/css')}[url.path];self.respond(200,(APP/name).read_bytes(),kind+'; charset=utf-8')
            else:self.json(404,dict(error='Introuvable'))
        except (ValueError,TypeError) as e:self.json(400,dict(error=str(e)))
        except Exception:self.json(500,dict(error='Erreur du calcul local. Consulter le journal de lancement.'))
    def do_POST(self):
        self.json(405,dict(error='Méthode non autorisée.'))
    def json(self,status,obj):self.respond(status,json.dumps(obj,ensure_ascii=False,allow_nan=False).encode('utf8'),'application/json; charset=utf-8')
    def respond(self,status,body,kind):
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)

def self_check(predictor):
    cases=json.loads((APP/'reference_cases.json').read_text(encoding='utf8'))
    for case in cases:
        actual=predictor.evaluate(case['naca'],case['alpha'],case['Re'])
        assert actual['available']==case['available'], case
        if actual['available']:
            for key,value in case['prediction'].items():
                assert math.isclose(actual['prediction'][key],value,rel_tol=1e-6,abs_tol=1e-8), (case,key)
    flow=compute_flow('0012',4)
    assert flow['profile_rotation_deg']==-4 and len(flow['streamlines'])>10
    assert flow['boundary_residual']<1e-6
    print(f"Vérification réussie : {len(cases)} cas ML et illustration de l'écoulement.",flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--port',type=int,default=0)
    p.add_argument('--open',action='store_true')
    p.add_argument('--check',action='store_true')
    a=p.parse_args();predictor=Predictor()
    if a.check:self_check(predictor);return
    s=ThreadingHTTPServer(('127.0.0.1',a.port),Handler)
    s.predictor=predictor;url=f'http://127.0.0.1:{s.server_port}'
    print(f'AeroDesign AI prêt : {url}',flush=True)
    print('Laisser cette fenêtre ouverte. Pour arrêter : Ctrl+C.',flush=True)
    if a.open:webbrowser.open(url)
    try:s.serve_forever()
    except KeyboardInterrupt:pass
    finally:s.server_close()
if __name__=='__main__':main()
