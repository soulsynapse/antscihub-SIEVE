## Vision and notes

This document is for my own thoughts on the process. It is not binding, it is just a list of thoughts for potential ways to implement things and things to keep in mind.

## User layout ideas

- Use logic gates to combine tools. Can probably be icons below the card maybe.
- Properties to join.. either the property comes first or the operation?
- Signal to user when they're not picking up something that is basically free?
- Add decode speed on player somewhere?

## Thoughts on decode

- Decode is usually expensive.
- A lot of "tag along" information can be picked up roughly for free - probably should make an option for the user to capture that.
- Different types of decode can buy a lot of speed.
- Materialized replicates are only worth it for user tuning speedups. Some ways to make it snappy:
  - Only materialize the user's loop window
  - Keep the user's crop's loop window in memory, if possible.

## Thoughts on truly cheap types of operations (Tier 1)

- Most things that can be represented as RLEs, especially bitwise RLE. Adding a few more to an RLE isn't bad either.
- Full frame reduction, anything that collapsed the image to numbers typically.
- Most pointwise operations: one pixel, no neighborhood. Integration, thresholding, absolute difference, **look-up table remapping**, MHI decay step.

## Thoughts on other frameworks

- JAABA encodes some good information

## Other tiers?

- Retaining image detail? Texture?
- Signal amplification?
- Temporal sampling?
- Downsampling?
- Aliasing?

## Overcoming limitations

- Figure out if you can pin point the window when it happened, then use more expensive tools on just those windows if necessary
- Downsampling regimes can *improve* signal (e.g., overcoming compression artifacts)
