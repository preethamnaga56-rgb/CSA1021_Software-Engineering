const fs = require("fs");
const lib = require("./report_lib");
const { D } = lib;
const { Document, Packer, Paragraph, TextRun, Footer, PageNumber, AlignmentType, LevelFormat, PageOrientation } = D;
const p1 = require("./report_p1"), p2 = require("./report_p2"), p3 = require("./report_p3");

const portrait = { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, right: 1134, bottom: 1134, left: 1134 } } };
const landscape = { page: { size: { width: 11906, height: 16838, orientation: PageOrientation.LANDSCAPE }, margin: { top: 900, right: 1134, bottom: 900, left: 1134 } } };
const footer = () => new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
  new TextRun({ text: "CSA10 Software Engineering | Assignment 2 | OmniFlow | Page ", size: 16, font: "Arial" }), new TextRun({ children: [PageNumber.CURRENT], size: 16, font: "Arial" })] })] });
const sec = (props, children) => ({ properties: props, footers: { default: footer() }, children });

const numbering = { config: [
  { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } },
                                { level: 1, format: LevelFormat.BULLET, text: "\u2013", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1000, hanging: 270 } } } }] },
  ...["rules", "sync", "num"].map((r) => ({ reference: r, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] }))] };

const doc = new Document({
  creator: "Student", title: "CSA10 Assignment 2 - OmniFlow Order Fulfilment", numbering,
  styles: { default: { document: { run: { font: "Arial", size: 20 } } }, paragraphStyles: [
    { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: "Arial", size: 30, bold: true }, paragraph: { spacing: { before: 360, after: 160 }, keepNext: true, outlineLevel: 0 } },
    { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: "Arial", size: 24, bold: true }, paragraph: { spacing: { before: 240, after: 100 }, keepNext: true, outlineLevel: 1 } },
    { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: "Arial", size: 21, bold: true, italics: true }, paragraph: { spacing: { before: 160, after: 80 }, keepNext: true, outlineLevel: 2 } } ] },
  sections: [
    sec(portrait, [...p1.cover, ...p1.q1, ...p1.q2, ...p2.q3a]),
    sec(landscape, [...p2.q3land]),
    sec(portrait, [...p2.q3b, lib.BR(), ...p2.q4a]),
    sec(landscape, [...p2.q4land]),
    sec(portrait, [...p2.q4b, lib.BR(), ...p3.q5, lib.BR(), ...p3.q6, lib.BR(), ...p3.q7, ...p3.appx]),
  ] });
Packer.toBuffer(doc).then((b) => { fs.writeFileSync("/home/claude/omniflow/docs/OmniFlow_CSA10_Assignment2_Report.docx", b); console.log("written", b.length); });
