"""ReefAhead research decision-support API. Run locally; no automatic alerts."""
from pathlib import Path
from datetime import date, datetime
from zoneinfo import ZoneInfo
import csv, io, json, os
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("CLIMATE_DATA_DIR", str(ROOT / "data")))
app = FastAPI(title="ReefAhead", version="2.0.0",
 description="Research prototype: fixed-pixel satellite heat-stress forecasts, not observed bleaching.")
app.mount("/assets", StaticFiles(directory=ROOT/"web/assets"), name="assets")

def daily():
    p=DATA/"processed/daily.csv"
    if not p.exists(): raise HTTPException(503,"Validated public data have not been prepared.")
    df=pd.read_csv(p)
    df["date"]=pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return df

@app.get("/")
def index():
    return FileResponse(ROOT/"web/index.html")

@app.get("/health")
def health():
    return {"status":"ok","data_ready":(DATA/"processed/daily.csv").exists(),
            "mode":"research-only","version":"2.0.0"}

@app.get("/api/sites")
def sites():
    df=daily()
    records=[]
    for name,g in df.groupby("site_id"):
        if "sabah" in str(name).lower(): continue
        records.append({"site_id":str(name),"latitude":float(g.latitude.iloc[0]),
            "longitude":float(g.longitude.iloc[0]),"first_date":g.date.min(),"last_date":g.date.max(),
            "n_days":len(g)})
    return records

@app.get("/api/forecast")
def forecast(site_id:str=Query(...,max_length=80),as_of:str|None=None):
    df=daily()
    site=df[df.site_id==site_id]
    if site.empty: raise HTTPException(404,"Unknown satellite pixel")
    if as_of:
        try: date.fromisoformat(as_of)
        except ValueError: raise HTTPException(422,"as_of must be YYYY-MM-DD")
        if as_of>site.date.max(): raise HTTPException(422,"No observations for requested future date")
    try:
        from src.predict import predict_forecast
        result=predict_forecast(site_id,as_of,data_path=DATA/"processed/daily.csv")
    except (ValueError,KeyError,FileNotFoundError) as e:
        raise HTTPException(422,str(e))
    except ImportError:
        raise HTTPException(503,"Forecast model has not been built.")
    issue=result.get("issue_date",result.get("date",as_of or site.date.max()))
    result["issue_date"]=str(issue)[:10]
    history=site[site.date<=result["issue_date"]].tail(120)
    result["history"]=json.loads(history[["date","sst","hotspot","dhw"]].to_json(orient="records"))
    result["coordinates"]={"latitude":float(site.latitude.iloc[0]),"longitude":float(site.longitude.iloc[0])}
    result["age_days"]=(datetime.now(ZoneInfo("Asia/Shanghai")).date()-date.fromisoformat(result["issue_date"])).days
    result["disclaimer"]="Satellite heat stress is not observed coral bleaching. Human review and official guidance are required."
    result["stale_input"]=result["age_days"]>2
    from src.diagnostics import build_diagnostics
    result["diagnostics"]=build_diagnostics(result,data_path=DATA/"processed/daily.csv")
    result["interface_version"]="2.0.0"
    return result

@app.get("/api/evaluation")
def evaluation():
    p=ROOT/"artifacts/evaluation.json"
    if not p.exists(): raise HTTPException(503,"Evaluation is not ready")
    return json.loads(p.read_text())

@app.get("/api/data-manifest")
def manifest():
    for p in [DATA/"manifest.json",DATA/"data_manifest.json",ROOT/"artifacts/data_manifest.json"]:
        if p.exists(): return json.loads(p.read_text())
    raise HTTPException(503,"Data provenance manifest is not ready")

@app.get("/api/export")
def export(site_id:str,as_of:str|None=None):
    f=forecast(site_id,as_of)
    out=io.StringIO()
    w=csv.writer(out)
    w.writerow(["site_id","issued_at","horizon_days","predicted_dhw_C_week","lower","upper","selected_model","physical_baseline","ai_candidate","comparison_envelope_lower","comparison_envelope_upper","comparison_envelope_calibrated","review_reasons","warning"])
    diagnostics={v["horizon"]:v for v in f["diagnostics"]["per_horizon"]}
    for v in f["forecasts"]:
        diag=diagnostics[v["horizon"]];env=diag["comparison_envelope"]
        w.writerow([site_id,f["issue_date"],v["horizon"],v["mean"],v["lower"],v["upper"],v["model_name"],v["baseline"],v["ai_prediction"],env["lower"],env["upper"],False,";".join(diag["reasons"]),"Research prototype; comparison envelope is uncalibrated; not observed bleaching or official warning"])
    return Response(out.getvalue(),media_type="text/csv",
        headers={"Content-Disposition":"attachment; filename=reefahead-brief.csv"})

@app.get("/observation-template.csv")
def observation_template():
    return Response("survey_id,date_utc,site_id,latitude,longitude,depth_m,observer_code,method,sampling_unit,total_count,bleached_count,photo_reference,consent,notes\n",
        media_type="text/csv",headers={"Content-Disposition":"attachment; filename=field-observation-template.csv"})

@app.get("/api/data-catalog")
def data_catalog():
    from src.catalog import build_catalog
    return build_catalog(DATA)

@app.get("/api/evaluation-v2")
def evaluation_v2():
    p=ROOT/"artifacts/evaluation_v2.json"
    if not p.exists():raise HTTPException(503,"Exploratory diagnostics are not ready")
    return json.loads(p.read_text())

@app.get("/api/spatial-context")
def spatial_context(site_id:str|None=None):
    p=DATA/"atlas_20261018/context.json"
    if not p.exists():raise HTTPException(503,"Atlas spatial context is not prepared")
    from src.spatial import load_context
    try:result=load_context(DATA)
    except (ValueError,FileNotFoundError,KeyError) as exc:raise HTTPException(503,str(exc))
    if site_id:
        result["sites"]=[s for s in result["sites"] if s["site_id"]==site_id]
        if not result["sites"]:raise HTTPException(404,"Unknown satellite pixel")
    return result

@app.get("/api/habitat")
def habitat():
    p=DATA/"atlas_20261018/display_habitat.geojson"
    if not p.exists():raise HTTPException(503,"Atlas display geometry is not prepared")
    from src.spatial import load_context
    try:load_context(DATA)
    except (ValueError,FileNotFoundError,KeyError) as exc:raise HTTPException(503,str(exc))
    return FileResponse(p,media_type="application/geo+json")
