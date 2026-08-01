# SIEVE rewrite — design brief

Kendrick's prompts from the pre-rewrite architecture session, 2026-07-31, verbatim
and in order. These are the requirements and constraints in the author's own words;
they are the source document, not a summary of one. The reasoning and conclusions
that came out of the exchange are in [DESIGN-SESSION.md](DESIGN-SESSION.md).

---

## 1 — Contracts that can change

This folder is for a rewrite of SIEVE from scratch. For now, you don't really need more information than what I'm going to be telling you and I mostly want to just be talking about how to write it so that it works well, and it's extensible and has beautifully maintained code. Everything should be clear where it belongs, with well defined interfaces, boundary rules, and ratchet thresholds, ledger diffs, among other things, but we'll get there. I have most of the answers here but when you're able to derive the correct answer from my hints, I'll know that the architecture will be clear enough that I can trust much of the construction to agents. The end deliberable of this session is an architecture.md file that is no longer than 

SIEVE operates as a pipeline of steps and a GUI, and it's primary deliberable is Signal Isolation of Ethological Video Events. Don't worry too much about the ethology component right now, that's what the user knows about and SIEVE itself makes no opinionated design choices for it, at least for the rewrite.

The pipeline is the run order. Its so the program has the information it needs to serve things up to the executor. The pipeline file owns the complete or incomplete steps the user chose.

The pipeline itself has a contract because all the parts of SIEVE depend on everything else being able to play nice with each other. I think the contracts need to be able to be updated without everything breaking, or we will be hand writing everything until the end of time as new functionality lands. Any idea on how to do that?

---

## 2 — The GUI, the step's ownership, and navigation

That more-or-less makes sense. let me just explain more of the software before telling you stuff. One open question is what to call the "steps" of the pipeline because what any given step does and needs to do to interact with other stuff can vary pretty wildly.

The GUI is pretty simple. On the left, there's a context viewer; since the first step is to select what folder or video they want, the first step of the pipeline is to pick the project basically, so there's no video on the left, there's just information on whatever project was selected by the user. A lot of the later steps, there's a video viewer. The video viewer just displays whatever any given step tells it to, same as the project viewer. The rule of thumb is the left is for representing the result of the configuration, and the right is the configuration. So the pipeline at minimum gets a video file from the users selection, and then in the GUI the user selects a step, and the video player shows the user the stuff relevant to that step. For the first step we are just making a crop utility. So on the right, there's crop tools pretty much entirely owned by the step, and on the left, there's a video player and ways the user can draw on top of the video player to draw boxes for crops.

That means the step has a contract and a bunch of things it can pass off: some standard ways to pass the information over to the video box, if it wants to, ways to get the users interactions passed back as parameters that are saved in the pipeline. It also takes SIEVE preferences too. It then defines some outputs or possible handoffs. like for example, the crop can either be pure information - just coordinates, and that's inherited by the next steps, but it can also actually do stuff, like run the crops. At the later steps, the steps themselves can define which of those they accept and if the crop gives multiple, the user can pick which they want. Or swap between them.

The navigation for this is pretty intuitive. You're given the step to build the pipeline, and you press the up arrow or down arrow to swap between steps. Since it is a dag, you press left and right to swap between equivalents at the same level. So if you're selecting a specific replicate you cropped, once youve got the replicates set, now it has equivalent options for each crop. And that's it - the subsequent steps don't know anything other than what they're given. When a user presses down to a new step, it starts with the list of things that have their requirements fulfilled. does this basically make sense?

---

## 3 — Downsampling, and the inefficiency that lives between steps

This is all fine. The implementation best practices is what I'm leaving to you. If the crop step lands the way I said - as a contracted step -  and works flawlessly, that's already a major milestone and defining moment that signals there won't be another rewrite ever again. I'm going to crack a beer once we reach that point lol.

