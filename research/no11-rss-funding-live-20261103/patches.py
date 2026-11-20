"""Context-pinned, strategy-preserving transforms for the applied clean rebuild."""
from __future__ import annotations
import ast
from pathlib import Path

ENGINE = 'research/no12-prebuy-causal-runtime-20261011'


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('NO11_RSS_INSTALL_SOURCE_CONTEXT_CHANGED:' + repr(old[:70]))
    return text.replace(old, new, 1)


def change_service(text):
    text = replace(text, 'import no11_securities_cash_only as securities_cash\n',
                   'import no11_securities_cash_only as securities_cash\nimport no11_rss_buying_power as rss_funding\n')
    text = replace(text, "    if live:\n        source_file = config.get('securitiesCashEvidenceFile')", "    rss_selected = rss_funding.selected(config)\n    if rss_selected:\n        rss_funding.validate(config)\n    if live and not rss_selected:\n        source_file = config.get('securitiesCashEvidenceFile')")
    anchor = "        self.opening_cash_evidence_sha256 = None\n        if config['transport']['mode'] == 'LIVE':"
    text = replace(text, anchor, """        self.opening_cash_evidence_sha256 = None
        self.rss_opening_cash_proof = None
        self.rss_opening_cash_sha256 = None
        if rss_funding.selected(config):
            ledger_config, self.rss_opening_cash_proof, self.rss_opening_cash_sha256 = rss_funding.resolve_opening(
                self.root, config, database, self.clock(), read_private, self.bridge, exclusive_json)
        elif config['transport']['mode'] == 'LIVE':""")
    text = replace(text, "            old = self.book.source_checkpoint('controller.identity')",
                   "            if self.rss_opening_cash_sha256 is not None:\n                identity['rssOpeningFundingSha256'] = self.rss_opening_cash_sha256\n            old = self.book.source_checkpoint('controller.identity')")
    text = replace(text, "        if self.config['evidenceMode'] == 'OFFLINE_REPLAY':\n            return True\n        filename = self.config.get('buyingPowerEvidenceFile')",
                   "        if self.config['evidenceMode'] == 'OFFLINE_REPLAY':\n            return True\n        if rss_funding.selected(self.config):\n            return rss_funding.current_usable(self, at)\n        filename = self.config.get('buyingPowerEvidenceFile')")
    text = replace(text, "            'buyingPowerRefreshVerified': self._buying_power_verified(at),",
                   "            'buyingPowerRefreshVerified': (False if rss_funding.selected(self.config) else self._buying_power_verified(at)),\n            'buyingPowerUsableByPolicy': self._buying_power_verified(at),\n            'fundingPolicy': self.config.get('fundingPolicy', 'SECURITIES_ACCOUNT_CASH_ONLY'),")
    text = replace(text, "            'openingCashScope': (self.opening_cash_proof['basis'] if self.opening_cash_proof\n                                 else 'NOT_MACHINE_CERTIFIED'),",
                   "            'openingCashScope': (self.rss_opening_cash_proof['basis'] if self.rss_opening_cash_proof else\n                                 self.opening_cash_proof['basis'] if self.opening_cash_proof else 'NOT_MACHINE_CERTIFIED'),")
    return text


def change_bootstrap(text):
    text = replace(text, 'import no11_received_pipeline_service as service\n',
                   'import no11_received_pipeline_service as service\nimport no11_rss_buying_power as rss_funding\n')
    text = replace(text, "             and type(obj.get('securitiesCashEvidenceFile')) is str\n             and Path(obj['securitiesCashEvidenceFile']).is_absolute(),",
                   "             and (rss_funding.selected(obj) or\n                  (type(obj.get('securitiesCashEvidenceFile')) is str\n                   and Path(obj['securitiesCashEvidenceFile']).is_absolute())),")
    text = replace(text, "             'EXPLICIT_LIVE_APPROVAL_AND_SECURITIES_EVIDENCE_REQUIRED')\n    else:",
                   "             'EXPLICIT_LIVE_APPROVAL_AND_SECURITIES_EVIDENCE_REQUIRED')\n        if rss_funding.selected(obj):\n            rss_funding.validate(obj)\n    else:")
    return text


def inject_helper(text):
    return replace(text, "$ErrorActionPreference='Stop'\n", "$ErrorActionPreference='Stop'\n. (Join-Path $PSScriptRoot 'No11RssFundingContract.ps1')\n")


