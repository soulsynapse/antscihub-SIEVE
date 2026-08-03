# How-to: get a PAR from Proposed to Accepted

This is hand written by the repo author. 

## HOW TO USE THIS HOW-TO:
It is highly recommended to execute this manually, as written. PARs are extremely important, and easy for agents to get wrong.

The double new line break is a gap for separate messages.

## Guide
*Start with stating which PAR you are working on*

This is a hardening session. Write the session file as you go. For the session file: be explicit about the outcomes at that point. The outcome, written with [STATUS] prepended to it. If it stands, keep it as STANDS. If improved, have it as IMPROVED. If overturned, have OVERTURNED. The type of the outcome should be prepended before it; for example, if a seam interaction is defined, have it as [INTERACTION][STATUS]. You can name these by the sections that are in the PAR itself. If a section is clearly warranted, you can propose it. A PAR should be written in plain language first and foremost. If repo-specific language or references need to be used, have them in parentheses. You should write your summary as such so that what makes it into the PAR doesn't inherit difficult language. Don't simplify, however. Keep it accurate.

Evidence first:
- Other systems that worked because of this seam
- Other systems that failed because of this seam
- Other systems that didn't adopt this seam and failed as a result
- Other systems that didn't adopt this seam and succeeded without it

Distill that: What the lessons from those systems tells us about this PAR, for this repo. Give concrete examples.
- What applies?
- What doesn't apply?

Now, stated specifically: the architectural boundary it defines. This is the most important part of any PAR. Everything else is up stream, downstream, within-domain-but-cheap. Don't scope a new PAR to deciding the internals of that domain that are cheap to change later. If it is all cheap, then it isn't a PAR.
- Define potential domains. For each: 
- Then define the parts of the domain that *must* exist for it to do it's job. What is expensive within the domain?
- What is upstream? What is downstream? What is cheap but internal to the domain?
- Shared upstreams and shared downstreams are a flag in your response: you scoped two domains together and called them different.
- Identical expensive internals are also a flag: you shuffled things around to make them look different.
- Don't define more potential domains than what genuinely fit. This could be a single domain. This could be no domain, and the PAR doesn't hold water. There could be genuine tradeoffs between domains.
- End with your proposed domain and why.

(Settle this with back and forth with the agent - establish the rationale for why the domain holds)

Tools for the back and forth:
- What is the diagram for how different things *got* to this architectural seam, and what are they? How are they adjusted internal to the seam? Then how are they omitted? Is there one or more loops the seam is explicitly responsible for?
- Say we make a figure to explain where this domain is. Is it consistent with all the other domains?
- Walk through howtos:
	- 
- The way you stated it above.. is that consistent with the other boundaries?

For the PAR specifically: what is the most accurate name for the system?
- Provide a list of candidate names with answers to the next two bullets:
- Is the name clear to the user: does it clearly identify the domain?
- Is the name clear to someone working in the repo: does it clearly identify the responsibility?
- Would it be confused or pattern matched to something else?

So what does this mean for working in the repository?
- What are the rules, as a result of this PAR?
- How does the PAR make it easier to work in the repository?
- What do the respository-specific how-tos that reference this look like? We don't need them written out, but what are their titles, and a 1-2 sentence summary of what following them does for someone working in the repo. Can those how-tos deliver on what you said they deliver?

What the end result is for the user?
- How does it make it easier for them to use SIEVE?
- How does it make it easier for them to trust SIEVE?
- What the component is doing to ensure other components are able to do their job efficiently and accurately?

We're starting to wrap up here. This discussion suggested a bunch of other domains and boundaries. You may have accidentally scoped them to inside of this PAR even. Which domains were detailed that don't have an existing PAR, but probably should?

Are any of those clearly in the domain of a PAR that already exists? Or unnecessary, because the boundary is cheap?

Lets do the diagram exercise for me again though, and name all the parts of the diagram by their domain/seam, not by how they interact.

So okay, good job here. We settled a bunch of things. For the session file: Outcomes that explicitly name debt should carry a debt marker, to be cleared on delivery.

Now write 

Now write what those PARs need to include 

So lets give this a final summary here: why MUST the architectural boundary exist the way we said?
- What it costs to not do it that way
- Why the seam is natural