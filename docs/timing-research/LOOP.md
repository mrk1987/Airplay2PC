# Timing investigation - 2026-11-02

I investigated whether a native Windows receiver could keep time with an
AirPlay group. I kept the working audio path in place and used silent tests
for the experimental clock and anchor code.

The investigation ran for four rounds, covering packet handling, anchor
semantics, clock fitting, replay, output-clock mapping and drift decisions.
See [the evidence ledger](ledger.md) for the findings and source links.

The offline tests pass, but the remaining questions need real sender data and
DAC measurements. The experimental output backend isn't implemented yet.
The current receiver sounds in sync to me; that listening result doesn't
validate the separate experimental pipeline.
