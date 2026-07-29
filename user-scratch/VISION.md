---
status: record
---

# SIEVE vision

> **Dated record of intent.** Written before the build; not maintained. What
> was actually built is in `completed-todo/`, what is measurably true is in
> `findings/`. Divergence from this document is expected and is not an error —
> supersede it with a new dated document rather than editing it.

## Overview

At it's core, SIEVE is about applying filters. The absolute bare-bones, pre-optimization version is like this:

1. You have a video file in a folder, and transformations live in subsequent folders.

It does not matter what kind of video file, what preprocessing it has, what encoding it has, SIEVE should be able to ingest it *as is*. The user knows what the folder is, SIEVE doesn't need to know really.

You then apply transformations to it, and again, in the *unoptimized version*, that transformation goes into a folder in that directory. So the logic is clear: you have a source, you did something, the result of that lives in the child folder.

SIEVE should be able to do this for any of the tools that live in the filter tab. It might be making a specialized background subtraction. It might be creating an output video with a mask that only lets through a specific color. It might be the coordinates of that specific color as a csv and enough information to stick it into R. The v1 of SIEVE had it so that you could set morlet wavelet bands, downsample, set pixel block sizes, set thresholds for how many pixels when averaged over time you wanted to count as a detection, and it could do all of that.

But in the simplest, dumbest version of the program, in a way that you can see absolutely everything that happens by navigating folders, each of those would be it's own folder. This would be like an image processor saving the entire processing history to individual files, so that when you have completed the first step, the 2nd step does the thing to the output of the first. Image processing doesn't do it that way because you don't necessarily need the inbetweens, but ideally the user should be able to do that if they want.

2. You crop to replicates

This is a pretty universal step, but is totally optional. You have a cropped replicate, and you can navigate forward and backwards in the replicate tab. This is already built out into SIEVE so it's not a problem. It exists as part of the DAG, however.

3. You filter the video.

Keeping with the theme of progressive, layering complexity, below is the next step for elaborating the workflow, but is still relatively simple/dumb, by design. Filters have a ton of different kinds, some of the main important ones for video:

A. Signal/economy interaction filters: Image pyramids, dropping channels, downsampling, frame decimation, pixel blocks and other sampling techniques, blur filters of various kinds. Note that some of these improve signal *and* economy in many situations.

B. Channel filters. Channels might be in the data, and it might be what you compute. So rgb, whatever is in the video, or some kind of computed derivative - optical flow, change energy, etc. The key part is channels are all the information in a single frame. A channel *filter* is when you set acceptance criteria for something downstream.

C. Temporal filters (1d temporal and 3d spatio-temporal) such as IIR, wavelets, frame decimation, MEI, MHI, temporal integration, 3d wavelet transforms.

Note that these things can be done before or after: I could take the optical flow measurement at 1:1, then do the optical flow measurement grouped. I could do a temporal filter on the channel directly (without any filters for thresholding), or do it on the thresholded channel. The order significantly shifts the outcome. But in the dumbest version of this, you do one thing, save it to the whole video (sure hope you have lots of storage), and the downstream is deterministic because it doesn't need to know the stuff above it. At this stage, you don't even have a gui to help you, so it's bumbling around in the dark. Huge files, huge processing overhead, no feedback at all until it's done.

4. You get a gui to tune these things in real time.

Now you have a timeline of the whole clip, but you limit yourself to like 5-10 seconds of it, on a representative part of it chosen by you. As you do transformations, you get feedback on how fast/slow that representative transformation is from the benchmark. This way you're not inherently limited to certain workflows. The multiple transformations are stored in live memory somewhere, so now you can apply multiple things at the same time. When things start getting slow, you can save that representative few seconds to the child layer, and because things are deterministic, it still represents what you're trying to do. Feedback from the benchmark gives you an idea for how expensive things are getting in terms of storage, compute time, required memory. Theres also some kind of information on how much space even just testing is taking up on your storage. You can buy back economy by decimating the video, saving the decimated video, and now you have a huge amount of compute to play with, and you can get some idea of how bad that hurt your ability to process the signal.

The gui gives you a few specific things: the representation of the video, the order of operations, the graphical representation (where you can choose from a few different ways to view the data.. summed total for a given frame, for example, but representative of the specific operation you're looking at. For a given operation, something like 'filter the hsv channel' there are buttons for tools specific to that filter, like a clicker tool to click the video and see how the color is represented in the color space, and handles on that color space to show where you want things cordoned off.

So you have 1: the video which is playing in the time-constained representative clip, 2: the overlay of that video which can switch between transparent (so the user can see the raw video), some kind of overlay representation showing the whole of the current state if you include all the operations, a third overlay showing the relative representation the current operation has on the one immediately before it, then 3: a top toolbar similar to stuff like fusion, word, photoshop that have buttons to implement things to the timeline, 4: the operations history which has stuff like saved to child (frees compute and memory, consumes storage), filter operations like downsampling, computed channels, etc. Then 5: to the right of that filter operation list there's information on the specific filter applied, the live graph with a vertical bar showing where in the 5-10s clip is represented on the graph. To the right of that, theres a few buttons: a) adjust visualization which makes a pop up wizard with options like log transform, change to a different visualization, etc), b) refine, which allows you to do the selection stuff I mentioned (which, when done, is just another operation on the operation list), and then 6: a benchmark summary of what the specific operation costs you.

So with all of the above, you have a comprehensive filter suite that lets you isolate and refine signals over time in a way that you can get direct feedback, progressively see how much it is going to cost you, etc. You can rapidly isolate signals based on signal theory and all of these live in modules so that if I want to add operations over time, it isn't difficult.. if you know how everything works.

5. The GUI guides you

So the user isn't going to know how everything works necessarily, but the key part here is we just bought a bunch of active feedback for the user, now we refine that feedback so that the many options don't overwhelm them.

Given that we have the benchmark information, and can generally know how the different things work, sometimes you don't need dense optical flow. So this is why the 'current operation' step gets a decent amount of screen realestate: users can scroll down from the pure information on that operation and see explanations, alternatives to try, and useful next steps. Information on what this step tends to buy, information on what this step doesn't buy, what isn't recoverable with this step, which formulas tend to work well with it, all that. These actively either try to swap out things or not.

When your memory use is getting high theres some kind of thing in the gui that suggests doing a compaction step - saving to a child folder, at least for the representative clip. It gives you feedback on how fast the video with overlay with graph is going compared to real time which is indirect feedback on compute overhead. But then what does the user do with it?

6. You create outputs

Once you've got your whole timeline, now you need to output everything. This is the final step of the workflow: since the different steps compound, the user can save the video representation of it, maybe tweak how the representation is shown a bit, or select a specific stage to output data to analyze. They can also go to some kind of HPC wizard that will help them with the commandline options - the user might do a compaction checkpoint for their local machine on the test clip, but provided the HPC memory capabilities, storage availability, cpu and gpu access, thread utilization, etc, maybe they don't need to. so the hpc wizard lets them toggle off stuff like a compaction state, or other things. Then tidies it up for them to hand off. Alternatively, the user can opt to do it all on their local computer with something like 'process whole video' and it'll pop up with progress on how that's going. Most projects won't need HPC - SIEVE should just be HPC ready.

7. Review outputs

Something like a processing report and durable results should be the end product. The ability to see the detection blocks, or the background subtracted footage output, or scrub the timeline to see when detection happened or not. This is a first class tool to interpret the outputs after the program runs.


So all in all, you have an intuitive workflow to completely isolate the signal based on replicates, and view the results.