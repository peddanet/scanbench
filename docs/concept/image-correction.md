# Image correction for scanned photos

Back to: [Concept](README.md) · [Documentation home](../README.md)

| | |
|---|---|
| Status | proposal, revision 1, 2026-11-12; not implemented |
| Requested | 2026-11-12: scans look flat and colourless; can the scanner do better, and a correction toolset as a proposal |
| Decides | which corrections exist, how they are computed, how they are shown, where they are stored |

**Abstract.** Flat, pale scans are the normal raw output of SANE: the
scanner delivers the image almost uncorrected, while the Canon driver on
Windows and the device panel apply an automatic tone and colour correction.
The `pixma` backend of the MX92x offers no brightness, contrast or saturation
control, only a gamma value and a custom gamma table for all three channels
together (checked with `scanimage -A` on the user's device). A useful
correction therefore has to be done on the computer. This concept proposes six
corrections, computed with NumPy and OpenCV from the unchanged raw scan,
stored as parameters per photo and applied when the photo is saved. Nothing
is ever applied twice to an already corrected image.

## Contents

1. [Findings](#1-findings)
2. [Corrections](#2-corrections)
3. [Workflow and screen](#3-workflow-and-screen)
4. [Storage](#4-storage)
5. [Architecture](#5-architecture)
6. [Increment and tests](#6-increment-and-tests)
7. [Open decisions](#7-open-decisions)
8. [Glossary](#8-glossary)
9. [Sources](#9-sources)

## 1. Findings

| Finding | Source | Consequence |
|---|---|---|
| `pixma` offers `--gamma 0.3…5` (default 2.2), `--custom-gamma` with a 1024-entry table for all channels together, `--calibrate`; no brightness, contrast, saturation | `scanimage -d pixma:… -A` on the MX925, 2026-11-12; [sane-pixma(5)](https://manpages.ubuntu.com/manpages/focal/en/man5/sane-pixma.5.html) | at the scanner only the tone curve can change; colour cast and saturation cannot |
| SANE practice: leave the device's tone controls at their defaults and correct on the computer | [sane-devel, 2020-09](https://lists.alioth.debian.org/pipermail/sane-devel/2020-September/038210.html) | correction in scanbench, from the raw scan |
| the `airscan` option list of the device is not yet known | open request to the user | if airscan offers brightness/contrast, they are probably computed by the backend as well; scanbench does not depend on them |
| OpenCV's ready white balance (`xphoto.GrayworldWB`) is part of the contrib modules, not of `opencv-python-headless` used by scanbench | [OpenCV xphoto](https://docs.opencv.org/4.x/d7/d71/classcv_1_1xphoto_1_1GrayworldWB.html) | the gray-world method is implemented directly with NumPy (a few lines) |

## 2. Corrections

All operations work on the cut-out photo, in 8 bit RGB, in this fixed order.
Each has a neutral value that changes nothing.

| # | Correction | Method | Parameter (neutral) | Automatic proposal |
|---|---|---|---|---|
| 1 | White balance | gray world on the photo: scale R, G, B so that their means are equal; only pixels with saturation below a threshold count, so a red dress does not tint the result | strength 0 … 100 % (0) | yes |
| 2 | Auto levels | per channel: the 0.5 % darkest and brightest pixels become 0 and 255, linear stretch between them | clip 0 … 2 % (off) | yes, 0.5 % |
| 3 | Gamma / brightness | tone curve `out = in^(1/γ)` on the lightness | γ 0.5 … 2.0 (1.0) | no |
| 4 | Local contrast (CLAHE) | contrast-limited adaptive histogram equalisation on L of Lab; lifts dark interiors without burning out windows | clip limit 1 … 4 (off) | no |
| 5 | Saturation | scale a and b in Lab around neutral | 0 … 200 % (100 %) | yes, from the measured saturation of faded prints, at most 130 % |
| 6 | Sharpen | unsharp mask on L: radius 1 … 3 px, amount 0 … 150 %, threshold 0 … 10 | amount 0 (off) | no |

Order rationale: the colour cast is removed before stretching, otherwise a
tinted channel would be stretched wrongly; sharpening comes last so it does
not amplify noise that the other steps changed.

**Automatic proposal ("Auto").** For a confirmed scan, scanbench computes
white balance strength, level clip and saturation per photo and shows them as
a proposal; the user accepts, changes or switches them off. Faded prints of
the 1970s typically need all three; modern prints often only levels.

**Presets.** Named sets of parameters, e.g. "Faded colour prints",
"Black-and-white prints" (white balance off, saturation 0 %, levels on),
"Neutral" (everything off). They are part of the presets of the settings
concept (0.3.0) and follow the same layers.

## 3. Workflow and screen

~~~text
+--------------------------------------------------------------------------+
| frame editor (scan with frames)        | CORRECTION  photo 2 of 4  < >   |
|                                        | [x] Auto   Preset: [Faded  v]   |
|                                        | White balance   [=====----] 80 %|
|                                        | Levels clip     [==-------] 0.5 |
|                                        | Gamma           [----|----] 1.0 |
|                                        | Local contrast  [off      ]     |
|                                        | Saturation      [=====|---] 120%|
|                                        | Sharpen         [off      ]     |
|                                        | [Apply to all photos] [Reset]   |
|                                        +---------------------------------+
|                                        | before | after  (split view)    |
+--------------------------------------------------------------------------+
~~~

| Principle | Implementation |
|---|---|
| per photo | each frame has its own parameters; "Apply to all photos" copies them to the other frames of the page (or the session) |
| visible effect | a split view of the selected photo: left original, right corrected, with a movable divider; the view is computed from a reduced copy (longest side about 1500 px), so sliders react at once |
| honest preview | the same code computes preview and final photo; only the input size differs |
| never cascade | the saved photo is always computed from the raw scan; changing the correction later recomputes from the raw scan |
| optional | "Neutral" is the default until the user turns on Auto or a preset (decision D17) |

## 4. Storage

Per photo in `album.json` (and later in `session.json`), next to the frame:

~~~json
"correction": {"white_balance": 0.8, "levels_clip": 0.5, "gamma": 1.0,
               "clahe": 0.0, "saturation": 1.2, "sharpen": 0.0}
~~~

The raw scans are kept (decision D9), so every photo can be recomputed with
other values later; a re-export command can apply a changed preset to a whole
album.

## 5. Architecture

| Layer | Class | Responsibility | Pattern |
|---|---|---|---|
| domain | `Correction` | the six parameters, neutral values, validation, (de)serialisation | Value Object |
| domain | `CorrectionPreset` | named `Correction` | — |
| infrastructure | `ImageCorrector` | applies a `Correction` to an RGB array, step by step (NumPy, OpenCV `cvtColor`, `createCLAHE`, `GaussianBlur`) | Pipeline / Chain of steps |
| infrastructure | `CorrectionAdvisor` | measures a photo and proposes white balance, clip, saturation | Strategy |
| application | `PhotoSession.accept` | applies the correction of each frame before saving | — |
| ui | `CorrectionPanel`, `SplitView` | sliders, presets, before/after view | — |

## 6. Increment and tests

Proposed as **0.2.6**, before the settings and sessions (0.3.x), because it
needs only `album.json` and the frame editor:

| Step | Content |
|---|---|
| 1 | `Correction`, `ImageCorrector`, `CorrectionAdvisor` with unit tests on synthetic images: a known colour cast is removed (channel means within 2 levels), a compressed tone range is stretched to 0…255 (± 1 %), neutral values change no pixel, saturation 0 gives grey |
| 2 | correction panel and split view; GUI tests for slider → preview update, "Apply to all", reset |
| 3 | `accept` applies the correction; `album.json` stores it; documentation (user guide, developer docs, glossary) |

Reference images for manual checks: the CC0 samples of the screenshots,
artificially faded (cast, reduced contrast and saturation), so the effect
can be shown in the README without private photos.

## 7. Open decisions

| # | Question | Proposal |
|---|---|---|
| D16 | colour space for saturation and CLAHE | Lab (OpenCV 8 bit), as already used by the detection |
| D17 | default for new photos | "Neutral"; Auto only when switched on (or a preset chosen); the choice is remembered |
| D18 | correction also for documents | not now; documents keep their own PDF options |

## 8. Glossary

| Term | Meaning | Further reading |
|---|---|---|
| Auto levels | stretching each colour channel so that its darkest and brightest values reach 0 and 255, after ignoring a small share of extreme pixels | [Wikipedia: Normalization (image processing)](https://en.wikipedia.org/wiki/Normalization_(image_processing)) |
| CLAHE | contrast-limited adaptive histogram equalisation: equalises small tiles separately and limits the gain, so noise is not amplified | [OpenCV tutorial](https://docs.opencv.org/5.x/d5/daf/tutorial_py_histogram_equalization.html) |
| Gamma | exponent of a tone curve; values above 1 (as used here) brighten the mid-tones | [Wikipedia: Gamma correction](https://en.wikipedia.org/wiki/Gamma_correction) |
| Gray world | white balance assuming that the average colour of a scene is grey | [OpenCV GrayworldWB](https://docs.opencv.org/4.x/d7/d71/classcv_1_1xphoto_1_1GrayworldWB.html) |
| Unsharp mask | sharpening by adding the difference between the image and a blurred copy | [Wikipedia: Unsharp masking](https://en.wikipedia.org/wiki/Unsharp_masking) |
| White balance | removing a colour cast so that neutral grey appears grey | [Wikipedia: Color balance](https://en.wikipedia.org/wiki/Color_balance) |

## 9. Sources

| Source | Used for |
|---|---|
| `scanimage -d pixma:MX920_… -A`, output of the user's device, 2026-11-12 | available scanner options |
| [sane-pixma(5)](https://manpages.ubuntu.com/manpages/focal/en/man5/sane-pixma.5.html) | backend features: custom gamma table |
| [sane-devel: brightness with airscan, 2020-09](https://lists.alioth.debian.org/pipermail/sane-devel/2020-September/038212.html) | airscan had no brightness/contrast then |
| [sane-devel: correct on the PC, 2020-09](https://lists.alioth.debian.org/pipermail/sane-devel/2020-September/038210.html) | practice: keep device defaults, correct on the computer |
| [OpenCV xphoto GrayworldWB](https://docs.opencv.org/4.x/d7/d71/classcv_1_1xphoto_1_1GrayworldWB.html) | gray-world method with saturation threshold |
| [OpenCV: histogram equalisation and CLAHE](https://docs.opencv.org/5.x/d5/daf/tutorial_py_histogram_equalization.html) | CLAHE |
