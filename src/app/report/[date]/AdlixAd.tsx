"use client";

import { useEffect, useRef } from "react";

export default function AdlixAd() {
  const containerRef = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);

  useEffect(() => {
    if (!containerRef.current || initialized.current) return;
    initialized.current = true;

    // 원본 광고 코드를 그대로 iframe으로 삽입하여 고유 ID 보존
    const iframe = document.createElement("iframe");
    iframe.style.width = "800px";
    iframe.style.maxWidth = "100%";
    iframe.style.height = "200px";
    iframe.style.border = "none";
    iframe.style.overflow = "hidden";
    iframe.scrolling = "no";

    containerRef.current.appendChild(iframe);

    const doc = iframe.contentDocument || iframe.contentWindow?.document;
    if (doc) {
      doc.open();
      doc.write(`
        <!DOCTYPE html>
        <html><head><style>body{margin:0;padding:0;overflow:hidden;}</style></head>
        <body>
          <script src="https://www.adlix.co.kr/js/adb_sc.js"><\/script>
          <script>new Ads_b_dhmi.G({"id":"21451463","ogb":"0","width":"800","height":"200","interval":"5000"});<\/script>
        </body></html>
      `);
      doc.close();
    }
  }, []);

  return <div ref={containerRef} className="mb-6 flex justify-center" />;
}
