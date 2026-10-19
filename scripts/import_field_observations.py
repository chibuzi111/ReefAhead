"""Validate authorized offline CSV; save separately from satellite training data."""
import argparse,json,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.observations import validate_observations
p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--sites',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
sites=pd.read_csv(a.sites).groupby('site_id')[['latitude','longitude']].first().reset_index().to_dict('records')
df=validate_observations(pd.read_csv(a.input),sites)
if a.output.exists():raise FileExistsError('Refusing to overwrite prior observation import')
a.output.parent.mkdir(parents=True,exist_ok=True);df.to_csv(a.output,index=False)
a.output.with_suffix('.provenance.json').write_text(json.dumps({'source_sha256':hashlib.sha256(a.input.read_bytes()).hexdigest(),'rows':len(df),'training_labels_created':False,'sensitive_locations':'keep private; no automatic upload'},indent=2))
print('Authorized observations validated:',len(df),'rows; no satellite training data changed')
