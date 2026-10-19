"""Synthetic polygons test geometry semantics; they are never shipped as habitat data."""
import hashlib,json
from pathlib import Path
import pytest
from shapely.geometry import box,Polygon,mapping
from src.spatial import analyse_habitat,load_context,SITE_CELLS,DEFAULT_BBOX

def feature(g,klass="Coral/Algae"):
    return {"type":"Feature","id":"synthetic-only","geometry":mapping(g),"properties":{"class_name":klass,"area_sqkm":None}}

def collection(features):
    return {"type":"FeatureCollection","numberMatched":len(features),"numberReturned":len(features),"features":features}

def layers(features):
    return {"benthic":collection(features),"geomorphic":collection([])}

def test_empty_valid_response_is_unknown_not_absence_of_reef():
    context,*_=analyse_habitat(layers([]))
    assert context["complete"]
    assert all(s["status"]=="no_mapped_overlap_unknown" for s in context["sites"])
    assert all(s["layers"]["benthic"]["mapped_area_km2"]==0 for s in context["sites"])
    assert "unknown" in context["sites"][0]["layers"]["benthic"]["unmapped_meaning"]

def test_truncated_response_cannot_be_treated_as_complete():
    data=layers([]);data["benthic"]["numberMatched"]=1
    with pytest.raises(ValueError,match="Incomplete"):
        analyse_habitat(data)

def test_duplicate_same_class_is_not_double_counted():
    f=feature(box(118.61,4.26,118.63,4.28))
    one,*_=analyse_habitat(layers([f]));two,*_=analyse_habitat(layers([f,f]))
    assert one["sites"][0]["layers"]["benthic"]["mapped_area_km2"]==two["sites"][0]["layers"]["benthic"]["mapped_area_km2"]
    assert two["layers"][0]["duplicates_removed"]==1

def test_different_classes_cannot_silently_overlap():
    g=box(118.61,4.26,118.63,4.28)
    with pytest.raises(ValueError,match="Overlapping class"):
        analyse_habitat(layers([feature(g),feature(g,"Sand")]))

def test_holes_preserved_and_display_simplification_does_not_change_areas():
    outer=box(118.61,4.26,118.64,4.29)
    inner=box(118.62,4.27,118.63,4.28)
    f=feature(Polygon(outer.exterior.coords,[inner.exterior.coords]))
    a,*_=analyse_habitat(layers([f]),display_tolerance_m=0)
    b,exact,_,display=analyse_habitat(layers([f]),display_tolerance_m=7)
    assert a["sites"]==b["sites"]
    assert len(exact["features"][0]["geometry"]["coordinates"])==2
    assert display["features"][0]["properties"]["geometry_use"]=="display_only_dissolved_and_simplified"

def test_invalid_polygon_is_not_silently_repaired():
    bowtie=Polygon([(118.61,4.26),(118.64,4.29),(118.61,4.29),(118.64,4.26),(118.61,4.26)])
    with pytest.raises(ValueError,match="Invalid source polygon"):
        analyse_habitat(layers([feature(bowtie)]))

def test_partial_aoi_cannot_claim_whole_pixel_statistics():
    with pytest.raises(ValueError,match="entire requested thermal pixel"):
        analyse_habitat(layers([]),bbox=[118.61,4.25,118.95,4.3])

def test_reversed_coordinate_order_is_rejected():
    with pytest.raises(ValueError,match="Invalid geographic bounds"):
        analyse_habitat(layers([feature(box(4.26,118.61,4.28,118.63))]))

def make_portable(root):
    context,_,pixels,display=analyse_habitat(layers([]))
    objects={"context.json":context,"pixels.geojson":pixels,"display_habitat.geojson":display}
    outputs={}
    for name,value in objects.items():
        raw=json.dumps(value).encode();(root/name).write_bytes(raw)
        outputs[name]={"path":name,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
    (root/"manifest.json").write_text(json.dumps({"schema_version":"1.0","complete":True,"outputs":outputs}))

def test_portable_load_requires_no_raw_sources_or_exact_geometry(tmp_path):
    make_portable(tmp_path);context=load_context(tmp_path)
    assert context["complete"]
    assert context["runtime_integrity"]["raw_sources_verified"] is False
    assert context["runtime_integrity"]["exact_habitat_present"] is False

def test_portable_corruption_fails_closed(tmp_path):
    make_portable(tmp_path);(tmp_path/"display_habitat.geojson").write_text("{}")
    with pytest.raises(ValueError,match="integrity failure"):
        load_context(tmp_path)
