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