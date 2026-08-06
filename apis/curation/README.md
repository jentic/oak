# Curation denylist

`DO-NOT-READD.csv` lists every API entry deliberately removed from this
directory, with the class of removal, the evidence trail, and the exact
condition under which it may return.

**Any importer — human, script, or agent — MUST check this file before
adding an API.** These entries were each verified dead, junk, private, or
misattributed by a two-step evidence process (curation ledger + live-web
recheck) before removal; re-importing one from a stale mirror, an old
aggregator listing, or a cached spec recreates work that has already been
done and re-publishes content that is wrong.

An entry leaves this list only by meeting its `readd_condition`, with the
revocation recorded here and in the curation ledger
(`api-catalogue-content`: `api-knowledge/corpus/spec-actions.csv`).
