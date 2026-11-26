# Two offices can commit

The top sequence follows offices A and B from the four-lane venue. All three seats in each office move from free to held as part of one reservation per lane. Both lanes can accept a request at revision zero and advance to one.

The second sequence isolates a race on a fresh lane A. Both calls expect revision zero. One advances the lane revision and returns `OK`. The other returns `STALE`. The moving dots depict the reservation operation and give the abstract seat units a visible path. The generated mission commits all three together. [Static storyboard](overview.png) · [Partitioned actor API](../PARTITIONING.md)

Regenerate with Python, Pillow, fontconfig, Open Sans Condensed Bold and Liberation Mono.

```sh
python3 docs/motion/render.py
```

The command writes the GIF and the static PNG beside the renderer.
