#!/usr/bin/env python3
"""Download a bounded public Atlas WFS subset, preserve source evidence, and calculate habitat context."""
from __future__ import annotations
import argparse,hashlib,json,sys,time
from datetime import datetime,timezone
from pathlib import Path
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.spatial import analyse_habitat,projection_for_bbox,DEFAULT_BBOX,ATTRIBUTION,LAYER_IDS

BASE="https://allencoralatlas.org/geoserver/ows"
UA={"User-Agent":"geoserver-client ReefAhead/1.1 public-research"}
SOURCES=[
 ("capabilities.xml",BASE+"?service=wfs&version=2.0.0&request=GetCapabilities"),
 ("maps.json","https://allencoralatlas.org/mapping/maps"),
 ("resources.html","https://allencoralatlas.org/resources/"),
 ("methods.html","https://allencoralatlas.org/methods/"),
 ("terms.html","https://allencoralatlas.org/tou/"),
 ("geoserver_tips.pdf","https://storage.googleapis.com/coral-atlas-static-files/resources-page-materials/Geoserver_Tips.pdf"),
]
def stamp():return datetime.now(timezone.utc).isoformat()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def fetch(url,path):
    meta_path=path.with_suffix(path.suffix+".meta.json")
    if path.exists() and meta_path.exists():
        m=json.loads(meta_path.read_text())
        if m.get("status",200)==200 and digest(path)==m["sha256"] and m.get("url")==url:return m
    last=None
    for attempt in range(3):
        try:
            response=requests.get(url,headers=UA,timeout=(15,120),stream=True);response.raise_for_status()
            tmp=path.with_suffix(path.suffix+".part");size=0
            with tmp.open("wb") as f:
                for chunk in response.iter_content(1048576):
                    size+=len(chunk)
                    if size>120_000_000:raise ValueError("Small-AOI response exceeded 120 MB; refusing broad download")
                    f.write(chunk)
            tmp.replace(path)
            m={"url":url,"resolved_url":response.url,"status":response.status_code,"retrieved_at_utc":stamp(),
               "sha256":digest(path),"bytes":size,"path":str(path),"content_type":response.headers.get("Content-Type")}
            meta_path.write_text(json.dumps(m,indent=2)+"\n");return m
        except Exception as e:
            last=e
            if attempt<2:time.sleep(attempt+1)
    raise RuntimeError(f"Public source unavailable: {url}: {last}")

def main():
    p=argparse.ArgumentParser();p.add_argument("--output-dir",default="data/atlas_20261018")
    p.add_argument("--bbox",nargs=4,type=float,default=DEFAULT_BBOX);p.add_argument("--display-tolerance-m",type=float,default=7.0)
    a=p.parse_args();projection_for_bbox(a.bbox)
    root=Path(a.output_dir);(root/"raw").mkdir(parents=True,exist_ok=True)
    inputs=[];layer_data={}
    for name,url in SOURCES:
        inputs.append(fetch(url,root/"raw"/name))
    for layer in LAYER_IDS:
        typename="coral-atlas:"+layer+"_data_verbose"
        schema_url=requests.Request("GET",BASE,params={"service":"wfs","version":"2.0.0","request":"DescribeFeatureType","typeNames":typename}).prepare().url
        inputs.append(fetch(schema_url,root/"raw"/(layer+"_schema.xsd")))
        params={"service":"wfs","version":"2.0.0","request":"GetFeature","typeNames":typename,
            "bbox":",".join(f"{x:.3f}" for x in a.bbox)+",urn:ogc:def:crs:OGC:1.3:CRS84",
            "srsName":"urn:ogc:def:crs:OGC:1.3:CRS84","outputFormat":"application/json","count":10000,"sortBy":"class_name,area_sqkm"}
        url=requests.Request("GET",BASE,params=params).prepare().url
        path=root/"raw"/(layer+"_full.geojson");inputs.append(fetch(url,path));layer_data[layer]=json.loads(path.read_text())
    context,habitat,pixels,display=analyse_habitat(layer_data,bbox=a.bbox,display_tolerance_m=a.display_tolerance_m)
    catalog=json.loads((root/"raw/maps.json").read_text())
    context.update({"generated_at_utc":stamp(),"source_name":"Allen Coral Atlas public WFS",
        "license":{"id":"CC-BY-4.0","url":"https://creativecommons.org/licenses/by/4.0/","attribution":ATTRIBUTION,
            "source_url":"https://allencoralatlas.org/resources/","terms_url":"https://allencoralatlas.org/tou/",
            "notes":"Only local habitat polygons; no Planet satellite imagery. FAQ explicitly permits WFS analysis and supplies CC BY 4.0 map attribution; global reproduction requires written consent. General site terms are retained separately; this project makes no unrestricted global redistribution claim."},
        "map_publication_catalog":catalog,"provenance":{"source_manifest":"manifest.json","wfs_request_complete":True,
            "sort_fields":["class_name","area_sqkm"],"pagination":"Single bounded request per layer; count=10000, numberReturned=numberMatched required. No unsupported natural-order pagination.",
            "raw_inputs":[{"path":str(Path(m["path"]).relative_to(root)),"sha256":m["sha256"],"url":m["url"],"retrieved_at_utc":m["retrieved_at_utc"]} for m in inputs]}})
    for layer in context["layers"]:
        meta=next(m for m in inputs if Path(m["path"]).name==layer["layer_id"]+"_full.geojson")
        layer["raw_sha256"]=meta["sha256"];layer["retrieved_at_utc"]=meta["retrieved_at_utc"]
    files={"context.json":context,"habitat.geojson":habitat,"pixels.geojson":pixels,"display_habitat.geojson":display}
    for name,obj in files.items():
        path=root/name;tmp=path.with_suffix(path.suffix+".part")
        tmp.write_text(json.dumps(obj,ensure_ascii=False,separators=(",",":"),allow_nan=False)+"\n");tmp.replace(path)
    manifest={"schema_version":"1.0","complete":True,"created_at_utc":stamp(),"bbox":a.bbox,"source":"Allen Coral Atlas",
        "license":context["license"],"inputs":inputs,"outputs":{name:{"path":name,"bytes":(root/name).stat().st_size,"sha256":digest(root/name)} for name in files},
        "code_sha256":{name:digest(Path(__file__).resolve().parents[1]/name) for name in ["src/spatial.py","scripts/fetch_atlas_context.py","scripts/verify_atlas_context.py"]},
        "frozen_thermal_data_modified":False}
    (root/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"complete":True,"output":str(root),"features":len(habitat["features"]),"display_features":len(display["features"]),"sites":context["sites"]},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
