"""Atlas habitat geometry context; no observations, labels, or forecasts are changed."""
from __future__ import annotations
from collections import defaultdict
import hashlib, json, math
from pathlib import Path
import shapely
from shapely.geometry import shape, box, mapping, GeometryCollection
from shapely.ops import unary_union
from pyproj import CRS, Transformer

SITE_CELLS = [
    {"site_id":"semporna_south_central","latitude":4.275,"longitude":118.625},
    {"site_id":"semporna_offshore_1","latitude":4.275,"longitude":118.725},
    {"site_id":"semporna_offshore_2","latitude":4.275,"longitude":118.825},
    {"site_id":"semporna_offshore_3","latitude":4.275,"longitude":118.925},
]
DEFAULT_BBOX = [118.600,4.250,118.950,4.300]
LAYER_IDS = ("benthic","geomorphic")
ATTRIBUTION = "Allen Coral Atlas maps, bathymetry and map statistics © 2018–2023 Allen Coral Atlas Partnership and Arizona State University; CC BY 4.0. Local subset clipped and reprojected for area calculation; display geometry simplified separately."
LIMITATIONS = [
    "Mapped habitat overlap is satellite-derived spatial context, not field confirmation of a reef, living coral, species, or present coral health.",
    "Coral/Algae is a combined mapped class and cannot be interpreted as live-coral cover or bleaching percentage.",
    "Unmapped area is unknown, not proof of no reef: depth, turbidity, masks, and classification errors affect map coverage.",
    "Atlas habitat maps have a nominal 5 m grid; NOAA heat-stress cells are 0.05 degrees. The whole NOAA cell is not a coral reef and the thermal value is not downscaled to 5 m.",
    "Official FAQ gives typical scope below 10 m for benthic and below 15 m for geomorphic mapping; these are not local depth measurements.",
    "The WFS does not expose observation date, mapping region, or regional accuracy for each feature. Download date is not habitat observation date; catalog publication dates cannot be assigned to this AOI without a region join.",
    "Benthic and geomorphic layers describe different attributes of overlapping space; their areas must not be added.",
    "Geometry is not a navigation chart, protected-area boundary, reef intervention authorization, or a field-survey result."
]

def pixel_polygon(site, width_degrees=0.05):
    lat,lon=float(site["latitude"]),float(site["longitude"])
    if not all(math.isfinite(v) for v in [lat,lon,width_degrees]) or not 0<width_degrees<=1 or not -89<lat<89 or not -179<lon<179:
        raise ValueError("Invalid pixel coordinates or width")
    half=width_degrees/2
    return box(lon-half,lat-half,lon+half,lat+half)

def projection_for_bbox(bbox):
    west,south,east,north=map(float,bbox)
    if not all(math.isfinite(x) for x in bbox) or not -180<west<east<180 or not -89<south<north<89 or east-west>1 or north-south>1:
        raise ValueError("Expected a bounded local AOI no larger than one degree")
    spec=f"+proj=laea +lat_0={(south+north)/2} +lon_0={(west+east)/2} +datum=WGS84 +units=m +no_defs"
    target=CRS.from_proj4(spec)
    forward=Transformer.from_crs("EPSG:4326",target,always_xy=True)
    inverse=Transformer.from_crs(target,"EPSG:4326",always_xy=True)
    return spec,lambda g:shapely.transform(g,forward.transform,interleaved=False),lambda g:shapely.transform(g,inverse.transform,interleaved=False)

def require_complete_collection(data):
    if not isinstance(data,dict) or data.get("type")!="FeatureCollection" or not isinstance(data.get("features"),list):
        raise ValueError("Not a GeoJSON FeatureCollection")
    matched=data.get("numberMatched",data.get("totalFeatures"))
    returned=data.get("numberReturned")
    if isinstance(matched,str) and matched.isdigit(): matched=int(matched)
    if isinstance(returned,str) and returned.isdigit(): returned=int(returned)
    if not isinstance(matched,int) or matched<0 or returned!=matched or len(data["features"])!=matched:
        raise ValueError("Incomplete or unverifiable WFS result; never interpret truncation as no coverage")
    return matched

