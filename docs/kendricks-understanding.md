# Kendrick's understanding 

This file is my understanding, updated as SIEVE develops. It is current to the commit that last edited it. It is not perfectly accurate; aspirational is mixed into reality.

It is how I am keeping track of how SIEVE works, in my own words. Agents do not edit this.

## List of dev techniques:

Unexhaustive.

- Experiment-to-live. Reasoning around things that don't exist is how unusable things get built.
- Mock up for GUI. This is how I get the general feel down.
- Rebuild from deletion. Code components have strong boundaries, it is easier to rewrite the file than figure out how to carefully edit it.
- /tighten once parts are built. Kills the design essays. Use fable to recover stuff that was over trimmed.

## Basic parts

SIEVE has basic parts that talk to each other. The way that these things talk to each other is strictly defined by design. Each part can be thought of like an organ: each of these needs to do it's job-*type* well, and it needs to be trusted by all the other parts.

It works through two mechanisms:

1. Contracts to standardize things
2. MCP reference for those contracts for how to build things.

## Contracts

Contracts are built by construction. For example, a tool family contract needs to provide a GUI component. How that GUI component is included in the tool is provided by the GUI primitives MCP. The GUI primitives MCP is possible because of the GUI contracts.

- Tool contracts. Different tool families get one contract apiece.
- Edge contracts. I have to talk about this because I'm still fuzzy on it.
- GUI contracts. This includes: 
  - Canvas: how it reports user clicks, how it sends slider information.
  - Primitives: How primitives talk to tools.
  - Cards: How cards get populated and where? I guess?
  - The seeker bar: how it talks to the source or anything else that needs the timeline.
- Other features that might need contracts? Resource pressure and availability reporting/rebalancing? Storage, which isn't really different? Parameter ports?

## Seams

Seams are in the Parnas sense: they hold a secret other things don't know about.

This means that something like a source node has distinct outputs, so all the FFMPEG filtergraphs can live within a video file source tool as subtools because that is how it is going to get grouped anyway. That part is needed for efficiency: all the things needed there that nothing else needs to know about is in service of what it is doing, and it removes all the complexity needed of splitting how that happens across a dozen tools by keeping them under the shared lowering. The video file source tool outputs frames for all the other tools but what shape those frames are in is decided by the video file source tool.

Tools can live externally, but for convenience, a number live next to the SIEVE src. Source tools tend to share functions, so there can be some kind of common functions folder for source tools. This should probably be true of the other tool families too.

Fuzzy understanding: SIEVE makes hard seams at folders and soft seams at files between folders. I think I want stuff in folders to follow some kind of contract so it can be standardized to the MCP but I'm not sure yet. This is definitely true of tools. If this is true of the GUI or Experiments, I am less clear.

### Stuff to build / hasn't been built yet

- Automatic agentic MCP reference. Would be really valuable.
- Organ design.

