"""Append a verified actual GET receipt as public evidence, no metric calculations."""
import sys
from control import *

def main():
    name=sys.argv[1]
    pubs=read(WORK/'publications.json');receipt=pubs[-1]
    assert receipt['status']=='PASS' and all(c['returned_body_exact'] for c in receipt['actual_GET_checks'])
    save(OUT/(name+'.json'),receipt)
    print(json.dumps({'receipt':name,'HEAD':receipt['HEAD'],'verified_bodies':len(receipt['paths'])}))

if __name__=='__main__':main()
