#!/usr/bin/env python3
"""Build book (the shop guide) as a letter-size PDF: cover, lettered parts list, milling plan, numbered
build steps with pictures, glue-up checks, finishing, and an index of the full-size sheets.

  python3 scripts/build_book.py --init build/cutlist.json > book.json     # a skeleton to fill in
  python3 scripts/build_book.py book.json --out build/Build_book.pdf

book.json (paths are relative to the book.json file):
{
  "title": "Cabinet on stand", "subtitle": "shop drawings and build steps", "maker": "Your name",
  "cutlist": "build/cutlist.json",           # parts list, milling plan and model hash come from here
  "cover": "renders/hero.jpg",               # hero render: finished wood, on white
  "intro": "One paragraph on the piece, the wood, and the order of work.",
  "tools": ["hollow-chisel mortiser, 1/4 and 3/8 chisels", "router table, 1/4 slot cutter"],
  "sections": [
    {"title": "Stand", "steps": [
      {"title": "Mortise the legs", "parts": ["A"],
       "text": "Lay out from the top of each leg. Start every mortise 1/2 in down ...",
       "image": "renders/step_legs.jpg",     # process shots are plain wood: no finish until the finishing step
       "check": "Dry-fit each apron; the shoulder must seat with no light under it."}]}],
  "finishing": {"text": "...", "image": "renders/finished.jpg"},
  "sheets": ["build/fullsize_tiled.pdf"],    # listed at the back with how to tape and check them
  "notes": ["Hinges: Brusso sells them by the pair: 4 hinges = 2 pairs."]
}
Pictures are placed full column width, never cropped. Every page carries the model file and its hash so
nobody builds from a stale book.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import furnlib as F


def init(cutlist_path):
    cl = json.load(open(cutlist_path))
    wood = [r for r in cl["parts"] if r["role"] != "hardware" and r["letter"]]
    return {
        "title": cl["meta"]["title"], "subtitle": "shop drawings and build steps", "maker": "",
        "cutlist": cutlist_path, "cover": "", "intro": "", "tools": [],
        "sections": [{"title": "Mill the stock", "steps": [
            {"title": f"Batch {i + 1}: {b['species']} at {F.frac(b['T'])}", "parts": sorted({c[0] for s in b['strips'] for c in s['cuts']}),
             "text": f"Plane everything in this batch at one setting from {b['stock']}. Rip, joint and plane the strips while they are long, then cross-cut as the milling plan says.",
             "image": "", "check": "Every part in the batch measures the same thickness."} for i, b in enumerate(cl["milling"])]},
            {"title": "Joinery", "steps": [
                {"title": f"{r['letter']}: {r['label']}", "parts": [r["letter"]], "text": "", "image": "", "check": ""} for r in wood]},
            {"title": "Glue-up", "steps": [{"title": "Dry fit, then glue", "parts": [], "text": "", "image": "", "check": ""}]}],
        "finishing": {"text": "", "image": ""}, "sheets": [], "notes": []}


def build(book_path, out, theme_path=None):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib.colors import Color
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Image, Table,
                                    TableStyle, PageBreak, KeepTogether, CondPageBreak)
    from reportlab.lib.styles import ParagraphStyle
    from PIL import Image as PILImage

    T = F.theme(theme_path)
    for k, f in (("Serif", "serif"), ("SerifLight", "serif_light"), ("Display", "serif_display"), ("Mono", "mono")):
        pdfmetrics.registerFont(TTFont(k, T["fonts"][f]))
    col = lambda h: Color(*F.hex_rgb(h))
    INK, HEAD, MUTED, RED, RULE = col(T["ink"]), col(T["ink_heading"]), col(T["muted"]), col(T["red"]), col(T["rule"])
    base = os.path.dirname(os.path.abspath(book_path))
    B = json.load(open(book_path))
    P = lambda p: p if (not p or os.path.isabs(p)) else os.path.join(base, p)
    cl = json.load(open(P(B["cutlist"]))) if B.get("cutlist") else None
    meta = cl["meta"] if cl else {}
    stamp = f"{meta.get('model', '')}  ·  sha256 {meta.get('sha256', '')}" if meta else ""

    st = dict(
        title=ParagraphStyle("t", fontName="Display", fontSize=30, leading=36, textColor=HEAD, spaceAfter=6),
        sub=ParagraphStyle("s", fontName="SerifLight", fontSize=14, leading=18, textColor=INK, spaceAfter=18),
        h1=ParagraphStyle("h1", fontName="Display", fontSize=17, leading=24, textColor=HEAD, spaceBefore=6, spaceAfter=10),
        h2=ParagraphStyle("h2", fontName="Serif", fontSize=12, leading=16, textColor=HEAD, spaceBefore=10, spaceAfter=4),
        body=ParagraphStyle("b", fontName="SerifLight", fontSize=10.5, leading=15, textColor=INK, spaceAfter=6),
        mono=ParagraphStyle("m", fontName="Mono", fontSize=8, leading=11, textColor=INK),
        check=ParagraphStyle("c", fontName="Serif", fontSize=10, leading=14, textColor=RED, spaceAfter=8),
        num=ParagraphStyle("n", fontName="Display", fontSize=22, leading=24, textColor=RED))

    def footer(cv, doc):
        cv.saveState()
        cv.setFont("Mono", 7); cv.setFillColor(MUTED)
        cv.drawString(0.7 * inch, 0.45 * inch, f"{B.get('title', '').upper()}  ·  {stamp}")
        cv.drawRightString(letter[0] - 0.7 * inch, 0.45 * inch, str(doc.page))
        cv.restoreState()

    doc = BaseDocTemplate(out, pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch,
                          topMargin=0.7 * inch, bottomMargin=0.8 * inch, title=B.get("title", ""), author=B.get("maker", ""))
    fr = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate(id="p", frames=[fr], onPage=footer)])
    W = doc.width

    def img(path, maxh=4.6 * inch):
        path = P(path)
        if not path or not os.path.exists(path):
            return None
        with PILImage.open(path) as im:
            w, h = im.size
        s = min(W / w, maxh / h)
        return Image(path, w * s, h * s)

    def tbl(rows, widths, header=True):
        t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
        t.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "Mono", 8), ("TEXTCOLOR", (0, 0), (-1, -1), INK),
                               ("FONT", (0, 0), (-1, 0), "Serif", 9), ("TEXTCOLOR", (0, 0), (0, -1), RED),
                               ("LINEBELOW", (0, 0), (-1, 0), 0.5, RULE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 2)]))
        return t

    S = []
    S += [Spacer(1, 0.6 * inch), Paragraph(B.get("title", "").upper(), st["title"]), Paragraph(B.get("subtitle", ""), st["sub"])]
    im = img(B.get("cover"), 5.6 * inch)
    if im:
        S += [im, Spacer(1, 12)]
    if B.get("maker"):
        S.append(Paragraph(B["maker"], st["body"]))
    if stamp:
        S.append(Paragraph(f"Built from {stamp}. If your model's hash is different, this book is out of date.", st["mono"]))
    S.append(PageBreak())
    if B.get("intro"):
        S += [Paragraph("ABOUT THIS PIECE", st["h1"]), Paragraph(B["intro"], st["body"])]
    if B.get("tools"):
        S += [Paragraph("TOOLS", st["h2"])] + [Paragraph("· " + t, st["body"]) for t in B["tools"]]
    if cl:
        S += [CondPageBreak(3 * inch), Paragraph("PARTS", st["h1"]),
              Paragraph("Finished sizes in inches, thickness x width x length, length with the grain. Each part keeps its letter on every drawing, sheet and step.", st["body"])]
        rows = [["", "Part", "Qty", "T", "W", "L", "Material"]]
        for r in cl["parts"]:
            if r["role"] == "hardware":
                continue
            rows.append([r["letter"], Paragraph(r["label"], st["mono"]), r["qty"], F.frac(r["T"]), F.frac(r["W"]), F.frac(r["L"]),
                         Paragraph(r["material"] or " ".join(x for x in (r["species"], r["cut"]) if x) or "wood", st["mono"])])
        S.append(tbl(rows, [0.35 * inch, 2.3 * inch, 0.4 * inch, 0.7 * inch, 0.8 * inch, 0.8 * inch, W - 5.35 * inch]))
        hw = [r for r in cl["parts"] if r["role"] == "hardware"]
        if hw:
            S += [Paragraph("HARDWARE", st["h2"])] + [Paragraph(f"· {r['label']} x{r['qty']}", st["body"]) for r in hw]
        S += [PageBreak(), Paragraph("MILLING PLAN", st["h1"]),
              Paragraph("One batch per thickness: plane the whole batch at one setting so mating parts match. Rip each strip and joint and plane it while it is still long; keep anything going over the jointer or planer at least 12 in. Only then cross-cut, longest first.", st["body"])]
        for i, b in enumerate(cl["milling"], 1):
            blk = [Paragraph(f"Batch {i}: {b['species']}, {F.frac(b['T'])} thick from {b['stock']}  ·  buy about {b['board_feet_buy']:.1f} bd ft", st["h2"])]
            rows = [["Strip", "Rip", "Cross-cuts, in order"]]
            for s in b["strips"]:
                rows.append([F.frac(s["W"]), F.frac(s["rip"]), Paragraph(", ".join(f"<font color='{T['red']}'>{c[0]}</font> {c[1]} {F.frac(c[2])}" for c in s["cuts"]), st["mono"])])
            blk.append(tbl(rows, [0.8 * inch, 0.8 * inch, W - 1.6 * inch]))
            S.append(KeepTogether(blk))
    cm = B.get("cutmap")
    if cm:                       # board-by-board cut map from scripts/cutmap.py (the user's own logged boards)
        cmd = json.load(open(cm if os.path.isabs(cm) else os.path.join(os.path.dirname(os.path.abspath(book_path)), cm)))
        S += [PageBreak(), Paragraph("BOARD-BY-BOARD CUT MAP", st["h1"]),
              Paragraph("One line per board, in cutting order. Chops are measured from the board's labelled end, rips from the jointed edge, "
                        "widest rip first so the fence only moves one way. Mill anything that goes over the jointer or planer while it is "
                        "still 12 in or longer, then cross-cut.", st["body"])]
        if cmd["meta"].get("only"):
            S.append(Paragraph("Today: " + cmd["meta"]["only"], st["mono"]))
        S += [Paragraph(l, st["mono"]) for l in cmd["lines"]]
        if cmd.get("need"):
            S.append(Paragraph("Need more wood: " + ", ".join(f"{x['letter']} {x['label']}" for x in cmd["need"]), st["check"]))
    n = 0
    for sec in B.get("sections", []):
        S += [PageBreak(), Paragraph(sec["title"].upper(), st["h1"])]
        if sec.get("text"):
            S.append(Paragraph(sec["text"], st["body"]))
        for step in sec.get("steps", []):
            n += 1
            blk = [Table([[Paragraph(str(n), st["num"]), Paragraph(step.get("title", ""), st["h2"])]], colWidths=[0.5 * inch, W - 0.5 * inch],
                         style=[("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("LEFTPADDING", (0, 0), (-1, -1), 0)])]
            if step.get("parts"):
                blk.append(Paragraph("Parts " + "  ".join(f"<font color='{T['red']}'>{p}</font>" for p in step["parts"]), st["mono"]))
            im = img(step.get("image"))
            if im:
                blk += [Spacer(1, 4), im, Spacer(1, 4)]
            if step.get("text"):
                blk.append(Paragraph(step["text"], st["body"]))
            if step.get("check"):
                blk.append(Paragraph("Check: " + step["check"], st["check"]))
            S.append(KeepTogether(blk))
    fin = B.get("finishing") or {}
    if fin.get("text") or fin.get("image"):
        S += [PageBreak(), Paragraph("FINISHING", st["h1"])]
        im = img(fin.get("image"), 5 * inch)
        if im:
            S.append(im)
        if fin.get("text"):
            S.append(Paragraph(fin["text"], st["body"]))
    if B.get("sheets") or B.get("notes"):
        S += [PageBreak(), Paragraph("FULL-SIZE SHEETS AND NOTES", st["h1"])]
        for s in B.get("sheets", []):
            S.append(Paragraph(f"· {os.path.basename(s)}", st["body"]))
        if B.get("sheets"):
            S.append(Paragraph("Print at 100% (no fit-to-page). Measure the 1 in check square on the first page before cutting anything. "
                               "Tiled pages overlap 1/2 in: trim one edge, line up the outlines and tape. Parts are drawn as red outlines at full size; "
                               "lay them on the stock to check figure and grain, and transfer curves and bevels from them.", st["body"]))
        for t in B.get("notes", []):
            S.append(Paragraph("· " + t, st["body"]))
    doc.build(S)
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book", nargs="?")
    ap.add_argument("--init", metavar="CUTLIST_JSON", help="print a skeleton book.json made from a cut list")
    ap.add_argument("--out", default="Build_book.pdf")
    ap.add_argument("--theme")
    a = ap.parse_args()
    if a.init:
        json.dump(init(a.init), sys.stdout, indent=1)
        return
    if not a.book:
        ap.error("book.json is required (or --init)")
    n = build(a.book, a.out, a.theme)
    print(f"{n} steps -> {a.out}")


if __name__ == "__main__":
    main()