def change_operator(text):
    text = inject_helper(text)
    old = """ Need ($broker.ledger.maxSymbols -eq 3 -and
       $broker.ledger.lotSize -eq 100 -and
       $broker.ledger.allocatedCashJpy -ceq 'AUTO_SECURITIES_ACCOUNT_CASH_ONLY') 'MAX3_AND_SECURITIES_CASH'
 $cash=Get-Content -LiteralPath (Private ([string]$broker.securitiesCashEvidenceFile)) -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($cash.sessionDate -ceq $today -and
       $cash.operatorReviewed -eq $true -and
       $cash.bankBridgeExcluded -eq $true -and
       $cash.autoSweepDisabledConfirmed -eq $true -and
       $cash.marginAndCreditExcluded -eq $true) 'REVIEWED_SECURITIES_ONLY_CASH'"""
    text = replace(text, old, " if(Test-No11RssFundingPolicy $broker){\n  Assert-No11RssFundingContract $broker $today\n }else{\n" + old + "\n }")
    anchor = "  [Environment]::SetEnvironmentVariable('ARK_NO11_ACCOUNT_OBSERVATION_FILE',$sourceFile,'Process')"
    text = replace(text, anchor, anchor + "\n  if(Test-No11RssFundingPolicy $broker){\n   Wait-No11RssFundingObservation $sourceFile $today $child\n  }")
    return text


def change_launcher(text):
    text = inject_helper(text)
    old = "       $broker.ledger.allocatedCashJpy -ceq 'AUTO_SECURITIES_ACCOUNT_CASH_ONLY') 'BROKER_CASH_ONLY_AND_SESSION_APPROVAL'\n [void](LocalFile $broker.securitiesCashEvidenceFile 'SECURITIES_CASH_EVIDENCE')"
    new = """       ($broker.ledger.allocatedCashJpy -ceq 'AUTO_SECURITIES_ACCOUNT_CASH_ONLY' -or
        (Test-No11RssFundingPolicy $broker))) 'BROKER_CASH_ONLY_AND_SESSION_APPROVAL'
 if(Test-No11RssFundingPolicy $broker){
  Assert-No11RssFundingContract $broker $day
 }else{
  [void](LocalFile $broker.securitiesCashEvidenceFile 'SECURITIES_CASH_EVIDENCE')
 }"""
    return replace(text, old, new)


def change_ui(text):
    text = replace(text, '            "buyingPowerVerified": False, "securitiesOnlyCashReviewed": False,',
                   '            "buyingPowerVerified": False, "securitiesOnlyCashReviewed": False,\n            "rssFundingSelected": False, "fundingPolicy": None,')
    text = replace(text, '                  securitiesOnlyCashReviewed=report.get("securitiesOnlyOpeningCashReviewed") is True,',
                   '                  securitiesOnlyCashReviewed=report.get("securitiesOnlyOpeningCashReviewed") is True,\n                  rssFundingSelected=(report.get("fundingPolicy") == "RSS_BUYING_POWER" and\n                                      report.get("openingCashScope") == "USER_SELECTED_RSS_BUYING_POWER_NOT_VENDOR_REFRESH_CERTIFIED"),\n                  fundingPolicy=report.get("fundingPolicy"),')
    text = replace(text, '                                  and report.get("buyingPowerRefreshVerified") is True),',
                   '                                  and (report.get("buyingPowerRefreshVerified") is True or\n                                       (report.get("fundingPolicy") == "RSS_BUYING_POWER" and\n                                        report.get("buyingPowerUsableByPolicy") is True))),')
    return replace(text, '    if result["securitiesOnlyCashReviewed"]:',
                   '    if result["securitiesOnlyCashReviewed"] or result["rssFundingSelected"]:')


TRANSFORMS = {
    'tools/no11_live_ui2_readonly.py': change_ui,
    'tools/no11_broker_execution_service.py': change_service,
    'tools/no11_received_session_bootstrap.py': change_bootstrap,
    'windows/Run-No11ReceivedSessionOperatorLive.ps1': change_operator,
    'windows/Start-No11UnifiedLauncher.ps1': change_launcher,
}
ADDITIONS = {
    'no11_rss_buying_power.py': 'tools/no11_rss_buying_power.py',
    'no11_make_rss_live_config.py': 'tools/no11_make_rss_live_config.py',
    'No11RssFundingContract.ps1': 'windows/No11RssFundingContract.ps1',
}


def transform(name, data):
    text = data.decode('utf-8').replace('\r\n', '\n')
    result = TRANSFORMS[name](text)
    if name.endswith('.py'):
        ast.parse(result, filename=name)
    return result.encode('utf-8')
