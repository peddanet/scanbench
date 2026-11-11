# Photo album: detection, cropping, frame editor

Back to: [Developer documentation](README.md) · [Architecture](architecture.md) · [Documentation home](../README.md)

## Modules

| Module | Class | Responsibility |
|---|---|---|
| `domain/crop_region.py` | `CropRegion` | rotated frame in scan pixels: centre, size, angle, quarter turns; turn, straighten, fit, snap, clamp |
| `domain/frame_handle.py` | `FrameHandle` | the nine grips of a selected frame |
| `domain/frame_edit.py` | functions | frame axes, grip positions, move, resize, rotate, summary text |
| `domain/image_format.py` | `ImageFormat` | PNG or JPEG |
| `infrastructure/photo_detector.py` | `PhotoDetector`, `DetectorTuning` | find photos (Strategy) |
| `infrastructure/image_cropper.py` | `ImageCropper` | affine cut-out, deskew, quarter turns |
| `infrastructure/settings_store.py` | `SettingsStore` | remembered album folder |
| `application/photo_session.py` | `PhotoSession`, `PhotoScan`, `AlbumOptions` | scan, proposal, confirmation, numbering, `album.json` (State) |
| `ui/photo_tab.py`, `ui/photo_form.py` | `PhotoTab`, `PhotoForm` | workflow and options |
| `ui/frame_editor.py` | `FrameEditor` | preview, details line, hint |
| `ui/region_view.py` | `RegionView` | drawing, selection, grip drags, keyboard |
| `ui/frame_items.py` | `RegionItem`, `HandleItem` | graphics items of frames and grips |
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
  filter --> norm["edge closest to horizontal = width; angle in (-45, 45]"]
  norm --> snap["optional: snap to photo presets (6 %)"]
~~~

Colour distance finds the photo area but misses light borders; the edges
(the shadow line every photo casts on the glass) outline them. Only rotation
is estimated, never perspective, so no result can become a trapezoid.

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
| move | drag the frame or arrow keys (1 mm, Shift 10 mm) |
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
borders, skew, 90-degree turns, shadow line). `tests/unit/test_image_pipeline.py`
checks position, size and skew of every detected photo;
`tests/unit/test_frame_edit.py` the geometry; `tests/gui/test_frame_editor.py`
grip drags and keys through synthetic mouse and key events.
