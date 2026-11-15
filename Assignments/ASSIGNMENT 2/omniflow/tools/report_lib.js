// Helpers for building the Word report with docx-js (black-and-white, print friendly).
const fs = require("fs");
const D = require("docx");
const { Paragraph, TextRun, Table, TableRow, TableCell, ImageRun, HeadingLevel, WidthType, ShadingType, AlignmentType,
        PageBreak, BorderStyle } = D;
const DATA = JSON.parse(fs.readFileSync("/home/claude/report_data.json", "utf8"));
const IMG = "/home/claude/omniflow/docs/diagrams/";
const FONT = "Arial";

function runs(text, base = {}) {
  const out = []; const parts = String(text).split(/(\*\*[^*]+\*\*|`[^`]+`)/);
  for (const p of parts) {
    if (!p) continue;
    if (p.startsWith("**")) out.push(new TextRun({ text: p.slice(2, -2), bold: true, font: FONT, ...base }));
    else if (p.startsWith("`")) out.push(new TextRun({ text: p.slice(1, -1), font: "Courier New", ...base, size: Math.max(14, (base.size || 20) - 2) }));
    else out.push(new TextRun({ text: p, font: FONT, ...base }));
  }
  return out;
}
const P = (text, o = {}) => new Paragraph({ children: runs(text, { size: o.size || 20, italics: o.italics }), spacing: { after: o.after ?? 100, line: 264 },
  alignment: o.align, keepNext: o.keepNext, indent: o.indent });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: t, font: FONT })], pageBreakBefore: false });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t, font: FONT })] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text: t, font: FONT })] });
const B = (text, level = 0) => new Paragraph({ numbering: { reference: "bul", level }, children: runs(text, { size: 20 }), spacing: { after: 60, line: 259 } });
const N = (text, ref = "num") => new Paragraph({ numbering: { reference: ref, level: 0 }, children: runs(text, { size: 20 }), spacing: { after: 60, line: 259 } });
const BR = () => new Paragraph({ children: [new PageBreak()] });
const SP = (n = 80) => new Paragraph({ children: [], spacing: { after: n } });
const LABEL = (t) => new Paragraph({ children: [new TextRun({ text: t, bold: true, italics: true, font: FONT, size: 18 })], spacing: { before: 60, after: 120 }, alignment: AlignmentType.CENTER });
const NOTE = (t) => new Paragraph({ children: runs("**Status label:** " + t, { size: 18, italics: true }), spacing: { after: 120 },
  border: { left: { style: BorderStyle.SINGLE, size: 12, color: "808080", space: 6 } }, indent: { left: 140 } });

const bd = { style: BorderStyle.SINGLE, size: 4, color: "808080" };
const borders = { top: bd, bottom: bd, left: bd, right: bd };
function cell(text, w, o = {}) {
  const lines = Array.isArray(text) ? text : String(text).split("\n");
  return new TableCell({ width: { size: w, type: WidthType.DXA }, borders, margins: { top: 40, bottom: 40, left: 70, right: 70 },
    shading: o.head ? { fill: "D9D9D9", type: ShadingType.CLEAR, color: "auto" } : (o.fill ? { fill: o.fill, type: ShadingType.CLEAR, color: "auto" } : undefined),
    children: lines.map((l) => new Paragraph({ children: runs(l, { size: o.size || 16, bold: o.head }), spacing: { after: 20, line: 240 } })) });
}
function T(headers, rows, widths, o = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const trs = [new TableRow({ tableHeader: true, cantSplit: true, children: headers.map((h, i) => cell(h, widths[i], { head: true, size: o.size })) })];
  for (const r of rows) trs.push(new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, widths[i], { size: o.size, fill: o.firstColFill && i === 0 ? "F2F2F2" : undefined })) }));
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths, rows: trs });
}
function FIG(file, caption, maxW = 640, maxH = 780) {
  const [w, h] = DATA.dims[file]; const s = Math.min(maxW / w, maxH / h);
  return [new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 80, after: 40 },
    children: [new ImageRun({ type: "png", data: fs.readFileSync(IMG + file), transformation: { width: Math.round(w * s), height: Math.round(h * s) },
      altText: { title: caption, description: caption, name: file } })] }), LABEL(caption)];
}
module.exports = { D, DATA, P, H1, H2, H3, B, N, BR, SP, LABEL, NOTE, T, FIG, runs, FONT };
