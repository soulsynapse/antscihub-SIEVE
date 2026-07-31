# Charter

## Overview of what SIEVE is:

SIEVE (Signal Isolation of Ethological Video Events) should be able to do the following:

1. Following the pipeline's dag, execute all components of the dag and produce outputs.
2. Let the user intuitively tune that pipeline from the gui, setting parameters that are useful.

This is the bear minimum, and SIEVE can do a lot of this today. Most of the components are there, and the things that are not are relatively trivial.

## General sources of fragility

To get to this state, unfortunately the SIEVE codebase is pretty fragile. Some general sources of problems:

1. Filters are largely bespoke implementations, there is no standard runbook that can or could be followed.
2. There is no dynamic load balancing; everything is tuned to what the user configures, and the lagginess of the program tells them to reel it in, or it was written for the author's (fairly beefy) dev machine, which is by no means a useful standard to measure anything against.
3. There is no clear separation of responsibility. There are gestures for it, but the enforcement was ignored to get to a working MVP.

The reason these are problems are listed in the next section.

## Current SPECIFIC weaknesses

These are limitations of the codebase and product today.

**Specific programming limitations:**
1. Adding a new filter in the code isn't intuitive. Right now, the process of adding a new filter needs deliberate testing of stress on even just the dev machine, let alone all the other user's machines. Then validating that it works how it is supposed to is totally unclear. It has to be as painless as possible to add new potential filters to the codebase as possible, so that the tool can be extended easily.
2. Adding new filters or changing *any* functionality has no benchmark capability on how adding that functionality hurt performance; there's no feedback on where to improve the code and why.
3. New future tabs are either overloaded with requirements or can be scoped to land or invent new things to begin with.
4. New future tabs, and even current pipelines, have no proper way to inherit the decomposted complexity without huge cost.
5. The complexity of the codebase makes agentic programming in it pretty fragile.

**Specific user limitations:**
1. The user's workflow is very fragile. They might make a crop, but the crop prevents things, or gives them more lag than not cropping, or they initiate a crop and then their workspace is laggy.
2. It is unintuitive to the user what they *should* do if it isn't already on the screen. I wrote it, so I can drive it, but a naive user would not know where to begin.

## What is exposed by these problems, and the shape of the solutions.

These are the shape of the solutions, but not necessarily the solutions themselves. There are clear open problems that can resurface (such as naive reinvention or reimplementation) that aren't addressed here. The refactoring isn't meant to suppress harmless reinvention, it's meant to prevent harmful reinvention and fragility. However, by 'shape of the solution', any substitution inherently addresses the underlying principle of the numbered sections below.

First, that the codebase doesn't organize itself by things that don't need to be touched again. Things frequently need to be reinvented. The codebase should function as self-announcing toolbags; when you want to add a type of thing, it belongs in a folder. The things that make up that type live next to it. The end goal is to have lots of types, and that's fine: for a tool of a specific class, having a large grab-bag is fine. Sometimes something that needs to be done needs to reach into many different bags, and that's okay.

Second, the specific things to compose *for* are ill-defined. If the way the codebase is organized is meant to represent tools for what SIEVE needs to achieve, then those things that can reach into bags and need to work with each other are poorly defined. These are contracts. As a kind of.. meta or 2.5, how the SIEVE GUI and CLI operate is a type of contract with the user. The ux is how that contract is made apparent. So even the GUI needs a contract of sorts, because ultimately the user's expectations and knowledge of what they can do serves the exact same role.

Third, how those contracts interoperate and rely on each other is ill-defined at best, or left up to chance at worst. The executor may need to know how to potentially manage things, and subservices of the executor need to know when they need to be automatically doing things too. This means that we don't just need an execution layer, but we need an execution layer that routes tasks to get information to orchestrate many things together.

Fourth, and what falls out of well defined contracts, is the reverse: imagine we have well defined things to compose for- how do they know what tools they can reach for? This is the __init__.py for the different package folders. We can help buffer against reinvention in two key ways: first, when we can, we put everything it's proper home. Second, we allow and welcome the proposal of new homes by agents, often and freely. A new home that doesn't hold it's weight will stick out and eventually make it's way to the right space, or genuinely make a new place for similar things to live. Neither are nearly as bad as a bespoke function that hides somewhere it shouldn't.

Fifth, then, is how to not reinvent the wheel. There are a number of ways here: runbooks, golden fixtures, etc, but the general shape of this isn't to disallow practices or overly constrain things, or force beaurocracy. Instead, it's to show how to do it, and have ways to clean up if the examples aren't followed.

Sixth is: how to keep what we fought for. The tests previously were pretty fragile, which yeah, less than ideal. We want a robust testing framework that won't die once anything is refactored.

Seventh, finally, is that the components that underlie all this, the invariants between them, are at the root of what SIEVE is, and define the most important and loadbearing parts:

1. SIEVE's pipeline DAG is everything. It breaks, everything breaks. Something that doesn't enable something for the pipeline, it is outside the scope of SIEVE. These are:

a) The pipeline itself, the inherent ability to execute from an input and produce outputs that are reingested or built upon.
b) Saving and loading a pipeline; right now most need to be tuned by hand. A pipeline that is built to be reused is exactly as useful as the rate of the redeployment.
c) Pipeline components: we've been calling these filters, but it is likely worthwhile defining what *any* section of a pipeline can be, so that if it reaches the actual DAG, it meets the requirements by construction, and doesn't overcouple what goes into the pipeline.
d) Tuning the pipeline, the user's entire load->measure->tune->load loop. This is fundamentally mostly the GUI, and I needed to get it right, which is why the filter tab is a god object right now.
e) Outputs of the pipeline: these are basically afterthoughts right now, but the shape of them actually shapes the entirety of how extensible the entire product is; different parts of different pipelines ingest different things.. I'm kind of vaguely gesturing at something, but this also means that the shape of SIEVE right now, which requires a video as an input, is actually a limitation; a well defined final product may not be limited this way, and it is a known limitation of potentially having background subtraction as a type of pipe section.

2. SIEVE *lives and dies* by it's ability to measure speed. This is not hyperbole; it is quite literal: there are other tools to do what it does if it is missing this. A version of SIEVE that only runs on some machines is a SIEVE that is ignored by any user that cannot run it. SIEVE being unable to provide the user metrics for how long it will take if the user runs a given pipeline on their laptop compared to an HPC provides absolutely zero insight into how feasible a detection project is-- one of the most important objectives of SIEVE. When SIEVE freezes parts of it's GUI due to some resource hog that runs rampant, the user experience degrades proportional to SIEVE's inability to respond to that constraint. It is the universal tool that every single part of SIEVE touches, and earns it's status as an invariant.

3. SIEVE's usefulness as a tool is exactly equal to the user's knowledge of that tool. This means that any functionality that is not visible to the user from the GUI might as well not exist. Even if the backbone of SIEVE works, anything intended for the pipeline that is not a part of the GUI is fundamentally incomplete, and loudly announces the work left to be done on that feature.

## Summary

The codebase and SIEVE itself organize as a mirror of each other. Working in the code base is very close to how the user works with SIEVE. A good codebase shows the tools available, so SIEVE ends up easily extensible. SIEVE itself shows the tools available, so the user ends up using SIEVE in a way that extends their own capability.
