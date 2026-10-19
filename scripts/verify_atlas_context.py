#!/usr/bin/env python3
"""Verify exported Atlas hashes; --raw independently traces geometry and checks geodesic areas."""
import argparse,hashlib,json,sys
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import shapely
from shapely.geometry import shape,box
from shapely.ops import unary_union
from pyproj import Geod
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.spatial import load_context,atlas_directory

def audit(data_root,raw=False):
    root=atlas_directory(data_root);context=load_context(root);manifest=json.loads((root/"manifest.json").read_text())
    report={"checked_at_utc":datetime.now(timezone.utc).isoformat(),"passed":True,"portable_outputs_verified":context["runtime_integrity"]["verified_outputs"],
        "raw_sources_verified":False}
    if not raw:return report
    for meta in manifest["inputs"]:
        path=root/"raw"/Path(meta["path"]).name
        assert hashlib.sha256(path.read_bytes()).hexdigest()==meta["sha256"],f"Raw checksum mismatch: {path.name}"
    original={layer:json.loads((root/"raw"/(layer+"_full.geojson")).read_text()) for layer in ["benthic","geomorphic"]}
    for layer,data in original.items():
        assert len(data["features"])==data["numberMatched"]==data["numberReturned"],"Truncated source"
    exact=json.loads((root/"habitat.geojson").read_text())
    aoi=box(*context["bbox"]);groups=defaultdict(list)
    for f in exact["features"]:
        prop=f["properties"];src=original[prop["layer_id"]]["features"][prop["source_feature_index"]]
        assert prop["class_name"]==src["properties"]["class_name"]
        raw_geom=shape(src["geometry"])
        assert hashlib.sha256(shapely.normalize(raw_geom).wkb).hexdigest()==prop["source_geometry_sha256"]
        expected=raw_geom.intersection(aoi);actual=shape(f["geometry"])
        assert actual.equals_exact(expected,1e-12),"Output geometry differs from the clipped original"
        groups[(prop["layer_id"],prop["class_name"])].append(actual)
    # Independent ellipsoidal measurement in geographic coordinates; no LAEA code used.
    geod=Geod(ellps="WGS84")
    def area(g):
        if g.is_empty:return 0.0
        return abs(geod.geometry_area_perimeter(shapely.orient_polygons(g))[0])/1e6
    unions={key:unary_union(gs) for key,gs in groups.items()}
    rows=[];max_difference=0.0;max_relative=0.0
    for site in context["sites"]:
        pixel=box(*site["pixel_bbox"])
        for layer in ["benthic","geomorphic"]:
            pieces=[g.intersection(pixel) for (l,c),g in unions.items() if l==layer]
            independent=area(unary_union(pieces));reported=site["layers"][layer]["mapped_area_km2"]
            difference=abs(independent-reported);relative=difference/max(reported,1e-12)
            assert difference<=max(1e-5,reported*1e-5),("Area disagreement",site["site_id"],layer,independent,reported)
            max_difference=max(max_difference,difference);max_relative=max(max_relative,relative)
            for klass in site["layers"][layer]["classes"]:
                class_area=area(unions[(layer,klass["class_name"])].intersection(pixel))
                assert abs(class_area-klass["area_km2"])<=max(1e-5,klass["area_km2"]*1e-5)
            rows.append({"site_id":site["site_id"],"layer":layer,"reported_laea_km2":reported,"independent_geodesic_km2":independent,"absolute_difference_km2":difference})
    report.update({"raw_sources_verified":True,"raw_files_verified":len(manifest["inputs"]),"exact_features_traced":len(exact["features"]),
        "independent_area_method":"WGS84 ellipsoidal area of source polygons clipped in geographic coordinates; independent of the LAEA implementation",
        "maximum_absolute_area_difference_km2":max_difference,"maximum_relative_area_difference":max_relative,"site_area_checks":rows})
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--data-root",default="data");p.add_argument("--raw",action="store_true");args=p.parse_args()
    report=audit(args.data_root,args.raw);root=atlas_directory(args.data_root)
    name="raw_audit.json" if args.raw else "portable_audit.json"
    (root/name).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(report,ensure_ascii=False,indent=2))
