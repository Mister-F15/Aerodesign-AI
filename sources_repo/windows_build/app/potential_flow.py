"""Illustration indépendante : Hess-Smith 2D, sources et vortex constants.

Grandeurs normalisées à U_inf=1, corde=1. Écoulement incompressible non
visqueux, stationnaire ; aucune couche limite, traînée ou donnée ML ajustée.
"""
from functools import lru_cache
import math,time,threading
import numpy as np
from threadpoolctl import threadpool_limits

LOCK=threading.Lock()
def contour(code,side=48):
    m,p,t=int(code[0])/100,int(code[1])/10,int(code[2:])/100
    x=(1-np.cos(np.linspace(0,np.pi,side+1)))/2
    yt=5*t*(.2969*np.sqrt(x)-.126*x-.3516*x*x+.2843*x**3-.1015*x**4)
    if m==0:yc=x*0;slope=x*0
    else:
        yc=np.where(x<p,m/p**2*(2*p*x-x*x),m/(1-p)**2*((1-2*p)+2*p*x-x*x))
        slope=np.where(x<p,2*m/p**2*(p-x),2*m/(1-p)**2*(p-x))
    angle=np.arctan(slope);upper=np.column_stack((x-yt*np.sin(angle),yc+yt*np.cos(angle)));lower=np.column_stack((x+yt*np.sin(angle),yc-yt*np.cos(angle)))
    return np.vstack((upper[::-1],lower[1:],upper[-1:]))
def inside(points,polygon):
    points=np.atleast_2d(points);x,y=points[:,0,None],points[:,1,None];a,b=polygon[:-1],polygon[1:];dy=b[:,1]-a[:,1];safe=np.where(abs(dy)>1e-15,dy,1.)
    cross=((a[:,1]>y)!=(b[:,1]>y))&(x<(b[:,0]-a[:,0])*(y-a[:,1])/safe+a[:,0])
    return np.logical_xor.reduce(cross,axis=1)

def crossing_body(starts,ends,polygon):
    """Détecter un segment traversant la paroi, même entre deux points extérieurs."""
    a=np.atleast_2d(starts);r=np.atleast_2d(ends)-a;q=polygon[:-1];s=np.diff(polygon,axis=0)
    def cross(x,y):return x[...,0]*y[...,1]-x[...,1]*y[...,0]
    offset=q[None,:,:]-a[:,None,:];denom=cross(r[:,None,:],s[None,:,:]);safe=np.where(abs(denom)>1e-15,denom,1.)
    t=cross(offset,s[None,:,:])/safe;u=cross(offset,r[:,None,:])/safe
    return np.any((abs(denom)>1e-15)&(t>1e-10)&(t<1+1e-10)&(u>=-1e-10)&(u<=1+1e-10),axis=1)

