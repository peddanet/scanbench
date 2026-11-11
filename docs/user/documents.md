# Scanning documents

Back to: [User documentation](README.md) · [Documentation home](../README.md)

The tab **Documents** scans single pages or whole stacks, lets you arrange the
pages and saves them as one PDF file in the size you choose.

## 1. Choose the scanner

The bar above the tabs lists every scanner SANE can reach. scanbench searches
once at start; **Search scanners** searches again (network scanners can take a
few seconds). Sources, colour modes and resolutions in the tabs always follow
the selected scanner.

To try scanbench without hardware, start it with SANE's virtual scanner:

~~~bash
SCANBENCH_TEST_DEVICE=1 scanbench
~~~

| Part | Meaning | Privilege |
|---|---|---|
| `SCANBENCH_TEST_DEVICE=1` | adds the device `test` of SANE's test backend to the list, for this start only | normal user |
| `scanbench` | starts the GUI | normal user |

## 2. Settings

| Setting | Choices | Notes |
|---|---|---|
| Source | Flatbed · Feeder, one side · Feeder, both sides | only what the scanner offers; "both sides" needs a duplex feeder |
| Colour | Color · Gray · Black and white | black and white (line art) gives the smallest files for text |
| Resolution | as offered by the scanner, e.g. 75 to 1200 dpi | 300 dpi suits documents; 150 dpi is enough for screen reading |
| Paper | A4 · A5 · A6 · Letter | the scan area; limited to the scanner's maximum |

## 3. Scan and arrange

| Action | How |
|---|---|
| scan | **Scan**: one page from the flatbed, or every sheet in the feeder |
| more pages | press **Scan** again; new pages are appended |
| turn a page | select it, **Rotate left/right**, or right-click: 90°, 180° |
| reorder | **Move up / Move down** |
| remove | **Delete page** or right-click > Delete page |
| start over | **Start new document** |

Rotations are stored and applied when saving, so editing never degrades the
scan.

### Two-sided documents without a duplex feeder (manual duplex)

1. Put the stack into the feeder, front sides as usual, press **Scan**.
2. Turn the whole stack over and put it back without re-sorting.
3. Press **Scan** again; the back sides arrive in reverse order.
4. Press **Merge fronts + backs**: the two runs are interleaved into reading
   order (front 1, back 1, front 2, ...). Both runs must have the same number
   of sheets.

## 4. Save as PDF

Choose **PDF size** and press **Save PDF ...**.

| PDF size | Ghostscript preset | Typical use |
|---|---|---|
| Original (lossless) | none | archive; pages are embedded unchanged with `img2pdf` |
| Screen (72 dpi) | `/screen` | smallest file, screen only |
| E-book (150 dpi) | `/ebook` | e-mail, reading on screen (default) |
| Printer (300 dpi) | `/printer` | printing ("Printfarbe") |
| Prepress (300 dpi, best) | `/prepress` | printing with highest quality ("Plasma") |

Every reduced size is produced from the lossless original, never from another
reduced file. If a reduction would not make the file smaller (this can
happen with black-and-white pages), the lossless file is kept. Reduced sizes
need Ghostscript (`sudo apt install ghostscript`).

## 5. Print

**Print ...** opens the print dialog ([printing](printing.md)). Documents are
always printed from the lossless pages.

## References

- [Ghostscript: PDFSETTINGS presets](https://ghostscript.readthedocs.io/en/latest/VectorDevices.html)
- [img2pdf: lossless conversion of images to PDF](https://gitlab.mister-muffin.de/josch/img2pdf)
- [scanimage(1)](https://manpages.debian.org/scanimage) -- the SANE command line program scanbench uses

Terms: [glossary](../glossary.md).