def analyse_habitat(layer_data, sites=None, bbox=None, display_tolerance_m=7.0):
    sites=list(SITE_CELLS if sites is None else sites)
    bbox=list(DEFAULT_BBOX if bbox is None else bbox)
    spec,project,unproject=projection_for_bbox(bbox);aoi=box(*bbox)
    if set(layer_data)!=set(LAYER_IDS): raise ValueError("Both independent habitat layers are required")
    if len({s["site_id"] for s in sites})!=len(sites): raise ValueError("Duplicate site ids")
    if not 0<=display_tolerance_m<=25: raise ValueError("Display simplification tolerance out of bounds")
    exact_features=[];display_features=[];layer_unions={};geographic_unions={};layer_meta=[]
    for layer in LAYER_IDS:
        data=layer_data[layer];matched=require_complete_collection(data)
        groups=defaultdict(list);geographic_groups=defaultdict(list);seen=set();empty=0;duplicate=0
        for index,feature in enumerate(data["features"]):
            if feature.get("type")!="Feature" or not isinstance(feature.get("properties"),dict):raise ValueError("Invalid source feature")
            klass=feature["properties"].get("class_name")
            if not isinstance(klass,str) or not klass.strip():raise ValueError("Missing habitat class")
            geom=shape(feature.get("geometry"))
            if geom.geom_type not in {"Polygon","MultiPolygon"} or geom.is_empty or not geom.is_valid:raise ValueError("Invalid source polygon; refusing automatic geometry repair")
            coords=shapely.get_coordinates(geom)
            if not all(math.isfinite(float(v)) for v in coords.flat):raise ValueError("Non-finite coordinates")
            if not (-180<=geom.bounds[0]<=geom.bounds[2]<=180 and -90<=geom.bounds[1]<=geom.bounds[3]<=90):raise ValueError("Invalid geographic bounds")
            # Coordinates are longitude/latitude from explicit OGC:CRS84 requests.
            clipped=geom.intersection(aoi)
            if clipped.is_empty or clipped.area<=0:
                empty+=1;continue
            if clipped.geom_type not in {"Polygon","MultiPolygon"}:
                polys=[g for g in clipped.geoms if g.geom_type in {"Polygon","MultiPolygon"}]
                clipped=unary_union(polys)
            fingerprint=hashlib.sha256(klass.encode()+shapely.normalize(clipped).wkb).hexdigest()
            if fingerprint in seen: duplicate+=1;continue
            seen.add(fingerprint)
            groups[klass].append(project(clipped))
            geographic_groups[klass].append(clipped)
            exact_features.append({"type":"Feature","id":layer+"-"+fingerprint[:20],"geometry":mapping(clipped),
                "properties":{"layer_id":layer,"class_name":klass,"source_feature_id":feature.get("id"),"source_feature_index":index,
                "source_area_sqkm":feature["properties"].get("area_sqkm"),"geometry_use":"exact_source_geometry_clipped_to_AOI",
                "source_geometry_sha256":hashlib.sha256(shapely.normalize(geom).wkb).hexdigest()}})
        unions={klass:unary_union(geoms) for klass,geoms in groups.items()}
        all_union=unary_union(list(unions.values()))
        overlap=max(0.0,sum(g.area for g in unions.values())-all_union.area)
        if overlap>max(1.0,all_union.area*1e-8):raise ValueError(f"Overlapping class areas in {layer}: {overlap} square meters; review source")
        layer_unions[layer]=unions
        geographic_unions[layer]={klass:unary_union(gs) for klass,gs in geographic_groups.items()}
        for klass,geometry in sorted(unions.items()):
            simplified=geometry.simplify(display_tolerance_m,preserve_topology=True)
            display_features.append({"type":"Feature","id":layer+"-"+klass.replace("/","-").replace(" ","_"),
                "geometry":mapping(unproject(simplified)),"properties":{"layer_id":layer,"class_name":klass,
                "geometry_use":"display_only_dissolved_and_simplified","simplification_tolerance_m":display_tolerance_m,
                "exact_mapped_area_km2":geometry.area/1e6}})
        layer_meta.append({"layer_id":layer,"wfs_type_name":"coral-atlas:"+layer+"_data_verbose","source_feature_count":matched,
            "clipped_feature_count":sum(f["properties"]["layer_id"]==layer for f in exact_features),
            "duplicates_removed":duplicate,"nonintersecting_or_zero_area_features":empty,"invalid_source_features":0,
            "cross_class_overlap_m2":overlap,"classes":sorted(groups),"mapped_aoi_area_km2":all_union.area/1e6,
            "nominal_map_grid_m":5,"publication_date_for_aoi":None,"regional_accuracy_for_aoi":None})
    site_rows=[];pixel_features=[]
    for site in sites:
        pixel=pixel_polygon(site)
        if not aoi.buffer(1e-9).covers(pixel):raise ValueError("AOI does not contain the entire requested thermal pixel")
        projected=project(shapely.segmentize(pixel,max_segment_length=0.005));pixel_area=projected.area/1e6;details={}
        for layer in LAYER_IDS:
            intersections={c:project(g.intersection(pixel)) for c,g in geographic_unions[layer].items()}
            intersections={c:g for c,g in intersections.items() if not g.is_empty and g.area>1e-6}
            mapped=unary_union(list(intersections.values())).area/1e6
            classes=[{"class_name":c,"area_km2":g.area/1e6,"fraction_of_mapped":g.area/1e6/mapped if mapped else None,
                "fraction_of_pixel":g.area/1e6/pixel_area} for c,g in sorted(intersections.items())]
            if mapped>pixel_area+1e-8:raise ValueError("Mapped area exceeds pixel")
            details[layer]={"status":"mapped_habitat_overlap" if mapped>0 else "no_mapped_overlap_unknown",
                "mapped_area_km2":mapped,"mapped_fraction_of_pixel":mapped/pixel_area,"unmapped_area_km2":max(0,pixel_area-mapped),
                "unmapped_meaning":"not mapped by this layer; reef presence is unknown","classes":classes}
        row={**site,"pixel_bbox":list(pixel.bounds),"pixel_area_km2":pixel_area,"status":"mapped_habitat_overlap" if any(v["mapped_area_km2"]>0 for v in details.values()) else "no_mapped_overlap_unknown",
            "layers":details,"field_verified":False,"pixel_definition":"NOAA CRW fixed 0.05 degree cell centered on the recorded latitude/longitude"}
        site_rows.append(row)
        pixel_features.append({"type":"Feature","id":site["site_id"],"geometry":mapping(pixel),"properties":{**site,"geometry_use":"satellite_pixel_boundary_not_reef_boundary","pixel_area_km2":pixel_area}})
    base={"type":"FeatureCollection","bbox":bbox,"attribution":ATTRIBUTION,"license":"CC-BY-4.0"}
    context={"schema_version":"1.0","complete":True,"status":"complete","bbox":bbox,"crs":"EPSG:4326","coordinate_order":"longitude,latitude",
        "area_method":"local_LAEA_equal_area","area_crs":spec,"area_units":"km2","area_note":"Union within each class prevents double counting; source polygons are intersected with the exact geographic pixel boundary before LAEA area measurement. Pixel boundaries are densified at 0.005 degree before projection. The two layers are evaluated separately.",
        "sites":site_rows,"layers":layer_meta,"limitations":LIMITATIONS,"display_simplification_m":display_tolerance_m}
    return context,{**base,"features":exact_features},{**base,"features":pixel_features},{**base,"features":display_features,"geometry_use":"display_only"}