class PanelFlow:
    def __init__(self,code,alpha,side=48):
        self.polygon=contour(code,side);validate_contour(self.polygon);self.starts=self.polygon[:-1];delta=np.diff(self.polygon,axis=0);self.length=np.linalg.norm(delta,axis=1);self.tangent=delta/self.length[:,None];self.left=np.column_stack((-self.tangent[:,1],self.tangent[:,0]));self.normal=-self.left;self.mid=(self.polygon[:-1]+self.polygon[1:])/2
        a=math.radians(alpha);self.freestream=np.array([math.cos(a),math.sin(a)])
        source,vortex=self.influence(self.mid)
        for i in range(len(self.length)):source[i,i]=.5*self.normal[i];vortex[i,i]=.5*self.tangent[i]
        n=len(self.length);A=np.zeros((n+1,n+1));A[:-1,:-1]=np.einsum('ijk,ik->ij',source,self.normal);A[:-1,-1]=np.einsum('ik,ik->i',vortex.sum(axis=1),self.normal)
        # Le dernier panneau est la petite fermeture du bord de fuite ouvert.
        top,bottom=0,n-2
        A[-1,:-1]=source[top]@self.tangent[top]+source[bottom]@self.tangent[bottom];A[-1,-1]=vortex[top].sum(axis=0)@self.tangent[top]+vortex[bottom].sum(axis=0)@self.tangent[bottom]
        rhs=np.r_[-self.normal@self.freestream,-self.freestream@(self.tangent[top]+self.tangent[bottom])]
        solution=np.linalg.solve(A,rhs);self.sigma=solution[:-1];self.gamma=solution[-1];self.residual=float(np.max(abs(A@solution-rhs)))
        if not np.isfinite(solution).all() or self.residual>1e-7:raise ValueError('Illustration indisponible pour cette géométrie.')
        self.wall_velocity=self.freestream+np.einsum('ijk,j->ik',source,self.sigma)+vortex.sum(axis=1)*self.gamma
        self.wall_cp=1-np.sum(self.wall_velocity**2,axis=1)
    def influence(self,points):
        d=np.asarray(points)[:,None,:]-self.starts[None,:,:];xi=np.einsum('ijk,jk->ij',d,self.tangent);eta=np.einsum('ijk,jk->ij',d,self.left)
        r0=np.maximum(xi*xi+eta*eta,1e-24);r1=np.maximum((xi-self.length)**2+eta*eta,1e-24)
        u=np.log(r0/r1)/(4*np.pi);angle=np.arctan2(eta,xi-self.length)-np.arctan2(eta,xi);angle=(angle+np.pi)%(2*np.pi)-np.pi;v=angle/(2*np.pi)
        source=u[:,:,None]*self.tangent+v[:,:,None]*self.left;vortex=-v[:,:,None]*self.tangent+u[:,:,None]*self.left
        return source,vortex
    def velocity(self,points):
        source,vortex=self.influence(np.atleast_2d(points));return self.freestream+np.einsum('ijk,j->ik',source,self.sigma)+vortex.sum(axis=1)*self.gamma
    def streamlines(self,bounds,seeds=37,step=.006):
        xmin,xmax,ymin,ymax=bounds;points=np.column_stack((np.full(seeds,xmin+.006),np.linspace(ymin+.025,ymax-.025,seeds)));paths=[[] for _ in range(seeds)];active=np.ones(seeds,dtype=bool)
        for _ in range(490):
            ids=np.flatnonzero(active)
            if not len(ids):break
            p=points[ids];v=self.velocity(p);speed=np.linalg.norm(v,axis=1);valid=np.isfinite(v).all(axis=1)&(speed>1e-5)&(speed<12)&~inside(p,self.polygon)
            for j,k in enumerate(ids):
                if valid[j]:paths[k].append([round(float(p[j,0]),5),round(float(p[j,1]),5),round(float(speed[j]),4)])
            active[ids[~valid]]=False;ids=ids[valid];p=p[valid];v=v[valid];speed=speed[valid]
            if not len(ids):continue
            # RK2 avec longueur de pas bornée : pas de saut à travers le profil.
            mid=p+.5*step*v/speed[:,None];vm=self.velocity(mid);sm=np.linalg.norm(vm,axis=1);nxt=p+step*vm/np.maximum(sm[:,None],1e-8)
            # Contrôler aussi le segment réellement affiché après arrondi.
            rendered=np.round(nxt,5);rendered_poly=np.round(self.polygon,6)
            good=np.isfinite(nxt).all(axis=1)&~inside(mid,self.polygon)&~inside(nxt,self.polygon)&~inside(rendered,rendered_poly)&~crossing_body(np.round(p,5),rendered,rendered_poly)&(nxt[:,0]>xmin)&(nxt[:,0]<xmax)&(nxt[:,1]>ymin)&(nxt[:,1]<ymax)
            points[ids[good]]=nxt[good];active[ids[~good]]=False
        return [p for p in paths if len(p)>4]

