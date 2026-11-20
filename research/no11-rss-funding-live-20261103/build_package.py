from pathlib import Path
import hashlib,json,shutil,sys
from patches import TRANSFORMS

HERE=Path(__file__).resolve().parent

def package(output, baseline):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    names=['install.py','patches.py','no11_rss_buying_power.py','no11_make_rss_live_config.py',
           'No11RssFundingContract.ps1','Install-No11RssFunding.ps1','README-ja.md']
    hashes={}
    for n in names:
        data=(HERE/n).read_text(encoding='utf-8').encode('utf-8');(output/n).write_bytes(data);hashes[n]=hashlib.sha256(data).hexdigest()
    src={}
    for n in TRANSFORMS:
        if n.endswith('Start-No11UnifiedLauncher.ps1'):continue
        raw=(Path(baseline)/n).read_text(encoding='utf-8').encode('utf-8')
        src[n]=hashlib.sha256(raw).hexdigest()
    manifest={'schemaId':'ARK_NO11_RSS_FUNDING_PACKAGE_V1','packageFiles':hashes,
              'sourceSha256':src,'strategyChanged':False,'createsLiveConfiguration':False,
              'orderSentByInstaller':False}
    (output/'package_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return output

if __name__=='__main__':package(sys.argv[1],sys.argv[2])
