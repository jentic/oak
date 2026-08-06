# Curation denylist

`DO-NOT-READD.csv` lists every API entry deliberately removed from this
directory, with the class of removal, the evidence trail, and the exact
condition under which it may return.

**Any importer - human, script, or agent - MUST check this file before
adding an API.** Re-importing one of these from a stale mirror, an old
aggregator listing, or a cached spec recreates verification work that has
already been done and re-publishes content that is wrong.

An entry leaves this list only by meeting its `readd_condition`, recorded
here and in the curation ledger (api-catalogue-content:
api-knowledge/corpus/spec-actions.csv).
