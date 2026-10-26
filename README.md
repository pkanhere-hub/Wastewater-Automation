# Wastewater Automation

## MBBR STP tablet schematic

A show-and-tell web app that displays the MBBR sewage treatment plant schematic full screen on an Android tablet in landscape. Level sensors, pumps, the air blower, flow meters and the pressure sensor can be tapped to show demo readings. The values are fixed demo values, not live data.

- Live page: https://pkanhere-hub.github.io/Wastewater-Automation/
- Works offline after the first visit (service worker), and can be installed from Chrome's menu with **Add to Home screen**, where it opens full screen.

### Files

- `docs/` is the published site (GitHub Pages serves this folder).
- `tools/convert.py` turns the PowerPoint slide into the grouped SVG. Each plant component is a `<g class="component">` with a stable `id` such as `mbbr-1` or `filter-feed-pump`.
- `tools/template.html` is the page (layout, pinch-zoom, popups and demo readings in `DEVICES`).
- `tools/assemble.py` combines the SVG and the template into `mbbr-plant.html` and `pwa/index.html`.

### Rebuilding

```sh
cd tools
unzip -o MBBR_STP_Pictorial_Schematic.pptx -d pptx
python3 convert.py pptx/ppt/slides/slide1.xml schematic.svg
mkdir -p pwa && python3 assemble.py
cp pwa/index.html ../docs/index.html
```

When you change the page, also bump `CACHE` in `docs/sw.js` so installed copies pick up the new files.
