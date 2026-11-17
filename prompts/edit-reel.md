# Edit brief: one vertical talking reel

The creator's request, in their words:

> Edit the clips I identify in raw/ into a vertical talking reel. Review every take before
> cutting. Group takes by topic and distinguish a duplicate, a false start and a continuation.
> Tell me which takes form the complete story and flag any missing ending.
>
> Keep my voice and the meaning of my story. Trim long gaps and failed starts. Use the strongest
> clear opening and a natural ending; do not cut off my last line to hit a time limit. Add
> readable captions and only graphics that explain what I am saying. Keep my face clear and
> preserve the original colour.
>
> Show me your cut plan, then render a draft in exports/. Save the transcript and cut list.
> Check playback, captions, speech and the ending. Do not publish it.

## Steps

1. **Brand.** Read `brand/brand.json`. If `"configured": false`, ask the creator once for colours,
   caption font and style, and pacing; save them and set `configured` to `true`.
2. **Probe** each clip: `./studio probe raw/<clip>`. Note orientation, HDR/SDR and audio.
3. **Transcribe** each clip into one reel folder: `./studio transcribe raw/<clip> --reel <name>`.
   Pick a short, lowercase reel name from the topic (e.g. `budget-tips`).
4. **Review every take** using the transcripts (`reels/<name>/*.txt`). Group by topic. For each
   take decide: keep, duplicate (a repeat of a better take), false start (abandoned line), or
   continuation (picks up where another take stopped). Check the last line of the story is
   complete; if the ending was never recorded, say so.
5. **First cut.** `./studio autocut raw/<a> raw/<b> --reel <name>` writes a cut list without long
   pauses. Edit `reels/<name>/cutlist.json`: remove false starts and duplicates, order the
   segments into the story, pick the strongest clear opening, keep the full ending.
6. **Graphics.** Add only graphics that explain what is being said (`headline`, or `image` with an
   approved screenshot from `references/`). Keep them off the face and out of the top ~12% and
   bottom ~25% of the frame.
7. **Show the cut plan** to the creator in plain words: the takes used, in order, the opening and
   closing lines, what was removed and why, the graphics, and the expected length. Wait for OK.
8. **Render a draft:** `./studio render reels/<name>/cutlist.json --draft`. Then look at the check
   frames in `reels/<name>/checks/`, confirm captions are readable, graphics are clear of the face
   and colour matches the source (`./studio compare raw/<clip> exports/<file>`).
9. **Final render** (without `--draft`) once the creator approves.
10. **Report:** the exact path of the MP4, what passed, and what they should check by eye and
    ear (first sentence, cuts, final words, caption spelling of names). Do not publish.

## Variations the creator may add

- **Batch of takes:** "These recordings include repeat takes and continuations. Review the whole
  batch first, then make one reel per distinct story. If there's a better ending in another take,
  use it. If the ending was never recorded, tell me." → one reel folder and cut list per story.
- **Cinematic reel:** "Use steady, well-framed B-roll that fits each line. Vary the shot lengths
  and don't recycle the same footage across the batch. For a voiceover, cut the picture to my
  recording." → transcribe the voiceover, set `voiceover` in the cut list, and cut the B-roll
  clips so their lengths follow the recording's lines.
- **Revision:** e.g. "remove the opening quote, keep my complete ending, move the diagram away from
  my face." → edit the cut list and render again; the new file gets the next `_vN` number.
