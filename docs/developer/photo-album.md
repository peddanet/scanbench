# Photo album: detection, cropping, frame editor

Back to: [Developer documentation](README.md) · [Architecture](architecture.md) · [Documentation home](../README.md)

## Modules

| Module | Class | Responsibility |
|---|---|---|
| `domain/crop_region.py` | `CropRegion` | rotated frame in scan pixels: centre, size, angle, quarter turns; turn, straighten, fit, snap, clamp |
| `domain/frame_handle.py` | `FrameHandle` | the nine grips of a selected frame |
| `domain/frame_edit.py` | functions | frame axes, grip positions, move, resize, rotate, transfer to an area scan, bounding area, merge, summary text |
| `domain/frame_history.py` | `FrameHistory` | undo/redo of frame lists (Memento) |
| `domain/scan_area.py` | `ScanArea` | part of the glass in mm (`scanimage -l -t -x -y`) |
| `domain/image_format.py` | `ImageFormat` | PNG or JPEG |
| `infrastructure/photo_detector.py` | `PhotoDetector`, `DetectorTuning` | find photos (Strategy) |
| `infrastructure/frame_splitter.py` | `FrameSplitter` | cut a blob of photos lying edge to edge into single photos |
| `infrastructure/edge_refiner.py` | `EdgeRefiner` | place each frame side on the photo edge at full resolution |
| `infrastructure/image_cropper.py` | `ImageCropper` | affine cut-out, deskew, quarter turns |
| `infrastructure/settings_store.py` | `SettingsStore` | remembered album folder |
| `application/photo_session.py` | `PhotoSession`, `PhotoScan`, `AlbumOptions` | preview, area scan, full scan, proposal, confirmation, numbering, `album.json` (State) |
| `ui/photo_tab.py`, `ui/photo_form.py` | `PhotoTab`, `PhotoForm` | workflow and options |
| `ui/frame_editor.py` | `FrameEditor`, `EditorTools` | toolbar, preview, details line, hint, undo history, live image |
| `ui/zoom_control.py` | `ZoomControl` | zoom steps, fit, 100 %, Ctrl + wheel (event filter) |
| `ui/guide_items.py` | `GuideItem` | guide lines, movable along one axis |
| `ui/frame_values_dialog.py` | `FrameValuesDialog` | exact width, height, skew, turn |
| `ui/region_view.py` | `RegionView` | drawing, selection, grip drags, drawing new frames, keyboard |
| `ui/frame_items.py` | `RegionItem`, `HandleItem` | graphics items of frames, number badges and grips |
| `ui/region_menus.py` | `RegionMenus` | context menus and their commands (Command) |

## Detection

~~~mermaid
flowchart TB
  scan["RGB scan at N dpi"] --> small["resize to 75 dpi"]
  small --> lab["Lab colour space"]
  lab --> bg["lid colour: most frequent light colour"]
  bg --> dist["colour distance > 14"]
  small --> canny["Canny edges"]
  dist --> union["union"]
  canny --> union
  union --> close["close 3 mm, fill outlines, open 2 mm"]
  close --> rect["minAreaRect per blob"]
  rect --> filter["shorter side >= 25 mm, fill >= 55 %"]
  filter --> split["FrameSplitter: cut at seams, up to 3 times"]
  split --> norm["edge closest to horizontal = width; angle in (-45, 45]"]
  norm --> refine["EdgeRefiner: sides onto the photo edges, full resolution"]
  refine --> snap["optional: snap to photo presets (6 %, grow <= 1 mm per side)"]
~~~

Colour distance finds the photo area but misses light borders; the edges
(the shadow line every photo casts on the glass) outline them. Only rotation
is estimated, never perspective, so no result can become a trapezoid.

### Splitting photos that lie edge to edge

Two touching photos form one blob. `FrameSplitter` turns the blob upright
(its own minimum-area rectangle) and scores every straight line across it,
in both directions and with slants of up to ±3°:

| Cue | Line counts as seam if | Accepted when |
|---|---|---|
| light | ≥ 60 % of its blob pixels are near the lid colour (distance < 2 × 14), and 3 mm to both sides the light share is < 30 % (a thin seam, not a bright sky) | both parts have at least the minimum photo side |
| edge | ≥ 75 % of its pixels lie on (slightly widened) Canny edges | additionally both parts have a standard photo size, or a row of two or three of them (±10 %) |

