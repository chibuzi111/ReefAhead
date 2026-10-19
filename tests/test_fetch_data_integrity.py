"""Synthetic unit inputs verify calendar/source safeguards, never training observations."""
import importlib.util
from pathlib import Path
import csv
import pytest

spec=importlib.util.spec_from_file_location("data_fetch",Path(__file__).parents[1]/"scripts"/"fetch_data.py")
fd=importlib.util.module_from_spec(spec)
spec.loader.exec_module(fd)


def test_expected_grid_calendar_and_leap_year():
    assert len(fd.expected_grid_keys("2024-01-01","2024-12-31"))==366*4
    assert len(fd.expected_grid_keys("2023-01-01","2023-12-31"))==365*4
    assert ("2025-01-01T12:00:00Z","4.275","118.625") not in fd.expected_grid_keys("2024-10-01","2024-12-31")


def test_gap_spans_do_not_request_unrelated_dates():
    keys={(d+"T12:00:00Z","4.275","118.625") for d in ["2024-12-28","2024-12-30","2024-12-31"]}
    assert [[str(x) for x in span] for span in fd.gap_spans(keys)]==[["2024-12-28","2024-12-28"],["2024-12-30","2024-12-31"]]


def fake_download(monkeypatch, expected, mismatch=False, omit_one=False):
    def download(url,path,**kwargs):
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("w") as f:
            writer=csv.writer(f);writer.writerow(["time","latitude","longitude",*fd.VARIABLES])
            for i,key in enumerate(sorted(expected)):
                if omit_one and i==0: continue
                writer.writerow([*key,"31" if mismatch else "30","1","4","0.5"])
        return {"path":str(path),"url":url}
    monkeypatch.setattr(fd,"download",download)


def test_gap_fill_adds_only_authentic_missing_values_and_checks_overlap(tmp_path,monkeypatch):
    expected=fd.expected_grid_keys("2024-12-31","2024-12-31")
    merged={k:{"CRW_SST":"30"} for k in expected}
    fake_download(monkeypatch,expected)
    sources=[]
    fd.fill_mirror_gaps(tmp_path,2024,4,merged,expected,sources)
    assert all(set(row)==set(fd.VARIABLES) for row in merged.values())
    assert sources[0]["filled_values"]==12
    assert sources[0]["overlap_values_compared"]==4
    assert sources[0]["overlap_max_absolute_difference"]==0
    assert all(row["CRW_SST"]=="30" for row in merged.values())


def test_mirror_disagreement_is_not_silently_overwritten(tmp_path,monkeypatch):
    expected=fd.expected_grid_keys("2024-12-31","2024-12-31")
    merged={k:{"CRW_SST":"30"} for k in expected}
    fake_download(monkeypatch,expected,mismatch=True)
    with pytest.raises(ValueError,match="Mirror disagreement"):
        fd.fill_mirror_gaps(tmp_path,2024,4,merged,expected,[])


def test_unresolved_calendar_gap_refuses_partial_year(tmp_path,monkeypatch):
    expected=fd.expected_grid_keys("2024-12-31","2024-12-31")
    fake_download(monkeypatch,expected,omit_one=True)
    with pytest.raises(ValueError,match="Unresolved gaps"):
        fd.fill_mirror_gaps(tmp_path,2024,4,{},expected,[])


def test_documented_repair_refuses_unreviewed_variables(tmp_path,monkeypatch):
    annual=tmp_path/"2019.csv"
    annual.write_text("time,latitude,longitude,CRW_SST,CRW_HOTSPOT,CRW_DHW,CRW_SSTANOMALY\n2019-04-02T12:00:00Z,4.275,118.625,30,0.78,0,1\n")
    def download(url,path,**kwargs):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text("time,latitude,longitude,CRW_SST,CRW_HOTSPOT,CRW_DHW,CRW_SSTANOMALY\n2019-04-02T12:00:00Z,4.275,118.625,31,0.78,0,1\n")
        return {"url":url,"path":str(path)}
    monkeypatch.setattr(fd,"download",download)
    with pytest.raises(ValueError,match="Unexpected cross-source discrepancy"):
        fd.reconcile_documented_2019_mirror_discrepancy(tmp_path,annual,{},2019)
    assert ",30," in annual.read_text()


def test_documented_repair_does_not_apply_to_other_years(tmp_path):
    meta={"sha256":"unaltered"}
    assert fd.reconcile_documented_2019_mirror_discrepancy(tmp_path,tmp_path/"2018.csv",meta,2018) is meta
