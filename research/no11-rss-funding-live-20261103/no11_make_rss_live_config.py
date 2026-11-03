"""Generate the native normal-MAX3 LIVE config pair from real input paths.

Does not launch anything, query a bank, invent market data, or initialize a
ledger. Actual startup still requires the existing same-day operator switch.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sys

import no11_received_session_bootstrap as bootstrap
import no11_broker_execution_service as service
import no11_broker_execution_ledger as ledger
import no11_rss_buying_power as rss


def build(spec, output, now):
    rss.need(type(spec) is dict and set(spec) == {'bootstrapInputs','transport','originalArrivalTable'}, 'SETUP_FIELDS')
    inputs=deepcopy(spec['bootstrapInputs'])
    rss.need(type(inputs) is dict and inputs.get('sessionDate') == now[:10], 'SETUP_ACTUAL_SESSION_DAY')
    rss.need('shadowAccountConfig' not in inputs and 'brokerExecutionConfig' not in inputs, 'SETUP_NO_SHADOW_OR_OLD_BROKER')
    day=inputs['sessionDate']
    transport=deepcopy(spec['transport'])
    # The operator supplies the actual physical pins and the session-enabled
    # transport file. Never fill missing pins, approvals or book identities.
    rss.need(type(transport) is dict and transport.get('sessionDate') == day
             and transport.get('mode') == 'LIVE'
             and transport.get('orderTransmission') is True
             and transport.get('operatorEnabled') is True
             and transport.get('approvedForSession') is True, 'SETUP_SESSION_TRANSPORT_REQUIRED')
    required={'schemaId','rssSessionKey','expiresAtJst','workbookPath','dispatchDirectory',
              'worksheetName','formulaCell','triggerCell','guardCell','sessionCell','guardValue',
              'expectedExcelPid','expectedExcelHwnd','expectedExcelStartedAt','expectedAddInPaths',
              'expectedOpenWorkbooks','permitMaximumAgeMs','responseTimeoutMs'}
    rss.need(required <= set(transport), 'SETUP_PHYSICAL_PINS_MISSING')
    root=bootstrap.private(output,True)
    table=bootstrap.private(spec['originalArrivalTable'])
    service.capital.original_arrival_tables(table)
    broker={'schemaId':service.CONFIG,'sessionDate':day,'fundingPolicy':rss.POLICY,
        'feeCourse':'ZERO','evidenceMode':'BROKER_OBSERVATION',
        'ledger':{'schemaId':ledger.CONFIG_SCHEMA,'sessionDate':day,'account':'一般',
                  'allocatedCashJpy':rss.AUTO,'externalSymbols':[],'maxSymbols':3,'lotSize':100,
                  'evidenceMode':'BROKER_OBSERVATION','productionReady':False,'orderTransmission':False},
        'transport':transport,
        'orderTerms':{'orderType':'MARKET','limitPrice':None,'timeInForce':'DAY','sor':True,
                      'accountType':1,'accountTypeVerified':True},
        'originalArrivalTable':str(table),'reserveChargesJpy':'0',
        'productionReady':False,'orderTransmission':True}
    service.validate_config(broker,day)
    broker_path=bootstrap.immutable(root,'rss-live-broker-config',broker)
    inputs.update(schemaId=bootstrap.CONFIG,productionReady=False,orderTransmission=False,
                  brokerExecutionConfig=str(broker_path))
    bootstrap.validate_config(inputs,allow_explicit_live=True)
    boot_path=bootstrap.immutable(root,'rss-live-bootstrap',inputs)
    return boot_path,broker_path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',required=True,type=Path)
    p.add_argument('--output-root',required=True,type=Path)
    args=p.parse_args()
    spec,_=bootstrap.load_json(args.spec,100_000)
    now=datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='milliseconds')
    boot,broker=build(spec,args.output_root,now)
    print('RSS_LIVE_BOOTSTRAP='+str(boot))
    print('RSS_LIVE_BROKER_CONFIG='+str(broker))
    print('TRADE_LAUNCHED=False')
    print('ORDER_SENT_BY_GENERATOR=False')


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,TypeError,KeyError) as e:
        print(service.safe_reason(e),file=sys.stderr)
        raise SystemExit(2)
