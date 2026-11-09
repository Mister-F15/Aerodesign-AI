/* Illustration potentielle indépendante des coefficients ML. */
(()=>{'use strict';
const el=id=>document.getElementById(id),canvas=el('flow-canvas'),ctx=canvas.getContext('2d');
if(!ctx){el('flow-status').textContent='Cette illustration nécessite un navigateur compatible avec Canvas.';return;}
const layer=document.createElement('canvas'),base=layer.getContext('2d'),cache=new Map();
let data=null,mode='speed',generation=0,desired=null,inflight=false,timer=null,width=800,height=400,dpr=1,particles=[],lastTime=0,frame=0;
let animate=!(globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
const palettes={speed:[[0,[65,111,157]],[.25,[132,198,196]],[.5,[234,243,226]],[.75,[242,201,117]],[1,[215,119,85]]],pressure:[[0,[52,99,154]],[.45,[130,194,199]],[.75,[234,243,226]],[1,[230,165,100]]]};
function color(t){const stops=palettes[mode];t=Math.max(0,Math.min(1,t));let k=1;while(k<stops.length-1&&t>stops[k][0])k++;const a=stops[k-1],b=stops[k],f=(t-a[0])/(b[0]-a[0]);return a[1].map((v,i)=>Math.round(v+(b[1][i]-v)*f));}
function legends(){
const speed=mode==='speed';el('flow-legend-name').textContent=speed?'Vitesse relative V/V∞':'Pression relative Cp';el('flow-legend-low').textContent=speed?'0 · ralenti':'≤ −3 · basse pression';el('flow-legend-mid').textContent=speed?'1 · air lointain':'0 · air lointain';el('flow-legend-high').textContent=speed?'≥ 2 · accéléré':'1 · haute pression';
el('flow-colorbar').style.background=speed?'linear-gradient(90deg,#416f9d,#84c6c4,#eaf3e2,#f2c975,#d77755)':'linear-gradient(90deg,#34639a,#82c2c7 45%,#eaf3e2 75%,#e6a564)';
for(const name of ['speed','pressure'])el('flow-'+name).setAttribute('aria-pressed',String(mode===name));
el('flow-motion').textContent=animate?'Mettre en pause':'Animer les particules';el('flow-motion').setAttribute('aria-pressed',String(animate));
}
function xy(p){const [xmin,xmax,ymin,ymax]=data.bounds;return [(p[0]-xmin)/(xmax-xmin)*width,(ymax-p[1])/(ymax-ymin)*height];}
function outline(context){context.beginPath();data.outline.forEach((p,i)=>{const q=xy(p);if(i)context.lineTo(...q);else context.moveTo(...q);});context.closePath();}
function paint(){
base.setTransform(dpr,0,0,dpr,0,0);base.clearRect(0,0,width,height);base.fillStyle='#f5f9f6';base.fillRect(0,0,width,height);
if(!data){ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,width,height);ctx.drawImage(layer,0,0,layer.width,layer.height,0,0,width,height);return;}
const {nx,ny,u,v}=data.grid,img=document.createElement('canvas');img.width=nx;img.height=ny;const ic=img.getContext('2d'),pixels=ic.createImageData(nx,ny);
for(let y=0;y<ny;y++)for(let x=0;x<nx;x++){const i=y*nx+x,j=((ny-1-y)*nx+x)*4;let rgb=[245,249,246];if(u[i]!==null&&v[i]!==null){const s2=u[i]*u[i]+v[i]*v[i];rgb=color(mode==='speed'?Math.sqrt(s2)/2:(1-s2+3)/4);}pixels.data.set([...rgb,255],j);}
ic.putImageData(pixels,0,0);base.imageSmoothingEnabled=true;base.drawImage(img,0,0,width,height);
if(el('flow-lines').checked){
base.strokeStyle='rgba(35,94,87,.48)';base.lineWidth=.9;
for(let k=0;k<data.streamlines.length;k++){const line=data.streamlines[k];base.beginPath();line.forEach((p,i)=>{const q=xy(p);if(i)base.lineTo(...q);else base.moveTo(...q);});base.stroke();
if(k%3===0&&line.length>40){const j=Math.floor(line.length*.61),q=xy(line[j]),next=xy(line[j+1]),angle=Math.atan2(next[1]-q[1],next[0]-q[0]);base.save();base.translate(...q);base.rotate(angle);base.fillStyle='rgba(35,94,87,.65)';base.beginPath();base.moveTo(3.5,0);base.lineTo(-3,-2.5);base.lineTo(-3,2.5);base.closePath();base.fill();base.restore();}}
}
base.save();base.shadowColor='rgba(15,53,44,.15)';base.shadowBlur=8;outline(base);const fill=base.createLinearGradient(0,height*.35,0,height*.65);fill.addColorStop(0,'#fcfef9');fill.addColorStop(1,'#ceded1');base.fillStyle=fill;base.fill();base.shadowBlur=0;base.strokeStyle='#244f49';base.lineWidth=1.8;base.stroke();base.restore();
base.font='11px Segoe UI, Arial, sans-serif';base.fillStyle='#496b64';base.fillText('x / corde',width-65,height-12);
for(const value of [0,.5,1]){const p=xy([value,data.bounds[2]]);base.fillText(String(value).replace('.',','),p[0]-3,height-12);}
base.save();base.translate(28,30);const a=Math.atan2(-data.freestream[1],data.freestream[0]);base.rotate(a);base.strokeStyle='#315e56';base.lineWidth=1.5;base.beginPath();base.moveTo(0,0);base.lineTo(40,0);base.lineTo(34,-4);base.moveTo(40,0);base.lineTo(34,4);base.stroke();base.restore();base.fillText('Air lointain',26,53);
ctx.setTransform(dpr,0,0,dpr,0,0);ctx.drawImage(layer,0,0,layer.width,layer.height,0,0,width,height);
}
function prepareParticles(){particles=[];if(!data)return;data.streamlines.forEach((line,k)=>{const distance=[0];for(let i=1;i<line.length;i++)distance.push(distance[i-1]+Math.hypot(line[i][0]-line[i-1][0],line[i][1]-line[i-1][1]));const length=distance.at(-1);if(length<.1)return;for(let p=0;p<2;p++)particles.push({line,distance,length,s:((k*.173+p*.5)%1)*length,index:0});});}
function tick(now){frame=0;if(!data||!animate||document.hidden){lastTime=0;return;}const dt=lastTime?Math.min(.045,(now-lastTime)/1000):0;lastTime=now;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.drawImage(layer,0,0,layer.width,layer.height,0,0,width,height);ctx.fillStyle='rgba(26,85,75,.82)';
for(const p of particles){let i=p.index;while(i<p.line.length-2&&p.distance[i+1]<p.s)i++;const speed=p.line[i][2];p.s+=dt*.15*speed;if(p.s>=p.length){p.s=0;i=0;}while(i<p.line.length-2&&p.distance[i+1]<p.s)i++;p.index=i;const f=(p.s-p.distance[i])/(p.distance[i+1]-p.distance[i]||1);const q=xy([p.line[i][0]+f*(p.line[i+1][0]-p.line[i][0]),p.line[i][1]+f*(p.line[i+1][1]-p.line[i][1])]);ctx.beginPath();ctx.arc(...q,1.6,0,Math.PI*2);ctx.fill();}
frame=requestAnimationFrame(tick);}
function run(){if(frame)cancelAnimationFrame(frame);frame=0;lastTime=0;if(data&&animate&&!document.hidden&&!document.getElementById('explorer-view')?.hidden&&!document.getElementById('studio-flow-view')?.hidden)frame=requestAnimationFrame(tick);}
function resize(){width=Math.max(240,canvas.getBoundingClientRect().width||800);height=width*(data?(data.bounds[3]-data.bounds[2])/(data.bounds[1]-data.bounds[0]):1.04/2.1);dpr=Math.min(2,globalThis.devicePixelRatio||1);canvas.width=layer.width=Math.round(width*dpr);canvas.height=layer.height=Math.round(height*dpr);paint();run();}
function display(value,snapshot){data=value;prepareParticles();canvas.dataset.ready='true';canvas.dataset.naca=value.naca;canvas.dataset.alpha=String(value.alpha_deg);el('flow-overlay').hidden=true;el('flow-status').textContent=`NACA ${value.naca} · incidence ${String(value.alpha_deg).replace('.',',')}° · air horizontal · illustration prête`;
canvas.setAttribute('aria-label',`Lignes de courant et champ normalisé autour du NACA ${value.naca} à ${value.alpha_deg} degrés. Écoulement potentiel sans viscosité.`);resize();}
async function pump(){if(inflight||!desired)return;const snapshot=desired;desired=null;const token=generation,key=snapshot.geometry.code+'|'+snapshot.conditions.alpha_deg;if(cache.has(key)){if(token===generation)display(cache.get(key),snapshot);return;}inflight=true;
try{const response=await fetch('/api/flow?'+new URLSearchParams({naca:snapshot.geometry.code,alpha:snapshot.conditions.alpha_deg}));const value=await response.json();if(!response.ok)throw new Error(value.error||'Illustration indisponible.');cache.set(key,value);if(cache.size>8)cache.delete(cache.keys().next().value);if(token===generation)display(value,snapshot);}
catch(error){if(token===generation){el('flow-overlay').hidden=false;el('flow-overlay').textContent='Illustration indisponible';el('flow-status').textContent=error.message;}}
finally{inflight=false;if(desired)pump();}}
function clear(text='Actualisation de l’illustration…'){generation++;desired=null;clearTimeout(timer);data=null;canvas.dataset.ready='false';delete canvas.dataset.naca;delete canvas.dataset.alpha;el('flow-overlay').hidden=false;el('flow-overlay').textContent=text;el('flow-status').textContent=text;paint();run();}
function update(snapshot){const g=snapshot.geometry;if(g.m>.08||g.t<.06||g.t>.30||(g.m>0&&(g.p<.1||g.p>.8))){clear('Profil hors du domaine de visualisation.\nCambrure : 0 à 8 % · position : 10 à 80 % · épaisseur : 6 à 30 %.');return;}if(snapshot.conditions.alpha_deg< -4||snapshot.conditions.alpha_deg>8){clear('Incidence hors du domaine de visualisation : −4 à 8°.');return;}desired=snapshot;el('flow-overlay').textContent='Calcul de l’écoulement simplifié…';el('flow-status').textContent='Calcul de l’écoulement simplifié…';clearTimeout(timer);timer=setTimeout(pump,350);}
for(const name of ['speed','pressure'])el('flow-'+name).addEventListener('click',()=>{mode=name;legends();paint();run();});el('flow-lines').addEventListener('change',()=>{paint();run();});el('flow-motion').addEventListener('click',()=>{animate=!animate;legends();paint();run();});document.addEventListener('visibilitychange',run);
if(globalThis.ResizeObserver)new ResizeObserver(resize).observe(canvas);else globalThis.addEventListener('resize',resize);
globalThis.AeroFlow={clear,update,setVisible(visible){if(visible)resize();else{if(frame)cancelAnimationFrame(frame);frame=0;}}};legends();resize();
})();
