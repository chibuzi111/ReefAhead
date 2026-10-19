#!/usr/bin/env python3
"""Verify a documented mirror correction against raw NOAA producer NetCDF.

This is a one-day, four-pixel independent check, not a claim of exhaustive
dual-source validation of the 2003-2026 record.
"""
import argparse,csv,hashlib,json
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import netCDF4

PRODUCTS={
    "hs":("hotspot","CRW_HOTSPOT"),
    "ssta":("sea_surface_temperature_anomaly","CRW_SSTANOMALY"),
    "dhw":("degree_heating_week","CRW_DHW"),
}

def verify(root):
    root=Path(root)
    mirror_path=root/"raw/probes/pacioos_2019_mmm_audit.csv"
    mirror_meta=json.loads(mirror_path.with_suffix(".csv.meta.json").read_text())
    assert hashlib.sha256(mirror_path.read_bytes()).hexdigest()==mirror_meta["sha256"]
    mirror={(r["time"][:10],round(float(r["latitude"]),3),round(float(r["longitude"]),3)):r
            for r in csv.DictReader(mirror_path.read_text().splitlines()) if r["time"]!="UTC"}
    report={"verified_at_utc":datetime.now(timezone.utc).isoformat(),"scope":"2019-04-02, four fixed satellite pixels, three original producer NetCDF products; representative-day check only",
            "source_of_choice":"PacIOOS matches NOAA STAR producer; PIFSC HS/SSTA conflict is retained in the audit trail",
            "records":[],"max_absolute_difference":0.0}
    for prod,(variable,mirror_variable) in PRODUCTS.items():
        path=root/"raw/probes"/f"ct5km_{prod}_v3.1_20190402.nc"
        meta=json.loads(path.with_suffix(".nc.meta.json").read_text())
        assert hashlib.sha256(path.read_bytes()).hexdigest()==meta["sha256"]
        with netCDF4.Dataset(path) as data:
            times=data.variables["time"]
            day=netCDF4.num2date(times[:],times.units)[0].strftime("%Y-%m-%d")
            assert day=="2019-04-02",f"Unexpected producer date {day}"
            v=data.variables[variable]
            assert abs(float(v.scale_factor)-0.01)<1e-12,"Unexpected producer packing precision"
            lat=data.variables["lat"][:];lon=data.variables["lon"][:]
            for longitude in [118.625,118.725,118.825,118.925]:
                iy=int(np.argmin(abs(lat-4.275)));ix=int(np.argmin(abs(lon-longitude)))
                assert abs(float(lat[iy])-4.275)<1e-4 and abs(float(lon[ix])-longitude)<1e-4
                value=float(v[0,iy,ix])
                reference=float(mirror[(day,4.275,longitude)][mirror_variable])
                error=abs(value-reference)
                assert error<1e-8,("Producer disagrees with selected mirror",prod,longitude,value,reference)
                report["max_absolute_difference"]=max(report["max_absolute_difference"],error)
                report["records"].append({"date":day,"latitude":4.275,"longitude":longitude,"product":prod,
                    "variable":variable,"producer_value":value,"pacioos_value":reference,"scale_factor":float(v.scale_factor),
                    "source_sha256":meta["sha256"],"source_url":meta["url"]})
    report["passed"]=True
    report["values_verified"]=len(report["records"])
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--data-dir",default="data");args=p.parse_args()
    report=verify(args.data_dir)
    path=Path(args.data_dir)/"processed/noaa_producer_sample_verification.json"
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(report,ensure_ascii=False,indent=2))