The edge cue alone needs the size check because pictures contain long
straight edges (steps, horizons). Each part gets its own minimum-area
rectangle, so the photos keep their own skew, and is split again (depth 3).
A wrong cut is undone in the editor with **Merge selected frames**.

### Placing the sides at full resolution

The detection works at 75 dpi (0.34 mm per pixel) and the mask is closed
and widened by edge pixels, so a rough side may lie up to about a millimetre
outside the photo. `EdgeRefiner` cuts each rough frame with 2 mm margin out
of the full-resolution scan, deskews it and computes the Lab distance from
the lid colour; neutral grey (a, b within 6 of the lid, at most 70 darker)
is mapped into the light-strip range. For each side it looks at the lines
parallel to that side over the middle 80 % of the side, outermost first:

| Situation at the outermost line | New side |
|---|---|
| lid colour | after the lid lines and after a light strip of at most 1.5 mm; a wider light band is a print border and stays; lid colour reaching more than 1.5 mm into the rough frame is a lid-coloured border: rough side stays |
| no lid (a neighbouring photo touches) | rough side, minus a light strip of at most 1.5 mm inside the frame |

Each side moves by at most 2 mm + 1.5 mm. Only the cut-out is converted to
Lab, so 2400 dpi scans need little memory.

### Preview and area scan

`PhotoSession.preview` scans the whole glass at the lowest offered
resolution of at least 75 dpi and marks the result as preview (it cannot be
accepted). `scan_area` computes the bounding rectangle of all frames plus
3 mm (`frame_edit.bounding_area_mm`), clamps it to the device maximum, scans
only that `ScanArea` at the chosen resolution and maps the frames with
`frame_edit.transferred`: `new = old × factor − offset`, with
`factor = dpi_new / dpi_preview` and the offset of the area in new pixels.

## Coordinates of a frame

A frame is a rectangle around `(cx, cy)` with `width` along its own u axis
and `height` along its v axis, turned by `angle` degrees (clockwise on
screen, y pointing down). `frame_edit.to_local` and `to_scan` convert between
scan pixels and frame axes:

~~~text
u =  dx·cos(a) + dy·sin(a)        x = cx + u·cos(a) − v·sin(a)
v = −dx·sin(a) + dy·cos(a)        y = cy + u·sin(a) + v·cos(a)
~~~

| Edit | Rule |
|---|---|
| resize with a side or corner grip | the opposite side stays; new size from the mouse position in frame axes; minimum 5 mm |
| rotate with the orange grip | the top of the frame points at the mouse: `angle = atan2(x − cx, cy − y)`; Shift rounds to 0.5°; result in (−180, 180] |
| move | drag the frame or arrow keys (one screen pixel, at least one scan pixel; Shift: ten) |
| draw | in draw mode a drag on free space makes a new selected frame (at least 5 mm) |
| merge | `frame_edit.merged`: the first frame's axes, enclosing all corners |
| exact values | `FrameValuesDialog`: width and height in mm, skew in 0.1°, turn |
| fine turn | `+` / `-` by 0.1° |
| quarter turns | only change the saved photo, not the frame on the scan |

Every result is clamped to the scan (`CropRegion.clamped`).

## Cropping

`ImageCropper` maps three corners of the frame onto an upright rectangle with
`cv2.getAffineTransform` and `cv2.warpAffine` (cubic interpolation, replicated
border), then applies `numpy.rot90` for the quarter turns.

## Frame editor interaction

~~~mermaid
sequenceDiagram
  actor U as User
  participant V as RegionView
  participant E as frame_edit
  participant T as PhotoTab
  U->>V: press on a grip
  V->>V: remember grip, frame, regions
  loop mouse move
    V->>E: resized / rotated_towards
    V->>V: redraw preview (no signal)
  end
  U->>V: release
  V->>V: set_regions(preview, selected)
  V-->>T: regions_changed
  T->>T: session.current.regions = edited
~~~

## Tests

`tests/scenes.py` renders synthetic flatbed scans (photos with grey or white
borders, skew, 90-degree turns, shadow line, photos edge to edge).
`tests/unit/test_image_pipeline.py` checks position (2 mm), size (1.5 mm)
and skew (0.5°) of every detected photo, the splitting and the removal of
light strips; `tests/unit/test_frame_edit.py` the geometry and the undo
history; `tests/unit/test_sessions.py` preview and area scan;
`tests/gui/test_frame_editor.py` and `tests/gui/test_editor_tools.py`
grip drags, keys, toolbar, guides, drawing, values and merging through
synthetic mouse and key events (helpers in `tests/editor_helpers.py`).