The next step id want to build out is the downsampling step, because it is a great exemplar of what steps have to be able to do to work together. Not every user is going to want to downsample. The cropping step is a major milestone and how building out the downsampling goes is going to be the first hurdle.

I mean there's already a ton of decisions implied by it right? Stuff like.. how does the user want to downsample? Should it really be its own step, or should it be an extension of crop?

I already know how to solve this problem, but I want you to name it. The decomposition of the steps the user constructs resists basic DPP construction - the combined step captures efficiency that is in neither. We are on step 2 and have already uncovered this inefficiency - imagine when a pipeline has 10 steps, and that inefficiency is compounding each step. What do you think the solution is?

---

## 4 — Displaying a multi-input, sequentially-computed result

Yep! So now imagine if we did the cropping and the downsampling - nailed it. We add the background subtraction, and yeah it more or less works. Here's the question: are all the contracts respected? Say I had an agent like yourself write it. The pipeline defined what the UI showed the user, the user picked stuff to parameterize the pipeline in discrete steps, which are secretly fused at the executor, who has two jobs. We are at step 4 with 4 tasks (crop, downsample, bg subtract, track), and while two can be written to be combined (nice), what about the case where the user does background subtraction and then... something else? Or does the crop, downsample, then... dense optical flow? or morlet wavelet over appearance energy? Or threshold detection over change energy to isolate blocks of interest, and then do bg sub tracking on that?

You said the executor needs to have two methods, but you didn't say who *owns* those methods. The potential operations the user might request can combinatorially explode for each new feature - can the step contract own them all? How does the GUI know what to produce, or reuse?

I know the answer. What do you think it is?

---

## 5 — Ownership, and the maintainability rejection

Yes, the way you suggested it, I suspect an agent would write spaghetti code every time. I suspect even an experienced engineer would write something very fragile that ends up being a headache for anyone else who works on the repo in the future. Your solution makes extending the repo a headache for all future edits. It's a good thing you wrote it as your first draft. Try again. What do you think the maintainable solution is?

---

## 6 — It was a maintainability problem; why the explosion never materializes

So go look at my prompt again. I posed it as a code problem, but it's actually a maintainability problem. If it isn't clear where everything lives, then the thing that needs to get written allows the agent to reinvent everything it needs to be written. The solution is hidden in what you wrote before: steps are derivative of the executor, and the context is pretty to easy to find if the executor is coupled to the kernel. That makes it so the step contracts can request anything it wants from the executor, so as the capability of the kernel grows, the executor offerings grow, and the possible steps grow.

But there is still room for optimization. I suspect the phrasing I gave you implied an impossible task: combinatorial explosion isn't going to be optimized automatically, it would require an engine that can solve every problem automatically - what you responded with was like the first steps on a road that would rebuild Mathematica. But consider this: even if every combination is *possible*, why arent most combinations utilized? And by the construction of the pipeline, why are all the products reachable?

---

## 7 — The unifying mechanism across every boundary

You're almost there. The answer lies in how the kernel talks to the executor, how the executor evaluates what it gets from the kernel, and how the executor talks to the pipeline step, and how the pipeline step evaluates what it gets from the executor. Consider that the executor wants to prefer the fast path from the kernel, but the fast path for some exist conditionally - for example if I make some kind of change energy tensor, depending on what there's a need for, there could both be a fast path for change energy over morlet, or appearance energy or LK as a derived result.

There are a few software architecture approaches that allow the fast path to be captured automatically once the fast path exists, without crippling the slow path. Some of them are better for repo maintainability than others.. and the best solutions make everything easy to extend, and has the entire engineer team feeling like everything was easy and nobody really knows why. There's at least one unifying approach that bridges how everything is written: pipeline to step, step to GUI, user to adding a new step, kernel to executor, executor to step. I can think of two decent candidates actually. What do you think they are?

---

## 8 — Kendrick's answer: verified statistical equivalence

