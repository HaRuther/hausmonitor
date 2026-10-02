from __future__ import annotations
from math import sqrt
from statistics import mean, stdev

POINTS=("SW","SO","ANB","TSW","TSO")

def summary(values):
    if not values:return {"n":0,"mean":None,"sd":None,"se":None,"range":None}
    m=mean(values); sd=stdev(values) if len(values)>1 else None
    return {"n":len(values),"mean":m,"sd":sd,"se":sd/sqrt(len(values)) if sd is not None else None,"range":max(values)-min(values)}

def campaign_stats(grouped, baseline_house=None, baseline_terrace=None):
    out={p:summary(grouped.get(p,[])) for p in POINTS}
    def pair(a,b,baseline):
        aa,bb=out[a],out[b]; result={"value":None,"se":None,"delta":None,"snr":None,"quality":"unvollständig"}
        if aa["mean"] is None or bb["mean"] is None:return result
        value=bb["mean"]-aa["mean"]
        se=sqrt(aa["se"]**2+bb["se"]**2) if aa["se"] is not None and bb["se"] is not None else None
        delta=value-baseline if baseline is not None else None
        snr=abs(delta)/se if delta is not None and se and se>0 else None
        quality="Signal klar" if snr is not None and snr>=3 else "Hinweis" if snr is not None and snr>=2 else "im Rauschen" if snr is not None else "nicht bewertbar"
        return {"value":value,"se":se,"delta":delta,"snr":snr,"quality":quality}
    out["house"]=pair("SW","SO",baseline_house); out["terrace"]=pair("TSW","TSO",baseline_terrace)
    return out

def linear_regression(xs,ys):
    pairs=[(float(x),float(y)) for x,y in zip(xs,ys) if x is not None and y is not None]
    if len(pairs)<3:return None
    mx=mean(x for x,_ in pairs); my=mean(y for _,y in pairs)
    den=sum((x-mx)**2 for x,_ in pairs)
    if den==0:return None
    slope=sum((x-mx)*(y-my) for x,y in pairs)/den; intercept=my-slope*mx
    ss_tot=sum((y-my)**2 for _,y in pairs); ss_res=sum((y-(intercept+slope*x))**2 for x,y in pairs)
    r2=1-ss_res/ss_tot if ss_tot else None
    return {"n":len(pairs),"slope":slope,"intercept":intercept,"r2":r2}
