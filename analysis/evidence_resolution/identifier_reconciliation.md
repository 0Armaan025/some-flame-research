# 193F001 Identifier Reconciliation (Phase 3.5, R5)

**Status: PARTIALLY RESOLVED (forensically characterised; identity not
establishable from the table; originator confirmation required — OQ-5).**

## 1. The two records (verbatim from the raw table)

| Field | Test 70 | Test 73 |
|---|---|---|
| FLEX Identifier | 193F001 | 193F001 |
| Fuel | Heptane | Heptane |
| Date / GMT | 3/23/2010 **7:25:43** | 3/23/2010 **7:25:43** |
| Ambient pressure | 761 mmHg | 761 mmHg |
| Composition | O2=0.15 / N2=0.84 | O2=0.15 / N2=0.84 |
| Initial diameter | 4.67 mm | 4.64 mm |
| Extinction diameter | 4.60 mm | 4.58 mm |
| Burning rate (unit unresolved) | 0.41 | 0.56 |
| Burn time | 1.6 s | 1.5 s |
| Outcome | Extinction | Extinction |

## 2. Series context

The `193` series on 3/23/2010 contains four table rows:

| Test | Identifier | Fuel | GMT | d0 (mm) | Outcome |
|---|---|---|---|---|---|
| 70 | **193F001** | Heptane | 07:25:43 | 4.67 | Extinction |
| 72 | 193R001 | Heptane | 09:06:37 | 1.13 | Completion |
| 69 | 193R002 | Heptane | 10:23:00 | 1.10 | Completion |
| 73 | **193F001** | Heptane | 07:25:43 | 4.64 | Extinction |

Both 193F001 rows (4.6–4.7 mm) are outliers within a series otherwise
consisting of 1.1 mm droplets. The F/R letter distinction recurs dataset-wide
(59 F-rows, 25 R-rows) but is **not documented anywhere**; no evidence ties it
to fiber vs free deployment, so it is recorded here as an unresolved naming
convention rather than interpreted.

## 3. Candidate identities and the evidence for each

| Candidate | Evidence for | Evidence against | Assessment |
|---|---|---|---|
| Two separate experiments (two droplets, one mis-entered identifier) | distinct reduced values (rate 0.41 vs 0.56); d0 differs by 0.03 mm | identical GMT to the second; identical conditions; two deployments in one second is implausible for one dispense cycle | cannot be excluded |
| One run reduced twice (two reduction passes) | identical timestamp and conditions; near-identical diameters (0.03 mm apart); differing derived values (rate, t) are exactly what independent reductions would produce | a duplicate reduction would be expected to reproduce rate/t; they differ by 0.15 and 0.1 s | **best-supported reading** |
| Duplicate row from an export | identical identifier/date/time | measurements are not identical, so not a copy-paste row | weaker than "reduced twice" |
| Technical replicates | two rapid sequential droplets | same-second timestamps | implausible |

## 4. Consequences for inference (quantified)

Removing either row changes the methanol-vs-heptane initial-diameter contrast
(Mann-Whitney, recomputed in `resolution_checks.csv`):

| Population | U | p (two-sided) |
|---|---|---|
| All records (n=154/108) | 7190 | 0.0623 |
| Excluding test 70 (n=154/107) | 7036 | 0.0450 |
| Excluding test 73 (n=154/107) | 7036 | 0.0450 |

The contrast crosses the conventional 0.05 threshold under either removal —
the Phase 2 "duplicate-sensitive" disclosure is confirmed and quantified.

## 5. Rules applied

- **No join on identifier alone**: all analyses key on `FLEX Test #` (a dense
  1–274 counter) with the identifier as metadata.
- **No renaming** of either record; no arbitrary choice of "the real" run.
- The collision is preserved as an explicit unresolved issue (OQ-5).

## 6. Reconciliation table (as required)

| Original identifier | Series | Fuel | Date | Available metadata | Telemetry linkage | Candidate identity | Evidence | Status |
|---|---|---|---|---|---|---|---|---|
| 193F001 (test 70) | 193 | Heptane | 3/23/2010 | pressure/composition/diameters/rate/time/outcome | none (not one of the 8 linked runs) | same physical run, reduction pass A | identical timestamp+conditions to test 73 | unresolved |
| 193F001 (test 73) | 193 | Heptane | 3/23/2010 | as above, near-identical diameters | none | same physical run, reduction pass B | as above | unresolved |
