'use strict';
const $=id=>document.getElementById(id);
const form=$('case-form'),naca=$('naca'),alpha=$('alpha'),re=$('re');
let timer,requestId=0,controller;
const number=(v,d=2)=>new Intl.NumberFormat('fr-FR',{minimumFractionDigits:d,maximumFractionDigits:d}).format(v);
let shapeDomain={m:[0,.06],p_cambered:[.1,.7],t:[.06,.30]},lastCamberPosition=4;
const shapeFields=[{key:'m',min:0,max:9,domain:'m',factor:100,display:1},{key:'p',min:1,max:9,domain:'p_cambered',factor:10,display:10},{key:'t',min:1,max:99,domain:'t',factor:100,display:1}];
function syncShapeControls(){
  const code=naca.value.replace(/\s+/g,'').toUpperCase().replace(/^NACA/,'');
  const valid=/^[0-9]{4}$/.test(code)&&Number(code.slice(2))>0&&(code[0]==='0'?code[1]==='0':code[1]!=='0');
  if(!valid){
    for(const f of shapeFields){$('shape-'+f.key+'-row').setAttribute('data-state','unknown');$('shape-'+f.key+'-value').textContent='—';$('shape-'+f.key+'-status').textContent='Code NACA incomplet ou invalide.';$('shape-'+f.key).disabled=false;$('shape-'+f.key).style.background='#dce3de';$('shape-'+f.key).setAttribute('aria-invalid','false');$('shape-'+f.key).setAttribute('aria-valuetext','Code NACA incomplet ou invalide. Déplacez ce curseur pour créer un profil.');}
    $('sliders-help').textContent='Complétez le code NACA ou déplacez un curseur pour créer un profil valide.';return;
  }
  const values={m:Number(code[0]),p:Number(code[1]),t:Number(code.slice(2))};
  if(values.m>0)lastCamberPosition=values.p;
  $('shape-m').value=String(values.m);$('shape-p').value=String(values.m===0?lastCamberPosition:values.p);$('shape-t').value=String(values.t);
  $('sliders-help').textContent='Les curseurs et le code NACA se mettent à jour ensemble.';
  for(const f of shapeFields){
    const input=$('shape-'+f.key),row=$('shape-'+f.key+'-row'),output=$('shape-'+f.key+'-value'),status=$('shape-'+f.key+'-status'),inactive=f.key==='p'&&values.m===0;
    const limits=shapeDomain[f.domain],low=limits[0]*f.factor,high=limits[1]*f.factor,v=values[f.key],outside=!inactive&&(v<low-1e-8||v>high+1e-8);
    input.disabled=inactive;row.setAttribute('data-state',inactive?'inactive':outside?'outside':'inside');input.setAttribute('aria-invalid',String(outside));
    output.textContent=inactive?'Sans objet':number(v*f.display,0)+' %';
    const bounds=number(low*f.display,0)+' à '+number(high*f.display,0)+' %';
    status.textContent=inactive?'Sans objet pour un profil symétrique.':outside?'Hors domaine ML : plage autorisée '+bounds+'.':'Domaine des coefficients : '+bounds+'.';
    input.setAttribute('aria-valuetext',inactive?'Sans objet pour un profil symétrique':output.textContent+(outside?', hors du domaine des coefficients':''));
    const a=100*(low-f.min)/(f.max-f.min),b=100*(high-f.min)/(f.max-f.min);
    input.style.background=inactive?'#dce3de':`linear-gradient(90deg,#e8b2a6 0%,#e8b2a6 ${a}%,#78b29a ${a}%,#78b29a ${b}%,#e8b2a6 ${b}%,#e8b2a6 100%)`;
  }
}
function shapeControlChanged(){
  const m=Number($('shape-m').value),p=Number($('shape-p').value)||lastCamberPosition,t=Number($('shape-t').value);
  if(m>0)lastCamberPosition=p;
  naca.value=(m===0?'00':String(m)+String(p))+String(t).padStart(2,'0');syncShapeControls();schedule();
}
function clearResults(status){for(const key of ['cl','cd','finesse'])$(key).textContent='—';$('result-status').textContent=status;}
function message(text,tone='info'){$('message').hidden=!text;$('message').textContent=text;$('message').setAttribute('data-tone',tone);}
function domainNotice(state,title,detail){$('domain-banner').setAttribute('data-state',state);$('domain-title').textContent=title;$('domain-detail').textContent=detail;$('metrics').setAttribute('data-available',String(state==='inside'));}
function explainDomain(data){
  const g=data.geometry,d=data.coverage||{m:[0,.06],p_cambered:[.1,.7],t:[.06,.30]},issues=[];
  if(g.m<d.m[0]||g.m>d.m[1])issues.push('Cambrure : '+number(g.m*100,0)+' % ; maximum autorisé : '+number(d.m[1]*100,0)+' %.');
  if(g.m>0&&(g.p<d.p_cambered[0]||g.p>d.p_cambered[1]))issues.push('Position de cambrure : '+number(g.p*100,0)+' % ; plage autorisée : '+number(d.p_cambered[0]*100,0)+' à '+number(d.p_cambered[1]*100,0)+' %.');
  if(g.t<d.t[0]||g.t>d.t[1])issues.push('Épaisseur : '+number(g.t*100,0)+' % ; plage autorisée : '+number(d.t[0]*100,0)+' à '+number(d.t[1]*100,0)+' %.');
  if(data.available){domainNotice('inside','Profil dans le domaine d’étude','La géométrie et les conditions choisies permettent d’estimer CL et CD.');return;}
  const flowOK=g.m<=.08&&g.t>=.06&&g.t<=.30&&(g.m===0||(g.p>=.1&&g.p<=.8));
  if(issues.length){domainNotice('outside','Profil hors du domaine d’étude',issues.join(' ')+' Aucun coefficient n’est affiché.'+(flowOK?' L’illustration de l’écoulement reste disponible, mais ne valide pas ces performances.':' Ce profil dépasse également les limites de la visualisation.'));return;}
  const a=data.conditions.alpha_deg,r=data.conditions.Re;
  if(a< -4||a>8||Math.abs(a*2-Math.round(a*2))>1e-8||![1000000,2000000,3000000].includes(r)){domainNotice('outside','Conditions hors du domaine d’étude','Choisissez une incidence de −4 à 8° par pas de 0,5° et un Reynolds de 1, 2 ou 3 millions. Aucun coefficient n’est affiché.');return;}
  domainNotice('outside','Ce cas est exclu du domaine d’étude',(data.reasons.length?data.reasons.join(' ')+' ':'')+'Les vérifications disponibles sont insuffisantes pour autoriser une estimation fiable dans ces conditions. Aucun coefficient n’est affiché.');
}
function explainPrediction(data){
  if(!data.available){message('');return;}
  if(data.numerical_warning){message('Les calculs de référence XFOIL n’ont pas été suffisamment stables pour confirmer cette estimation.','warning');return;}
  if(data.extension_prediction){const cd=data.accuracy_context?.metrics?.CD;message('Ce profil plus épais utilise le modèle complémentaire.'+(cd?' Sur '+cd.profiles+' profils de contrôle ('+cd.cases+' cas), l’écart moyen de CD par rapport à XFOIL est de '+number(cd.mean,1)+' %. Ce chiffre ne donne pas l’erreur de ce cas précis.':''));return;}
  message(data.geometry_in_training?'Le modèle a appris à partir de calculs réalisés sur ce profil. Les coefficients affichés restent des estimations.':data.geometry_in_dataset?'Ce profil a servi à contrôler le modèle, sans être utilisé pour son apprentissage. Les coefficients affichés sont estimés pour les conditions choisies.':'Nouveau profil pour le modèle : ses coefficients sont estimés à partir des formes apprises. La précision peut varier selon la géométrie et les conditions choisies.');
}
function draw(g){
  const angle=Number(alpha.value),radians=angle*Math.PI/180,cos=Math.cos(radians),sin=Math.sin(radians);
  const rotate=([x,y])=>[.25+(x-.25)*cos+y*sin,-(x-.25)*sin+y*cos];
  const ys=[...g.upper,...g.lower].map(rotate).map(point=>point[1]);
  const low=Math.min(...ys),high=Math.max(...ys);
  const scale=Math.min(820,190/(high-low)),x0=(1000-scale)/2,y0=160+(high+low)*scale/2;
  const xy=point=>{const [x,y]=rotate(point);return `${(x0+x*scale).toFixed(3)},${(y0-y*scale).toFixed(3)}`;};
  const path=points=>'M'+points.map(xy).join(' L');
  // Seules des valeurs numériques validées par le serveur sont injectées dans le SVG.
  $('drawing').innerHTML=`<path d="M${xy([0,0])} L${xy([1,0])}" fill="none" stroke="#aabcb0" stroke-width="1" stroke-dasharray="4 5"/><path d="${path(g.upper)} L${g.lower.slice().reverse().map(xy).join(' L')} Z" fill="url(#foil-fill)" stroke="#20796b" stroke-width="2.4" stroke-linejoin="round"/><path d="${path(g.mean)}" fill="none" stroke="#b28a47" stroke-width="1.5" stroke-dasharray="7 6"/><line x1="${x0}" y1="272" x2="${x0+scale}" y2="272" stroke="#c8d6cb"/><line x1="${x0}" y1="267" x2="${x0}" y2="277" stroke="#a8bdb0"/><line x1="${x0+scale}" y1="267" x2="${x0+scale}" y2="277" stroke="#a8bdb0"/><text x="${x0}" y="300">0</text><text x="${x0+scale}" y="300" text-anchor="end">1 corde</text><text x="500" y="320" text-anchor="middle">Échelle de longueur</text>`;
  $('drawing').setAttribute('data-profile-angle',String(angle));
  $('profile-title').textContent=g.profile;$('profile-plot').setAttribute('aria-label',`Contour du profil ${g.profile}, épaisseur ${number(g.t*100,0)} %, corde normalisée, incidence ${angle} degrés`);
  $('decoded-profile').textContent=g.profile;
  $('digit-m').textContent=g.code[0];$('digit-p').textContent=g.code[1];$('digit-t').textContent=g.code.slice(2);
  $('decoded-m').textContent=g.m===0?'0 % de la corde : profil symétrique.':number(g.m*100,0)+' % de la corde : hauteur maximale de la ligne moyenne.';
  $('decoded-p').textContent=g.m===0?'Sans objet quand la cambrure est nulle.':number(g.p*100,0)+' % de la corde depuis le bord d’attaque.';
  $('decoded-t').textContent=number(g.t*100,0)+' % de la corde : épaisseur totale maximale.';
  $('shape-kind').textContent=g.m===0?'Symétrique':'Cambré';$('camber').textContent=number(g.m*100,0)+' %';$('camber-position').textContent=g.m===0?'Sans objet':number(g.p*100,0)+' % de corde';$('thickness').textContent=number(g.t*100,0)+' %';
}
async function evaluate(){
  syncShapeControls();
  clearTimeout(timer);const id=++requestId;if(controller)controller.abort();controller=new AbortController();
  clearResults('Actualisation…');domainNotice('checking','Vérification du domaine…','');message('');globalThis.AeroFlow?.clear();
  try{
    const query=new URLSearchParams({naca:naca.value,alpha:alpha.value,re:re.value});
    const response=await fetch('/api/evaluate?'+query,{signal:controller.signal});const data=await response.json();if(id!==requestId)return;
    if(!response.ok)throw new Error(data.error||'Le calcul n’a pas pu aboutir.');
    if(data.coverage)shapeDomain=data.coverage;syncShapeControls();
    draw(data.geometry);globalThis.AeroFlow?.update(data);
    for(const button of document.querySelectorAll('[data-naca]'))button.classList.toggle('selected',button.dataset.naca===data.geometry.code);
    explainDomain(data);
    if(data.available){$('cl').textContent=number(data.prediction.CL,4);$('cd').textContent=number(data.prediction.CD,5);$('finesse').textContent=number(data.prediction.finesse,2);$('result-status').textContent='Estimation disponible';}
    else{clearResults('Coefficients indisponibles');}explainPrediction(data);
  }catch(error){if(error.name==='AbortError'||id!==requestId)return;globalThis.AeroFlow?.clear('Corrigez la saisie pour afficher l’écoulement.');clearResults('Coefficients indisponibles');domainNotice('outside',error instanceof TypeError?'Connexion à l’application interrompue':'Saisie à corriger',error instanceof TypeError?'Les coefficients ne peuvent pas être actualisés.':error.message);message('');$('drawing').innerHTML='';$('profile-title').textContent='Profil à corriger';$('shape-kind').textContent='Saisie invalide';$('decoded-profile').textContent='Saisie invalide';for(const key of ['digit-m','digit-p','digit-t','decoded-m','decoded-p','decoded-t'])$(key).textContent='—';for(const key of ['camber','camber-position','thickness'])$(key).textContent='—';}
}
function schedule(){domainNotice('checking','Vérification du domaine…','');message('');globalThis.AeroFlow?.clear();clearTimeout(timer);requestId++;if(controller)controller.abort();clearResults('Actualisation…');$('alpha-value').textContent=number(Number(alpha.value),Number(alpha.value)%1?1:0)+'°';timer=setTimeout(evaluate,180);}
naca.addEventListener('input',()=>{syncShapeControls();schedule();});
for(const input of [alpha,re])input.addEventListener('input',schedule);
for(const f of shapeFields)$('shape-'+f.key).addEventListener('input',shapeControlChanged);
for(const button of document.querySelectorAll('[data-naca]'))button.addEventListener('click',()=>{naca.value=button.dataset.naca;evaluate();});
form.addEventListener('submit',event=>{event.preventDefault();evaluate();});
globalThis.AeroExplorer={open(code,conditions){naca.value=code;alpha.value=conditions.alpha_deg;re.value=conditions.Re;syncShapeControls();schedule();}};

evaluate();
