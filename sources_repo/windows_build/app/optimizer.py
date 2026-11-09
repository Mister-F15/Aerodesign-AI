"""Classement ML pur, sans lecture de polaires, calcul XFOIL ou entraînement."""
from collections import OrderedDict
import math,threading
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

class Optimizer:
    def __init__(self,predictor):
        self.predictor=predictor;self.lock=threading.Lock();self.cache=OrderedDict()
        self.domain=predictor.coverage['original_domain']
        d=self.domain;self.rows=[]
        for m in range(round(d['m'][0]*100),round(d['m'][1]*100)+1):
            for p in ([0] if m==0 else range(round(d['p_cambered'][0]*10),round(d['p_cambered'][1]*10)+1)):
                for t in range(round(d['t'][0]*100),round(d['t'][1]*100)+1):
                    self.rows.append(dict(code=f'{m}{p}{t:02}',m=m/100,p=p/10,t=t/100))
        self.codes={r['code'] for r in self.rows}
        self.unqualified={(r['profile_id'],int(r['Re']),float(r['alpha_deg'])) for r in predictor.coverage.get('unqualified_cases',[])}

    def predictions(self,alpha,reynolds):
        key=(alpha,reynolds)
        with self.lock:
            if key not in self.cache:
                frame=pd.DataFrame([[r['m'],r['p'],r['t'],alpha,reynolds] for r in self.rows],columns=self.predictor.bundle['entrees'])
                with self.predictor.lock,threadpool_limits(limits=2):
                    values={c:self.predictor.bundle['modeles'][c].predict(frame) for c in ['CL','CD']}
                result=[]
                for row,cl,cd in zip(self.rows,values['CL'],values['CD']):
                    cl,cd=float(cl),float(cd)
                    if not (math.isfinite(cl) and math.isfinite(cd) and cd>0):continue
                    result.append(dict(**row,CL=cl,CD=cd,finesse=cl/cd,known_unqualified=('NACA'+row['code'],reynolds,alpha) in self.unqualified))
                self.cache[key]=result
                if len(self.cache)>8:self.cache.popitem(last=False)
            self.cache.move_to_end(key)
            return self.cache[key]

    def search(self,objective='max_finesse',alpha=4,reynolds=1000000,cl_min=.6,thickness_min=12,reference='2412'):
        if objective not in ['max_finesse','min_CD','max_CL']:raise ValueError('Objectif inconnu.')
        alpha,reynolds,cl_min,thickness_min=map(float,[alpha,reynolds,cl_min,thickness_min])
        if not all(math.isfinite(v) for v in [alpha,reynolds,cl_min,thickness_min]):raise ValueError('Les paramètres doivent être des nombres finis.')
        d=self.domain
        if not d['alpha_deg'][0]<=alpha<=d['alpha_deg'][1] or abs(alpha*2-round(alpha*2))>1e-8:raise ValueError('Incidence : −4 à 8°, par pas de 0,5°.')
        if reynolds not in d['Re']:raise ValueError('Reynolds : choisir 1, 2 ou 3 millions.')
        if not 0<=cl_min<=3:raise ValueError('CL minimal : choisir une valeur entre 0 et 3.')
        if not d['t'][0]*100<=thickness_min<=d['t'][1]*100 or not thickness_min.is_integer():raise ValueError('Épaisseur minimale : choisir un pourcentage entier de 6 à 24 %.')
        reynolds=int(reynolds);thickness=thickness_min/100
        # Une référence hors contraintes reste un point de comparaison. Une
        # référence hors domaine ou non qualifiée ne fournit aucun gain chiffré.
        ref=None
        if str(reference).strip():
            value=self.predictor.evaluate(reference,alpha,reynolds);g=value['geometry'];ref=dict(code=g['code'],m=g['m'],p=g['p'],t=g['t'],prediction=None,available=False,reasons=[])
            if g['code'] not in self.codes:ref['reasons'].append('Référence hors du domaine de recherche (épaisseur 6–24 %, cambrure 0–6 %, position 10–70 %).')
            elif not value['available']:ref['reasons'].extend(value['reasons'])
            elif value.get('numerical_warning'):ref['reasons'].append('Ce cas de référence est signalé non qualifié ; comparaison indisponible.')
            else:
                ref.update(available=True,prediction=value['prediction'],constraints_met=bool(value['prediction']['CL']>=cl_min and g['t']>=thickness))
        values=self.predictions(alpha,reynolds)
        allowed=[r for r in values if not r['known_unqualified'] and r['t']>=thickness and r['CL']>=cl_min]
        metric={'max_finesse':'finesse','min_CD':'CD','max_CL':'CL'}[objective]
        allowed.sort(key=lambda r:(r[metric] if objective=='min_CD' else -r[metric],r['code']))
        best=[]
        for i,row in enumerate(allowed[:5],1):
            r={k:v for k,v in row.items() if k!='known_unqualified'};r['rank']=i;r['improvement_pct']=None;r['objective_delta']=None
            if ref and ref['available']:
                before=ref['prediction'][metric];delta=(before-r[metric]) if objective=='min_CD' else (r[metric]-before)
                r['objective_delta']=delta
                usable=(abs(before)>=.01 if metric=='CL' else before>1e-8 and (metric!='finesse' or abs(ref['prediction']['CL'])>=.01))
                if usable:r['improvement_pct']=100*delta/abs(before)
            r['boundary']=bool(r['m'] in d['m'] or r['t'] in d['t'] or (r['m']>0 and r['p'] in d['p_cambered']) or r['t']==thickness)
            best.append(r)
        return dict(objective=objective,metric=metric,conditions=dict(alpha_deg=alpha,Re=reynolds,Mach=0,Ncrit=9),constraints=dict(CL_min=cl_min,thickness_min_pct=int(thickness_min)),domain=d,total_geometries=len(self.rows),after_thickness=sum(r['t']>=thickness for r in self.rows),known_unqualified=sum(r['known_unqualified'] for r in values),feasible_count=len(allowed),candidates=best,reference=ref,model_id=self.predictor.pointer['identifiant'],model_sha256=self.predictor.pointer['model_sha256'],source='ML',xfoil_executed=False,model_refitted=False,empty_reason='Aucun profil ne respecte ces contraintes dans le domaine retenu. Modifiez les paramètres pour relancer la recherche.' if not best else '')
