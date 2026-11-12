/* Browser-side capture for UI002 icon centering. Real page/DOM only.
 * Run in DevTools on the actual rendered HTML, or use Playwright:
 *   await page.addScriptTag({path:'scripts/capture_ui_alignment.js'});
 *   const result = await page.evaluate(() => captureUiAlignment([
 *     {id:'bottom-production', slot:'#production .icon-slot', image:'#production .icon-slot img'}
 *   ]));
 * Persist JSON to reports/browser-layout.json; do not fabricate or edit boxes.
 */
(function (global) {
  "use strict";
  function rect(node) {
    const b = node.getBoundingClientRect();
    return [b.left, b.top, b.width, b.height].map(x => Math.round(x * 1000) / 1000);
  }
  function canvasBBox(img) {
    const canvas = document.createElement("canvas");
    const width = img.naturalWidth, height = img.naturalHeight;
    if (!width || !height) throw new Error("Image not decoded or has no natural size");
    if (width * height > 18000000) throw new Error("Image too large to inspect safely");
    canvas.width = width; canvas.height = height;
    const context = canvas.getContext("2d", {willReadFrequently: true});
    context.clearRect(0, 0, width, height);
    context.drawImage(img, 0, 0);
    // Same origin is required for getImageData; CORS errors fail the item.
    const data = context.getImageData(0, 0, width, height).data;
    let x0 = width, y0 = height, x1 = -1, y1 = -1;
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        if (data[(y * width + x) * 4 + 3] > 0) {
          x0 = Math.min(x0, x); y0 = Math.min(y0, y);
          x1 = Math.max(x1, x); y1 = Math.max(y1, y);
        }
      }
    }
    if (x1 < x0) throw new Error("PNG/SVG has no visible alpha pixels");
    return [x0, y0, x1 + 1, y1 + 1];
  }
  function imageVisualBox(img) {
    const style = getComputedStyle(img), box = rect(img);
    if (style.transform !== "none") {
      throw new Error("CSS transform on image: inspect layout manually, cannot infer alpha box");
    }
    if (style.objectPosition !== "50% 50%") {
      throw new Error("Noncenter object-position: inspect element or normalize source first");
    }
    const mode = style.objectFit;
    const natural = [img.naturalWidth, img.naturalHeight];
    const px = box[0], py = box[1], pw = box[2], ph = box[3];
    let displayedW = pw, displayedH = ph, ox = 0, oy = 0;
    if (mode === "contain" || mode === "scale-down") {
      const scale = Math.min(pw / natural[0], ph / natural[1],
                             mode === "scale-down" ? 1 : Infinity);
      displayedW = natural[0] * scale;
      displayedH = natural[1] * scale;
      ox = (pw - displayedW) / 2;
      oy = (ph - displayedH) / 2;
    } else if (mode !== "fill") {
      throw new Error("Unsupported object-fit (" + mode + "): use contain/fill or inspect manually");
    }
    const alpha = canvasBBox(img);
    return [
      px + ox + alpha[0] / natural[0] * displayedW,
      py + oy + alpha[1] / natural[1] * displayedH,
      (alpha[2] - alpha[0]) / natural[0] * displayedW,
      (alpha[3] - alpha[1]) / natural[1] * displayedH
    ].map(x => Math.round(x * 1000) / 1000);
  }
  global.captureUiAlignment = async function captureUiAlignment(targets) {
    if (!Array.isArray(targets) || !targets.length) {
      throw new Error("Define actual visual-slot and img selectors for every target");
    }
    const items = [];
    for (const target of targets) {
      const item = {id: target && target.id};
      try {
        if (!target || typeof target.id !== "string" ||
            typeof target.slot !== "string" || typeof target.image !== "string") {
          throw new Error("id, slot, image selectors are required");
        }
        const slot = document.querySelector(target.slot);
        const img = document.querySelector(target.image);
        if (!slot || !img) throw new Error("slot or image selector not found");
        if (!(img instanceof HTMLImageElement)) throw new Error("image selector must target an img element");
        await img.decode();
        if (!slot.contains(img)) throw new Error("selected image is not inside designated slot");
        const slotStyle = getComputedStyle(slot);
        if (slotStyle.transform !== "none") throw new Error("slot has CSS transform; cannot infer visual center");
        item.slot_rect = rect(slot);
        item.image_rect = rect(img);
        item.visible_rect = imageVisualBox(img);
        item.src = img.currentSrc || img.src;
        item.object_fit = getComputedStyle(img).objectFit;
      } catch (e) {
        item.error = String(e && e.message || e);
      }
      items.push(item);
    }
    return {
      capture_type: "browser_dom_image_alpha",
      viewport: [window.innerWidth, window.innerHeight],
      device_pixel_ratio: window.devicePixelRatio,
      page_url: window.location.href,
      items
    };
  };
})(window);
