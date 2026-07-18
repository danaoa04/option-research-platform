# Strategy Builder Guide

The strategy workspace lets you explore a fixture option chain, add legs, and
review research-only diagnostics before any historical testing.

## Supported beginner workflow

1. Choose an underlying and expiration.
2. Review strike rows, quote quality, and warning badges.
3. Select contracts from the call or put side to add legs.
4. Choose a strategy template or continue with a custom multi-leg structure.
5. Review:
   - payoff preview;
   - Greeks;
   - liquidity;
   - margin preview;
   - policy toggles;
   - diagnostics.
6. Save the draft for later research use.

## Strategies to try in fixture mode

- Bull put spread
- Iron condor
- Calendar spread
- Custom multi-leg structure

PMCC and diagonal workflows remain part of the documented product scope, but
the current fixture workspace is still a bounded research preview rather than a
complete production strategy editor.

## What to watch carefully

- Missing bid/ask values prevent a valid net premium.
- Quote quality warnings should be treated as research limitations.
- Assignment and lifecycle policies are research settings, not execution
  instructions.
- Greeks shown in the fixture workspace are synthetic previews and should be
  reconciled with backend-owned analytics before serious research use.
