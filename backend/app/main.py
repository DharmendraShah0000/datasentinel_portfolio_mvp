from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, String, Integer, Float, DateTime, Text, func
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session, Mapped, mapped_column
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd, numpy as np, io, json, os
from pydantic import BaseModel, Field

DATABASE_URL=os.getenv("DATABASE_URL","sqlite:///./datasentinel.db")
engine=create_engine(DATABASE_URL, connect_args={"check_same_thread":False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal=sessionmaker(bind=engine, autoflush=False, autocommit=False)
class Base(DeclarativeBase): pass
class Dataset(Base):
    __tablename__="datasets"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    name: Mapped[str]=mapped_column(String(255),index=True)
    rows: Mapped[int]=mapped_column(Integer)
    columns: Mapped[int]=mapped_column(Integer)
    quality_score: Mapped[float]=mapped_column(Float)
    profile_json: Mapped[str]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
Base.metadata.create_all(engine)
app=FastAPI(title="DataSentinel API",version="0.1.0",description="Data quality, profiling and anomaly analytics.")
app.add_middleware(CORSMiddleware,allow_origins=os.getenv("CORS_ORIGINS","http://localhost:3000").split(","),allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
def db():
    s=SessionLocal()
    try: yield s
    finally: s.close()
class DatasetOut(BaseModel):
    id:int; name:str; rows:int; columns:int; quality_score:float; profile:dict; created_at:datetime
def output(d): return {"id":d.id,"name":d.name,"rows":d.rows,"columns":d.columns,"quality_score":d.quality_score,"profile":json.loads(d.profile_json),"created_at":d.created_at}
@app.get("/health")
def health(): return {"status":"ok","service":"datasentinel-api"}
@app.get("/api/datasets")
def list_datasets(s:Session=Depends(db)):
    return [output(d) for d in s.query(Dataset).order_by(Dataset.id.desc()).all()]
@app.post("/api/datasets/upload")
async def upload(file:UploadFile=File(...),s:Session=Depends(db)):
    if not file.filename.lower().endswith(".csv"): raise HTTPException(400,"Upload a CSV file.")
    raw=await file.read()
    if len(raw)>15_000_000: raise HTTPException(413,"CSV must be smaller than 15 MB.")
    try: df=pd.read_csv(io.BytesIO(raw))
    except Exception as e: raise HTTPException(400,f"Could not parse CSV: {e}")
    if df.empty or len(df.columns)==0: raise HTTPException(400,"Dataset is empty.")
    if len(df)>500_000: raise HTTPException(400,"Maximum supported rows: 500,000.")
    total_cells=max(1,df.shape[0]*df.shape[1]); missing=int(df.isna().sum().sum()); duplicate=int(df.duplicated().sum())
    completeness=1-missing/total_cells; uniqueness=1-duplicate/max(1,len(df))
    score=round(max(0,min(100,100*(.75*completeness+.25*uniqueness))),2)
    profile={"missing_cells":missing,"duplicate_rows":duplicate,"completeness_pct":round(100*completeness,2),"columns":[],"numeric_summary":{},"anomalies":[]}
    for col in df.columns:
        series=df[col]
        item={"name":str(col),"dtype":str(series.dtype),"missing":int(series.isna().sum()),"distinct":int(series.nunique(dropna=True))}
        profile["columns"].append(item)
        if pd.api.types.is_numeric_dtype(series):
            vals=series.dropna()
            if len(vals):
                q1,q3=vals.quantile(.25),vals.quantile(.75); iqr=q3-q1
                outliers=vals[(vals<q1-1.5*iqr)|(vals>q3+1.5*iqr)]
                profile["numeric_summary"][str(col)]={"mean":round(float(vals.mean()),4),"median":round(float(vals.median()),4),"std":round(float(vals.std(ddof=0)),4),"min":float(vals.min()),"max":float(vals.max()),"outlier_count":int(len(outliers))}
                if len(outliers): profile["anomalies"].append({"column":str(col),"type":"IQR outliers","count":int(len(outliers)),"method":"1.5 × IQR"})
    d=Dataset(name=file.filename,rows=len(df),columns=len(df.columns),quality_score=score,profile_json=json.dumps(profile))
    s.add(d);s.commit();s.refresh(d)
    return output(d)
@app.get("/api/datasets/{dataset_id}")
def get_dataset(dataset_id:int,s:Session=Depends(db)):
    d=s.get(Dataset,dataset_id)
    if not d: raise HTTPException(404,"Dataset not found")
    return output(d)
@app.delete("/api/datasets/{dataset_id}")
def delete_dataset(dataset_id:int,s:Session=Depends(db)):
    d=s.get(Dataset,dataset_id)
    if not d: raise HTTPException(404,"Dataset not found")
    s.delete(d);s.commit();return {"deleted":dataset_id}
@app.get("/api/analytics/overview")
def overview(s:Session=Depends(db)):
    ds=s.query(Dataset).all()
    return {"dataset_count":len(ds),"total_rows":sum(d.rows for d in ds),"avg_quality":round(sum(d.quality_score for d in ds)/len(ds),2) if ds else 0,"datasets":[{"name":d.name,"rows":d.rows,"quality_score":d.quality_score,"created_at":d.created_at.isoformat()} for d in ds]}
