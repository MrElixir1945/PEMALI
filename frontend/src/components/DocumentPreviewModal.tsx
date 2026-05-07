"use client";

import { motion, AnimatePresence } from "framer-motion";
import { FileText, Award, Download, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface DocumentPreviewModalProps {
  previewDoc: { type: 'pdf' | 'cert', content: any } | null;
  setPreviewDoc: (doc: any | null) => void;
  sessionId: string | null;
}

export default function DocumentPreviewModal({ previewDoc, setPreviewDoc, sessionId }: DocumentPreviewModalProps) {
  if (!previewDoc) return null;
  const auditLog = previewDoc.content;

  const handleDownload = () => {
    const content = document.getElementById('document-print-area')?.innerHTML;
    const win = window.open("", "_blank");
    if (win) {
      win.document.write(`
        <html>
          <head>
            <title>Download - PEMALI</title>
            <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
            <style>
              @page { size: A4; margin: 0; }
              body { margin: 0; padding: 0; }
              .print-container { width: 210mm; min-height: 297mm; padding: 20mm; box-sizing: border-box; position: relative; font-family: 'Inter', sans-serif; }
              table { width: 100%; border-collapse: collapse; margin: 20px 0; }
              th { background: #f5f5f4; text-align: left; padding: 12px; border-bottom: 2px solid #ddd; }
              td { padding: 12px; border-bottom: 1px solid #eee; }
              ${previewDoc.type === 'cert' ? '.cert-doc { border: 20px solid #1c1917; padding: 40px; height: 217mm; }' : ''}
            </style>
          </head>
          <body>
            <div class="print-container">${content}</div>
            <script>window.onload = () => { setTimeout(() => { window.print(); window.close(); }, 500); }</script>
          </body>
        </html>
      `);
      win.document.close();
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15 }}
        className="fixed inset-0 z-[100] flex items-center justify-center p-4 md:p-8"
        style={{ willChange: 'opacity' }}
      >
        <div className="absolute inset-0 bg-black/50" onClick={() => setPreviewDoc(null)} />

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 12 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
          style={{ willChange: 'transform, opacity' }}
          className="relative w-full max-w-5xl bg-white rounded-2xl shadow-xl overflow-hidden flex flex-col h-full max-h-[92vh] z-10"
        >
          {/* Modal Header */}
          <div className="px-8 py-5 border-b border-stone-100 flex items-center justify-between bg-white">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-stone-900 rounded-2xl flex items-center justify-center text-white shadow-lg">
                {previewDoc.type === 'pdf' ? <FileText className="w-5 h-5" /> : <Award className="w-5 h-5" />}
              </div>
              <div>
                <div className="text-[10px] text-stone-400 font-bold uppercase tracking-widest mb-0.5">Preview Dokumen</div>
                <div className="text-sm font-black text-stone-900 uppercase tracking-tight">
                  {previewDoc.type === 'pdf' ? 'Official Audit Report' : 'Digital Compliance Certificate'}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={handleDownload}
                className="flex items-center gap-2 bg-stone-900 text-white px-6 py-2.5 rounded-xl text-xs font-bold hover:bg-stone-800 transition-all shadow-lg hover:shadow-stone-900/20 active:scale-95"
              >
                <Download className="w-4 h-4" /> Download PDF
              </button>
              <button
                onClick={() => setPreviewDoc(null)}
                className="w-10 h-10 flex items-center justify-center hover:bg-stone-100 rounded-xl transition-colors text-stone-400 hover:text-stone-900"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Modal Content */}
          <div className="flex-1 overflow-y-auto bg-stone-100 p-6 flex justify-center">
            <div id="document-print-area" className="bg-white w-full max-w-[210mm] min-h-[297mm] p-12 text-stone-900 border border-stone-200">
              {previewDoc.type === 'pdf' ? (
                <div className="report-doc">
                  {/* Header */}
                  <div className="flex justify-between items-start border-b-[3px] border-stone-900 pb-8 mb-10">
                    <div>
                      <div className="text-[9px] font-black uppercase tracking-[0.5em] text-stone-400 mb-2">PEMALI — Platform Audit Ekologi Otonom</div>
                      <h1 className="font-serif text-4xl uppercase tracking-tighter leading-tight">Laporan Audit<br/>Lingkungan</h1>
                    </div>
                    <div className="text-right space-y-1">
                      <div className="text-[9px] font-mono text-stone-400 uppercase tracking-widest">No. Dokumen</div>
                      <div className="text-sm font-black text-stone-900 font-mono">PM-{new Date().getFullYear()}-{auditLog?.id?.toString().padStart(4, '0')}</div>
                      <div className="text-[9px] font-mono text-stone-400 mt-2">Diterbitkan: {new Date().toLocaleDateString('id-ID', { day: '2-digit', month: 'long', year: 'numeric' })}</div>
                    </div>
                  </div>

                  {/* Metadata Grid */}
                  <div className="grid grid-cols-3 gap-px bg-stone-100 border border-stone-100 mb-10 text-xs overflow-hidden rounded-lg">
                    <div className="bg-white p-4 col-span-2">
                      <div className="text-[8px] uppercase tracking-widest text-stone-400 font-black mb-1">Lokasi Audit</div>
                      <div className="font-bold text-stone-900">{auditLog?.location}, Bali, Indonesia</div>
                    </div>
                    <div className="bg-white p-4">
                      <div className="text-[8px] uppercase tracking-widest text-stone-400 font-black mb-1">Periode Analisis</div>
                      <div className="font-bold text-stone-900">12 Bulan Terakhir</div>
                    </div>
                    <div className="bg-white p-4">
                      <div className="text-[8px] uppercase tracking-widest text-stone-400 font-black mb-1">Kerangka THK</div>
                      <div className="font-bold text-stone-900">{auditLog?.thk}</div>
                    </div>
                    <div className="bg-white p-4">
                      <div className="text-[8px] uppercase tracking-widest text-stone-400 font-black mb-1">Status Kritis</div>
                      <div className="font-black text-red-600 uppercase text-[10px]">{auditLog?.issue}</div>
                    </div>
                    <div className="bg-white p-4">
                      <div className="text-[8px] uppercase tracking-widest text-stone-400 font-black mb-1">Agen Pengolah</div>
                      <div className="font-bold text-stone-900">PEMALI Autonomous V2.4</div>
                    </div>
                  </div>

                  {/* AI Narrative */}
                  <div className="mb-10">
                    <div className="flex items-center gap-3 mb-5">
                      <div className="w-6 h-[2px] bg-stone-900"></div>
                      <h2 className="font-serif text-lg text-stone-900 uppercase tracking-tight">Analisis Strategis AI</h2>
                    </div>
                    <div className="text-[11px] leading-[1.8] text-stone-700 text-justify
                      [&_h1]:font-serif [&_h1]:text-lg [&_h1]:font-bold [&_h1]:mt-6 [&_h1]:mb-2 [&_h1]:text-stone-900
                      [&_h2]:font-serif [&_h2]:text-base [&_h2]:font-bold [&_h2]:mt-6 [&_h2]:mb-2 [&_h2]:text-stone-900
                      [&_h3]:text-[11px] [&_h3]:font-black [&_h3]:uppercase [&_h3]:tracking-widest [&_h3]:mt-5 [&_h3]:mb-2 [&_h3]:text-stone-500
                      [&_p]:mb-3 [&_p]:leading-relaxed
                      [&_strong]:font-bold [&_strong]:text-stone-900
                      [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:mb-3 [&_ul]:space-y-1
                      [&_ol]:list-decimal [&_ol]:pl-5 [&_ol]:mb-3
                      [&_li]:leading-relaxed
                      [&_hr]:border-stone-100 [&_hr]:my-4
                      [&_table]:w-full [&_table]:text-[10px] [&_table]:border-collapse [&_table]:mb-4
                      [&_th]:bg-stone-900 [&_th]:text-white [&_th]:px-3 [&_th]:py-2 [&_th]:text-left [&_th]:font-black [&_th]:uppercase [&_th]:tracking-wider [&_th]:text-[9px]
                      [&_td]:px-3 [&_td]:py-2 [&_td]:border-b [&_td]:border-stone-100 [&_td]:text-stone-600
                      [&_tr:nth-child(even)_td]:bg-stone-50
                      [&_blockquote]:border-l-2 [&_blockquote]:border-stone-200 [&_blockquote]:pl-4 [&_blockquote]:italic [&_blockquote]:text-stone-500
                    ">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {auditLog?.narrative || ""}
                      </ReactMarkdown>
                    </div>
                  </div>

                  {/* Spatial Data Table */}
                  <div className="mb-10">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-6 h-[2px] bg-stone-900"></div>
                      <h2 className="font-serif text-lg text-stone-900 uppercase tracking-tight">Metrik Spasial Sentinel-2</h2>
                    </div>
                    <table className="w-full text-[11px] border-collapse">
                      <thead>
                        <tr className="bg-stone-900 text-white">
                          <th className="py-3 px-4 text-left font-black uppercase tracking-widest text-[9px]">Parameter</th>
                          <th className="py-3 px-4 text-right font-black uppercase tracking-widest text-[9px]">Nilai</th>
                          <th className="py-3 px-4 text-right font-black uppercase tracking-widest text-[9px]">Ambang Batas</th>
                          <th className="py-3 px-4 text-right font-black uppercase tracking-widest text-[9px]">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr className="border-b border-stone-100 bg-amber-50/30">
                          <td className="py-3 px-4 text-stone-700">Indeks Vegetasi (NDVI)</td>
                          <td className="py-3 px-4 text-right font-mono font-bold">{auditLog?.ndvi_score || "0.41"}</td>
                          <td className="py-3 px-4 text-right font-mono text-stone-400">≥ 0.60</td>
                          <td className="py-3 px-4 text-right font-black text-amber-600">⚠ Tertekan</td>
                        </tr>
                        <tr className="border-b border-stone-100 bg-red-50/30">
                          <td className="py-3 px-4 text-stone-700">Konversi Lahan (12 bln)</td>
                          <td className="py-3 px-4 text-right font-mono font-bold">12.4%</td>
                          <td className="py-3 px-4 text-right font-mono text-stone-400">{"< 5%"}</td>
                          <td className="py-3 px-4 text-right font-black text-red-600">✗ Anomali</td>
                        </tr>
                        <tr className="border-b border-stone-100">
                          <td className="py-3 px-4 text-stone-700">Area Terbangun Baru</td>
                          <td className="py-3 px-4 text-right font-mono font-bold">89.7 ha</td>
                          <td className="py-3 px-4 text-right font-mono text-stone-400">Baseline</td>
                          <td className="py-3 px-4 text-right font-black text-stone-600">• Valid</td>
                        </tr>
                        <tr className="border-b border-stone-100">
                          <td className="py-3 px-4 text-stone-700">Tutupan Vegetasi Aktif</td>
                          <td className="py-3 px-4 text-right font-mono font-bold">127.3 ha</td>
                          <td className="py-3 px-4 text-right font-mono text-stone-400">Baseline</td>
                          <td className="py-3 px-4 text-right font-black text-stone-600">• Valid</td>
                        </tr>
                        <tr>
                          <td className="py-3 px-4 text-stone-700">Cloud Cover Interferensi</td>
                          <td className="py-3 px-4 text-right font-mono font-bold">8.2%</td>
                          <td className="py-3 px-4 text-right font-mono text-stone-400">{"< 20%"}</td>
                          <td className="py-3 px-4 text-right font-black text-green-600">✓ Optimum</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  {/* OSINT Intel Section */}
                  <div className="mb-10 p-4 bg-stone-50 rounded-lg border border-stone-100">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-6 h-[2px] bg-stone-900"></div>
                      <h2 className="font-serif text-lg text-stone-900 uppercase tracking-tight">Intelijen OSINT</h2>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-[11px]">
                      <div>
                        <div className="text-[8px] font-black uppercase tracking-widest text-stone-400 mb-1">Sumber Berita Terdeteksi</div>
                        <div className="font-bold">3 Artikel Relevan (30 hari)</div>
                      </div>
                      <div>
                        <div className="text-[8px] font-black uppercase tracking-widest text-stone-400 mb-1">Skor Risiko Sosial</div>
                        <div className="font-black text-red-600">67% — Kritis</div>
                      </div>
                      <div className="col-span-2">
                        <div className="text-[8px] font-black uppercase tracking-widest text-stone-400 mb-1">Topik Terdeteksi</div>
                        <div className="font-medium text-stone-600">Resistensi warga terhadap pembangunan resort, alih fungsi lahan Subak, konflik agraria</div>
                      </div>
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="pt-6 border-t border-stone-200 flex justify-between items-end">
                    <div className="text-[9px] text-stone-400 font-mono uppercase tracking-[0.2em] leading-relaxed">
                      Diverifikasi via Sentinel-2 MSI L2A<br/>
                      Session ID: {sessionId?.slice(-12) || "—"}
                    </div>
                    <div className="flex flex-col items-center">
                      <div className="w-24 h-24 border-2 border-dashed border-stone-200 rounded-full flex flex-col items-center justify-center rotate-[-12deg] opacity-50">
                        <p className="text-[7px] font-black uppercase text-stone-500">PEMALI AI</p>
                        <p className="text-[10px] font-black text-stone-900">VERIFIED</p>
                      </div>
                    </div>
                  </div>
                  <div className="mt-8 text-center text-[8px] text-stone-300 uppercase tracking-[0.4em]">
                    PEMALI Autonomous Ecological Monitoring Platform • Confidential Internal Document
                  </div>
                </div>
              ) : (
                <div className="cert-doc h-full flex flex-col items-center justify-center text-center p-12 border-[20px] border-stone-900 relative">
                  <div className="absolute inset-4 border border-stone-900 pointer-events-none opacity-20"></div>

                  <div className="text-[11px] font-black tracking-[0.6em] text-stone-400 uppercase mb-20">Official Certificate of Compliance</div>

                  <h1 className="font-serif text-7xl text-stone-900 mb-2 tracking-tighter">Pemali.</h1>
                  <div className="w-20 h-1.5 bg-stone-900 mb-16"></div>

                  <p className="text-stone-400 text-sm italic mb-10 max-w-md">
                    This document serves as an official confirmation that an autonomous ecological investigation was successfully completed at
                  </p>

                  <div className="border-y-2 border-stone-100 py-8 px-16 mb-12">
                     <h2 className="font-serif text-4xl text-stone-900 tracking-tight">
                      {auditLog?.location}
                    </h2>
                  </div>

                  <p className="text-stone-500 max-w-lg leading-relaxed text-sm mb-20">
                    The analysis confirms alignment with the <b>Tri Hita Karana</b> framework, specifically protecting the integrity of <b>{auditLog?.thk}</b>. All findings have been cross-referenced with Sentinel-2 satellite feeds and validated by the PEMALI AI reasoning engine.
                  </p>

                  <div className="grid grid-cols-3 w-full items-end mt-auto pb-10">
                    <div className="flex flex-col items-center">
                      <p className="text-[9px] font-black uppercase tracking-widest text-stone-900 mb-2">Ecological Agent</p>
                      <div className="w-32 h-[1px] bg-stone-200 mb-1"></div>
                      <p className="text-[8px] font-mono text-stone-400">PEMALI-V2-AUTONOMOUS</p>
                    </div>

                    <div className="flex flex-col items-center px-4">
                      <div className="w-24 h-24 bg-stone-50 rounded-full border-2 border-double border-stone-200 flex flex-col items-center justify-center p-2">
                        <p className="text-[7px] font-black uppercase tracking-widest text-stone-300">Verified</p>
                        <div className="w-10 h-10 border border-stone-200 rounded-lg my-1 flex items-center justify-center">
                          <Award className="w-5 h-5 text-stone-300" />
                        </div>
                        <p className="text-[7px] font-serif italic text-stone-400">Original</p>
                      </div>
                    </div>

                    <div className="flex flex-col items-center">
                      <p className="text-[9px] font-black uppercase tracking-widest text-stone-900 mb-2">Timestamp</p>
                      <div className="w-32 h-[1px] bg-stone-200 mb-1"></div>
                      <p className="text-[8px] font-mono text-stone-400">{new Date().toLocaleDateString('id-ID')}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