Haha, okay, let's add that last question to the list too. I think your answers might be better than mine, but I'm not sure. My first answer is that the answer equivalence, or signature of the solution that was made, requires that the inputs are tested against a reference object, maybe two or three, and any signature has a statistical test for how different any one solve is from another. Then for any method written, they have to declare what it is doing and eligible types. This is the natural bridge between each; it gives the executor the ability to pick, it gives a clean test for how much the fast path is actually useful, it provides the building blocks agents can use when making anything. These can be mathematically clustered too. So now you have the signature of everything that gives you the output you want, and when two things are identical, now you know to evaluate them for merging, or separately, flag them for why they should stay separate. When a fast path declares equivalence to multiple other paths, that's checkable. Then the executor just picks the result working backwards based on its speed ranking.

The second solution might be easier to understand and implement in practice: the executor checks the joins for every possible joins that exist in the pipeline, and matches them in a clever way against fast paths that exist. Basically, the interpreter or handshake approach. So the fast path or potential path self validates and is preferred because it already exists. This was one of my answers but it is only nice in the short term, I fear, and I was pattern matching to plugin architecture, where features can be written in isolation.

--------EDIT: Written in a separate section with Claude 5 Opus Max
The second solution is easier to understand and implement in practice and just frontloads the responsibility and leverages correctness and availability of agentic problem solving being nearly free, but expands scope to include unknowns. A registry of characterized equivalents is good and all but it pretty strictly defines the scope, and this alternative allows for effort into optimization to scale with demand, allowing a responsive architecture at the cost of long term maintainability. It basically states that there will be a rewrite (or a targeted branching off, if one function comes into particularly high demand), but gains agility and freedom on top of a standardized interface. SIEVE transitions to a bunch of scripts ductaped together. This bets on the pipeline type usage being absurdly lopsided, and rejects investment into infrastructure that isn't proven to be needed.

---

## 9 — Disarming the objections

Disarming your concerns:

1. Tolerance doesn't compose in *every* scenario, but it isn't a problem. Dynamic systems become chaos only by sensitivity and folding. Sufficient damping can create the well behaved system, and history dependent sensitivity are going to be known when the feature is added. That's one flag in the contract and the problem is gone.

2. Yes, but it actually highlights the dual value to the user. This also potentially gives the users the ability to test for equivalence: some manipulations to footage will also be able to create statistical similarity, and that could be what the user desires. In fact, it will often be the case that that is what the user desires.. and the tooling that helps the executor pick the defaults is the same tooling that the user can run on their derived pipeline step to discover a trick to turn a massive computational task into a trivial one. For example, frame decimation equivalence in detection where 1 frame per 3 minutes gives statistical equivalence to 30fps once the detection thresholds on the channel discriminator runs is how SIEVE turns into a tool of convenience to a hypothesis discriminator that enables the 6 month video recording study to actually happen.

3. You stated this as a problem and it just became a valuable feature. It is the 3rd valuable use of the implementation.

4. Yes this is a known limitation - your solutions are why the statistical equivalence is the discriminator.

Make sure all of my messages are in the markdown doc - it was written as questions.md but let's call it something else. Then let's make a second one that is essentially transcript, that details this whole session.

---

## 10 — The signatures are a baseline, and the call for the write-up

Agreed. And at the risk of getting a little too cute here, they're tests, so if you change how something is written, now you have a baseline in the git history you can compare automatically.

So this more-or-less settles what the program looks like in the end. For an agent or engineer with perfect knowledge, if SIEVE were written as described, it would come out perfectly.

We haven't decided on the shape of the repo yet, just the fairly abstract major components, and it is pretty simple how they all interact and what they do. Let's write that up, keeping it clear and easy to understand. I'm very clear on where we landed and I want you to write the < 2pg explanation.

---

## Housekeeping messages

Kept for completeness; no design content.

> You can author the commit.

> You can make the commit for the rewrite branch.

> Oh, update the transcript and my messages file and commit again
