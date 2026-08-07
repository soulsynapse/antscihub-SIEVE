# VISION v3

The reason for v3 is to make the repo easy to grow. v2 works, and works well, but the way the code is structured, it is faster to do the refactoring here.

The ideal case: everything makes it over from v2, but specific boundaries are enforced, and the missing components are integrated from the start:


## Features, and why I want them:

1. Tool *contracts*. If cropping is a 'contract' from day 1, then the hand off that it needs (ability to draw boxes on a canvas, stamp tool, etc) can fairly easily live on a separate tab, *or* live as a tool item itself on the 2nd tab.
2. Stereotyped GUI features. Tools say how they're populated, mostly. This makes tool build out much faster.
3. Terminology change: Tools, not filters.
4. Way less bloat from comments and docstrings. This alone was like 50% of the repo last time.
5. Adding a new tool should take a few hours whether it is the 5th tool or the 50th tool.
6. There seemed to be some problems with how detect could or could not be a tool last time. That needs to be resolved.

The end result is that tools are most of the customization surface: if you design what is in the tool folder right, it should work with SIEVE. It declares what it wants, and what it can emit, etc. It should be intuitive for users to wire things up.

Done correctly, I will be able to rework the GUI in an afternoon with the help of Claude. All the mappings and dependencies should be non-confusing and clear.

