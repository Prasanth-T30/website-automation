import * as pdfjs from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { useEffect, useRef, useState } from "react";
import { LoadingState } from "@/components/ui/States";

// pdf.js parses on a worker thread; Vite hands us its hashed URL so it is
// bundled rather than fetched from a CDN the console may not be able to reach.
pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

/**
 * Render a PDF onto canvases, rather than handing it to the browser.
 *
 * An `<iframe>` pointed at a PDF depends on the browser's built-in viewer,
 * and that is not something the console can rely on: Chrome's "Download PDF
 * files instead of automatically opening them" setting, some managed
 * policies, and several embedded browsers all leave the frame blank — a grey
 * box with no explanation, on the one screen where an HR is supposed to check
 * a document before it goes out under the company's name.
 *
 * Drawing it ourselves means the preview looks the same everywhere, and that
 * what is on screen is provably the bytes we were given.
 *
 * @param {object} props
 * @param {Blob} props.file  The PDF to draw.
 * @param {string} props.label  For the accessible name of each page.
 * @param {string} [props.className]
 */
export function PdfPreview({ file, label, className }) {
  const holder = useRef(null);
  const [status, setStatus] = useState("loading");
  const [pages, setPages] = useState(0);

  useEffect(() => {
    if (!file) return undefined;
    let cancelled = false;
    let doc = null;

    (async () => {
      setStatus("loading");
      try {
        const data = new Uint8Array(await file.arrayBuffer());
        doc = await pdfjs.getDocument({ data }).promise;
        if (cancelled) return;
        setPages(doc.numPages);

        const target = holder.current;
        if (!target) return;
        target.replaceChildren();

        // Drawn at the container's width so the page fills the panel, and at
        // the device pixel ratio so it is not soft on a high-DPI screen.
        const width = target.clientWidth || 640;
        const dpr = Math.min(window.devicePixelRatio || 1, 2);

        for (let n = 1; n <= doc.numPages; n += 1) {
          const page = await doc.getPage(n);
          if (cancelled) return;
          const unscaled = page.getViewport({ scale: 1 });
          const viewport = page.getViewport({ scale: width / unscaled.width });

          const canvas = document.createElement("canvas");
          canvas.width = Math.floor(viewport.width * dpr);
          canvas.height = Math.floor(viewport.height * dpr);
          canvas.style.width = "100%";
          canvas.style.height = "auto";
          canvas.className = "block rounded-md border border-line bg-white";
          canvas.setAttribute("role", "img");
          canvas.setAttribute("aria-label", `${label} — page ${n} of ${doc.numPages}`);
          target.append(canvas);

          await page.render({
            canvasContext: canvas.getContext("2d"),
            viewport,
            transform: dpr === 1 ? undefined : [dpr, 0, 0, dpr, 0, 0],
          }).promise;
          if (cancelled) return;
        }
        setStatus("ready");
      } catch {
        if (!cancelled) setStatus("error");
      }
    })();

    return () => {
      cancelled = true;
      doc?.destroy?.();
    };
  }, [file, label]);

  return (
    <div className={className}>
      {status === "loading" && <LoadingState label="Rendering…" />}
      {status === "error" && (
        <p className="px-3 py-6 text-center text-xs text-danger-text">
          This file could not be displayed. Download it to check it instead.
        </p>
      )}
      <div
        ref={holder}
        className="flex flex-col gap-3"
        aria-busy={status === "loading" || undefined}
      />
      {status === "ready" && pages > 1 && (
        <p className="mt-2 text-center text-[11px] text-fg-muted">{pages} pages</p>
      )}
    </div>
  );
}
