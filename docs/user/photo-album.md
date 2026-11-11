# Scanning photo albums

Back to: [User documentation](README.md) · [Documentation home](../README.md)

The tab **Photo album** scans several photos or postcards at once on the
flatbed, finds them, straightens them and saves each one as its own file.

## 1. Put the photos on the glass

- Up to four photos fit on the A4 glass, e.g. three 10 x 15 cm landscape
  photos and one portrait photo, or three postcards.
- Leave a few millimetres between the photos; touching photos may be found as
  one.
- Photos may lie slightly skewed or turned by 90 degrees; both are detected.
- Close the lid. A white or light grey lid works best.

## 2. Settings

| Setting | Default | Notes |
|---|---|---|
| Colour | Color | Gray for black-and-white photos |
| Resolution | 600 dpi | 300 dpi for small prints, 600 dpi for archiving |
| Format | PNG (lossless) | JPEG (quality 92) gives about a tenth of the size |
| Album | `~/Pictures/scanbench-album` | remembered across restarts |
| Fit frames to photo sizes | on | frames within 6 % of 9 x 13, 10 x 15, postcard A6 or 13 x 18 cm get exactly that size |
| Keep full-page scans | off | also stores the whole page in `scans/` of the album |

The scan always covers the whole A4 frame; this is the largest possible
photo frame.

## 3. Scan, check, confirm

1. **Scan page**. The preview shows the page with a blue frame per photo, its
   number and an arrow that points to the side that becomes the top.
2. Check every frame. Right-click on a frame:

   | Command | Effect |
   |---|---|
   | Rotate 90° clockwise / counter-clockwise, Rotate 180° | turns the saved photo, e.g. for a portrait postcard |
   | Align horizontally (remove skew) | sets the skew to 0 degrees |
   | Fit to size > 9 x 13 cm ... | gives the frame an exact photo size |
   | Delete frame | the photo is not saved |

   Right-click on free space: **Add frame here** with a photo size, **Add
   frame: whole page**, **Delete all frames**. Drag a frame to move it.
3. **Confirm N photo(s)**. Only now the photos are cut out, deskewed and saved
   as `photo-0001.png`, `photo-0002.png` ...; numbering continues after the
   highest number already in the album.
4. Put the next page on the glass and scan again. **Discard scan** throws a
   scan away; **Detect again** repeats the detection, e.g. after switching
   the size fitting off.

The result is always a straight rectangle: the photo is only rotated, never
distorted into a trapezoid.

## 4. What is in the album folder

~~~text
album/
  photo-0001.png ...   the photos, numbered in scan order
  album.json           per photo: file, source scan, resolution, frame
  scans/               full-page scans (only with "Keep full-page scans")
~~~

## 5. Print

**Print saved photos ...** prints the photos of the last confirmed page, see
[printing](printing.md). "Scale to fit the page" is preselected.

## How the detection works

The scan is reduced to 75 dpi. Two cues are combined: the colour distance
from the lid colour (finds the photo area) and edges (the thin shadow line
every photo casts on the glass also outlines white or grey borders). The
union is closed, filled and opened; each remaining area is described by its
minimum-area rotated rectangle
([OpenCV minAreaRect](https://docs.opencv.org/4.x/d3/dc0/group__imgproc__shape.html)).
Of the two possible descriptions, the one with the smaller skew is used, so
a photo turned by 89 degrees counts as a portrait photo with 1 degree skew.

Terms: [glossary](../glossary.md).
