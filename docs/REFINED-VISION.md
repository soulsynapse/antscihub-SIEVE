# REFINED VISION

This is the vision after the wizard/setting workflow was decided on. 2026.07.26

The purpose of this is to put down in words what the workflow should be like, and what the lead-ins and lead-outs to the filter tab are.

## The project interface.

The project interface, a wizard, defines any folder with any number of video files in it as the target for SIEVE.

Any folder that already has the sieve sidecar files to define them as a project are not assumed to be sieve projects.

Any folder that The user attempts to add is evaluated for what would be needed to deploy a one video one folder rule. This is how the source video is defined for all downstream functions, but in the project interface, each individual folder that has one video in it has its own pipeline.

The project interface exists to 

1. Import video files and process folders of video so that they are ready for the sieve pipeline folder organization 
2. Quickly view the progress of a given folder so that folders marked as configured are clear to the user 
3. Browse between different projects and navigate files 

The project defining step is part of the pipeline as well; SIEVE on the CLI can accept a folder or file for ingest with the pipeline file as an argument and apply the pipeline to the video(s).

The ideal case is that the project doesn't move video files into new folders and instead accepts symbolic links to them. This maintains SIEVE as non destructive for source material.

---

## Replicates

The replicates tab has the video, the tab bottom seeker, and a replicates table spanning the bottom half.

The top half has the video on the left and settings and information on the right. 

The settings and information should be able to point to the parent as well as other information useful at the replicate stage. 

The right panel is also where the cropping tools live. The basic behavior should be a toggle between drawn and a stamp. The stamp needs to be drawn first or can be entered by dimensions.

When the user first sets a replicate, it can be dragged around by the cursor. Scrolling in or out magnifies the video so they can position it carefully, but doesn't zoom out more than the natural resizing to fit the box. While it isn't locked in, the dimensions have enterable numbers.

When the replicate box is set (either individually or via a "set all" or clicking into a replicate, it begins processing it. Left click on a replicate is the same as accepting it, and begins the crop, and moves the user over to the filters tab.

Right click on the video in the filters tab goes back up to the source. Left click on the video in the filters tab advances forward in outputs.

Back on the replicate tab, the full width replicate table is the replicate status. It should have the progress bar for the crop, at the very least, and the list of outputs defined by the DAG, and whether they exist.

---

## Filter tab

At the top of the window, there is a breadcrumbs trail for how deep onto outputs the user is. Outputs are when the user has decided they want some kind of output, and it materializes in that replicates folder as a new folder. Going into that folder, SIEVE only works with what is in that folder and doesn't know what is above it. If there is a video of a binary mask from a detection filter, then that is all that it has to work with. Any prior resource can be passed down with symbolic links. What is past forward is defined by what the user configures as the outputs, which is always the last item of the DAG in the filter view.