def atlas_directory(data_root):
    root=Path(data_root)
    return root if (root/"context.json").exists() or root.name=="atlas_20261018" else root/"atlas_20261018"

def load_context(data_root):
    """Validate portable exported files before returning context; raw inputs are a separate audit.
    Requires context/display/pixels/manifest. Exact habitat.geojson is optional in
    portable distributions; when present it is verified too. Hashes detect changes,
    but an unsigned local manifest is not a cryptographic identity guarantee.
    """
    root=atlas_directory(data_root)
    manifest=json.loads((root/"manifest.json").read_text())
    if manifest.get("complete") is not True or manifest.get("schema_version")!="1.0":
        raise ValueError("Atlas manifest is incomplete or unsupported")
    names=["context.json","display_habitat.geojson","pixels.geojson"]
    if (root/"habitat.geojson").exists():names.append("habitat.geojson")
    for name in names:
        info=manifest.get("outputs",{}).get(name)
        if not isinstance(info,dict) or info.get("path")!=name:raise ValueError("Missing or unsafe Atlas output entry")
        path=root/name
        if not path.resolve().is_relative_to(root.resolve()):raise ValueError("Atlas output path escapes its directory")
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=info["sha256"] or len(raw)!=info["bytes"]:
            raise ValueError(f"Atlas output integrity failure: {name}")
    context=json.loads((root/"context.json").read_text())
    if context.get("complete") is not True or context.get("schema_version")!="1.0":
        raise ValueError("Atlas context is incomplete or unsupported")
    if set(s["site_id"] for s in context.get("sites",[]))!={s["site_id"] for s in SITE_CELLS}:
        raise ValueError("Atlas context does not cover the configured sites")
    for site in context["sites"]:
        for layer in LAYER_IDS:
            entry=site["layers"][layer]
            if not 0<=entry["mapped_fraction_of_pixel"]<=1+1e-8 or entry["mapped_area_km2"]<0:
                raise ValueError("Invalid Atlas area statistics")
    context["runtime_integrity"]={"verified_outputs":names,"raw_sources_verified":False,
        "exact_habitat_present":"habitat.geojson" in names,"note":"Export hashes verified against local manifest; raw-source verification is a separate offline audit."}
    return context
