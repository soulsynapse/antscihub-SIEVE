# VISION.md
This vision document is a log of how SIEVE works and how I want it to work. The end goal of the vision document is to be the intuitive explanation I share with people.

## Intuitive explanation, written pre-period tool 11/20/26

Here is the simple explanation of how I envision SIEVE working.

SIEVE works with separate "items" by their keys. Keys are functionally their own item, and it makes it so that each piece of the pipeline is independently checkable. The verifiable ('caveman') way to do this in CV is to take large footage file, then make static area crops of the footage, and run the pipeline on those crops. SIEVE allows me to do that without having to make the cuts, or I *can* make the cuts, and the results whether I make the cuts or not are typically very similar (acceptably close). But I get a very significant speed up. The speed up is what allows me to carry heavier pipeline tasks on the smaller crops.

The way I want SIEVE to work for periods (temporal cuts of footage) is the same way. I can run one pipeline that determines which parts of the footage to pay more attention to, then the temporal cuts allow me to conditionally run a heavier pipeline on just the temporally cut sections that were determined. The same as before holds: the caveman way to do this is to find those times, write a script to cut those so that they're keyed to their timestamps within the larger footage, then do heavier analysis on those heavier parts, and then fold it back up to have an intact pipeline where I don't have to do the heavy conditional analysis on the whole footage.

Heres where it gets messy. I want tracking to work the same way, but as a synthesis. The 'caveman' way to do this is to make tracking work such that outputs tracking that is only one individual and doesn't make any kind of determination for when merge/loss events happen, and build it so that it can be built cheaply and accurately. These trackings would be saved as individual files so they can all essentially be folded back up. Then I would want the ability to characterize the tracked individuals the same way SIEVE does the rest of the pipeline, but this is a shift from "doing some image analysis on video" to doing analysis on what was tracked. The rest of SIEVE works because the user can intuitively see how the analysis is going, but the way SIEVE currently works (one plot representation per node) is starting to crack at the seams because I suspect tracking is a different beast.

The implementation of tracking to work with the current runtime - the runtime evaluates which nodes exist, what a node may read, how rows are walked and kept, and what one node hands the next. This generates the raw tracking just fine. This can decompose into the "caveman" components similarly: a continuous tracking can be exported as a moving crop over time. The properties of that crop can even be used to qualify or disqualify the detections. This is the "region" tool (static spatial crops) plus the period tool (temporal crops) plus a crop that moves, which is the tracking.

I can even imagine how to represent this to the user, since doing analysis on each of those is just a temporal crop and a region crop. A temporal region crop is not too far off, and multiple temporal region crops are not an unreasonable extension.

The above seems very doable. The next step is to compose these together. This is also a reasonable extension: if I have something like change energy, I can have a detection band for one threshold that makes temporal segmentation, and I can have a detection band for another thing like "color present" or maybe direction, and this is another detection output. Then I can say "where the threshold is crossed for both of these at the same time is what I care about". This allows me to compose two different detections at the same time.

Where I am getting lost in the weeds a bit is how to do this with tracking. I can say something like "two drops in detection at the same time and the emergence as another indicates a merge event, and I want to detect that temporally and spatially, which creates the "caveman" output for a social interaction. What I'm worried about is where it starts to break down: say I have two that merged, and a third joins that merged one, then one leaves. If I have the end of the social touching event be "one blob too large to be a single individual splits off/jumps in size for a new one" then I'd have to handle how that remaining blob that still has two ants connected is handled by the detection.

What I think this means is I have to build the temporal piece first (period), and then the tracking.

This is just lookahead for development. I think what this means is the tracking plan should be revisited later. The atomic unit of this appears to be converging on one thing: a subset of (x, y, t) that carries a reference to what it was cut from, each of which contains it. 

- The region tool is a cylinder, a fixed mask over all frames
- A period is a slab, the whole frame over an interval
- A region in a period is basically both
- A track is a tube, a moving mask over an interval

SIEVE's final form, I think, is the ability to do these together. So say track ∩ period is a segment of a tube. Several temporal region crops are a set of tubes.

For keying, a cut that only restricts and doesn't renumber probably saves a ton of headache on the rolling-back-up process. So a detection, a stretch or a track has the same name whether or not the footage was cut, and anything can be traced back to the footage it came from.

These should give us all the components we need, so that detection can be simple algebra over the supports.

But the bottom line is that **getting atomization and keying correct for units as (x, y, t) and references of what it was cut** is what makes the rest work.

--- end write up