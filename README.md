# fzgx-checkpoint-diagrams

This is a desktop GUI program to draw and save checkpoint diagrams for F-Zero GX courses. You can pan, zoom, pick which checkpoints to show, and add path lines to your liking.

(TODO: Add a screenshot)

## Running

**From executable:** Not available yet. Stay tuned.

**From source:** Install the stuff listed at the top of `main.py`. Then at the command line, run `python main.py`. Windows, Mac, and Linux should work (Python and QT support all of these).

## Usage

To start off, select a course and then click "Update diagram".

Pan by dragging on the diagram, and zoom using the mousewheel. The rest of the options are described by tooltips. Hover your mouse over the various text labels ("Extended checkpoints:", "Hidden numbers:", etc.) to see the tooltips. You can change some options and then click "Update diagram" again to see the changes.

When you are satisfied with how the diagram looks, click "Save image" to save the diagram as a PNG file.

## About the project

The GUI is coded using Python, PyQt, and Matplotlib. The checkpoint data is laid out in CSV format in this repository. Checkpoint data was collected using Dolphin emulator, [RAM watch scripts](https://github.com/yoshifan/ram-watch-cheat-engine), and some amount of tedious start-and-stop driving (maybe averaging 1 hour per course so far). Checkpoint parameters are not exact, but hopefully they're pretty close.

The repository and its author(s) are not affiliated with Nintendo or the game's creators.