class HorizontalFlow:
    """Solution dans le repère de l'air : profil tourné autour du quart de corde."""
    def __init__(self,flow,alpha):
        self.flow=flow;self.pivot=np.array([.25,0.]);a=math.radians(alpha)
        self.rotation=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
        self.polygon=(flow.polygon-self.pivot)@self.rotation+self.pivot
    def velocity(self,points):
        local=(np.atleast_2d(points)-self.pivot)@self.rotation.T+self.pivot
        return self.flow.velocity(local)@self.rotation
    streamlines=PanelFlow.streamlines

def validate_contour(poly):
    # Refuser les contours croisés : aucune solution potentielle exploitable.
    a=poly[:-1];b=poly[1:];d=b-a;n=len(a)
    def cross(x,y):return x[...,0]*y[...,1]-x[...,1]*y[...,0]
    ab=cross(d[:,None,:],a[None,:,:]-a[:,None,:]);bb=cross(d[:,None,:],b[None,:,:]-a[:,None,:])
    ba=cross(d[None,:,:],a[:,None,:]-a[None,:,:]);cb=cross(d[None,:,:],b[:,None,:]-a[None,:,:])
    adjacent=np.eye(n,dtype=bool)|np.eye(n,k=1,dtype=bool)|np.eye(n,k=-1,dtype=bool);adjacent[0,-1]=adjacent[-1,0]=True
    if np.any((ab*bb < -1e-20)&(ba*cb < -1e-20)&~adjacent):raise ValueError('Ce NACA produit un contour qui se croise : représentation physique impossible.')
    if np.min(np.linalg.norm(d,axis=1))<1e-10:raise ValueError('Contour dégénéré : épaisseur ou position de cambrure invalide.')

def validate(code,alpha):
    if len(code)!=4 or not code.isascii() or not code.isdigit():raise ValueError('Code NACA invalide.')
    m,p,t=int(code[0]),int(code[1]),int(code[2:])
    if not (0<=m<=8 and 6<=t<=30 and ((m==0 and p==0) or (m>0 and 1<=p<=8))):raise ValueError('Illustration limitée à une cambrure de 8 %, une position de 10 à 80 % et une épaisseur de 6 à 30 %.')
    if not math.isfinite(alpha) or not -4<=alpha<=8:raise ValueError('Incidence hors de la plage −4° à 8°.')

@lru_cache(maxsize=12)
def _compute(code,alpha):
    tic=time.perf_counter();body_flow=PanelFlow(code,alpha);flow=HorizontalFlow(body_flow,alpha);bounds=(-.48,1.62,-.52,.52);nx,ny=190,96;xs=np.linspace(bounds[0],bounds[1],nx);ys=np.linspace(bounds[2],bounds[3],ny);xx,yy=np.meshgrid(xs,ys);points=np.column_stack((xx.ravel(),yy.ravel()));mask=inside(points,flow.polygon);velocity=flow.velocity(points);valid=~mask&np.isfinite(velocity).all(axis=1)
    speed=np.linalg.norm(velocity,axis=1);valid&=speed<12
    u=[round(float(v),4) if ok else None for v,ok in zip(velocity[:,0],valid)];v=[round(float(v),4) if ok else None for v,ok in zip(velocity[:,1],valid)]
    lines=flow.streamlines(bounds)
    return dict(model='potential_hess_smith_v1',view_frame='horizontal_freestream',profile_rotation_deg=-alpha,rotation_center=[.25,0],naca=code,alpha_deg=alpha,normalized=True,depends_on_Re=False,viscous=False,CL_CD_from_this_field=False,bounds=bounds,grid=dict(nx=nx,ny=ny,u=u,v=v),outline=np.round(flow.polygon,6).tolist(),streamlines=lines,freestream=[1.,0.],panel_count=len(body_flow.length),boundary_residual=body_flow.residual,elapsed_s=round(time.perf_counter()-tic,3))
def compute(code,alpha):
    alpha=float(alpha);validate(code,alpha)
    with LOCK,threadpool_limits(limits=2):return _compute(code,round(alpha,3))
