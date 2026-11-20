"""Metadata-only entitlement/calendar probe. Never admit price response payloads."""
import hashlib,json,os,re,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/phase57-behavior-expansion-v1/probe-v2'

def main():
 if OUT.exists():
  print('PRESERVED_EXISTING_METADATA_NO_REQUESTS');return
 OUT.mkdir(parents=True,exist_ok=False)
 key=os.environ['JQUANTS_API_KEY']; assert key
 receipts=[]
 # Deliberately outside all research/holdout windows. Only HTTP error semantics retained.
 for endpoint in ['equities/bars/daily','equities/bars/minute']:
  url='https://api.jquants.com/v2/'+endpoint+'?date=1900-01-01'
  r={'url':url,'retrievedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'payloadAdmitted':False}
  req=urllib.request.Request(url,headers={'x-api-key':key})
  try:
   with urllib.request.urlopen(req,timeout=120) as response:
    r['status']=response.status
    # An unexpected success is not permission to consume its payload.
    r['error']='UNEXPECTED_SUCCESS_NO_BODY_READ'
  except urllib.error.HTTPError as e:
   raw=e.read();r['status']=e.code;r['responseSha256']=hashlib.sha256(raw).hexdigest()
   text=raw.decode('utf8').replace(key,'[REDACTED]')
   body=json.loads(text);assert isinstance(body,dict) and 'data' not in body
   r['errorBody']=body
  receipts.append(r);time.sleep(1.2)
 (OUT/'boundaries.json').write_text(json.dumps(receipts,indent=2)+'\n')
 url='https://api.jquants.com/v2/markets/calendar?from=2021-09-19&to=2026-09-19'
 req=urllib.request.Request(url,headers={'x-api-key':key})
 print(json.dumps(receipts),flush=True)
 try:
  with urllib.request.urlopen(req,timeout=120) as response: raw=response.read()
 except urllib.error.HTTPError as e:
  error=json.loads(e.read().decode().replace(key,'[REDACTED]'));print(json.dumps(error),flush=True)
  (OUT/'calendar-error.json').write_text(json.dumps(error,indent=2)+'\n');return
 body=json.loads(raw);assert 'pagination_key' not in body or not body['pagination_key']
 assert all(set(x)<= {'Date','HolDiv'} for x in body['data'])
 (OUT/'calendar.json').write_bytes(raw)
 (OUT/'receipt.json').write_text(json.dumps({'calendarUrl':url,'calendarSha256':hashlib.sha256(raw).hexdigest(),'requests':3,'outcomePayloadsRead':0,'purchases':0,'runId':os.getenv('GITHUB_RUN_ID'),'head':os.getenv('EXPECTED_HEAD')},indent=2)+'\n')
 print(json.dumps(receipts))
if __name__=='__main__':main()
