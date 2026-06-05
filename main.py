

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading
import re
import io

app = FastAPI(title="KVKK Maskeleme Motoru")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


MODEL_YOLU = "model_best_fixed"
_durum = {"hazir": False, "mesaj": "Model yukleniyor..."}
nlp = None


def model_yukle():
    global nlp, _durum
    try:
        import spacy
        nlp = spacy.load(MODEL_YOLU)
        _durum["hazir"] = True
        _durum["mesaj"] = "Hazir"
        print(f"Model yuklendi — etiketler: {nlp.get_pipe('ner').labels}")
    except Exception as e:
        _durum["mesaj"] = f"Model yuklenemedi: {e}"
        print(f"HATA: {e}")


threading.Thread(target=model_yukle, daemon=True).start()


def normalize(s):
    return (s.replace('İ','I').replace('ı','i')
             .replace('Ğ','G').replace('ğ','g')
             .replace('Ü','U').replace('ü','u')
             .replace('Ş','S').replace('ş','s')
             .replace('Ö','O').replace('ö','o')
             .replace('Ç','C').replace('ç','c'))



REGEX_DESENLER = [
    ("IBAN",    re.compile(r'\bTR\s*\d{2}(?:\s*\d{4}){5}\s*\d{2}\b', re.IGNORECASE)),
    ("EPOSTA",  re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')),
    ("TELEFON", re.compile(r'(?<!\d)(?:\+90[\s\-]?|0090[\s\-]?|0)?(?:5[0-9]{2}|2[0-9]{2}|3[0-9]{2}|4[0-9]{2})[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)')),
    ("TUTAR",   re.compile(
        r'\b\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?\s*(?:TL|TRY|₺|EUR|€|USD|\$|lira)?'
        r'|\b\d+(?:[.,]\d{1,2})?\s*(?:TL|TRY|₺|EUR|€|USD|\$|lira)\b',
        re.IGNORECASE)),
    ("TC",      re.compile(r'(?<![\d.,])[1-9]\d{10}(?![\d.,])')),
]

ETIKET_TOKEN = {
    "KISI":    "[KISI_SANSURLENDI]",
    "ADRES":   "[ADRES_SANSURLENDI]",
    "TC":      "[TC_KIMLIK_SANSURLENDI]",
    "IBAN":    "[IBAN_SANSURLENDI]",
    "TELEFON": "[TELEFON_SANSURLENDI]",
    "EPOSTA":  "[EPOSTA_SANSURLENDI]",
    "TUTAR":   "[TUTAR_SANSURLENDI]",
}


def tc_sansurlenmeli_mi(tc: str) -> bool:
    tc = re.sub(r"\D", "", tc)
    return len(tc) == 11 and tc[0] != "0"


def yildizla(deger: str) -> str:
    out = []
    ilk_harf_kondu = False
    for ch in deger:
        if ch.isalnum():
            if not ilk_harf_kondu:
                out.append(ch)        
                ilk_harf_kondu = True
            else:
                out.append("*")
        else:
            out.append(ch)           
    return "".join(out)


def maskele_metin(metin: str, ayarlar: dict = None, stil: str = "etiket"):
    if ayarlar is None:
        ayarlar = {k: True for k in ETIKET_TOKEN}

    sayac = {k: 0 for k in ["KISI", "TC_KIMLIK", "TC_ATLA", "IBAN",
                              "TELEFON", "EPOSTA", "TUTAR", "ADRES"]}
    eslesmeler = []

    for etiket, desen in REGEX_DESENLER:
        for m in desen.finditer(metin):
            eslesmeler.append((m.start(), m.end(), etiket, metin[m.start():m.end()]))

    doc = nlp(metin)
    for ent in doc.ents:
        if ent.label_ in ("KISI", "ADRES"):
            eslesmeler.append((ent.start_char, ent.end_char, ent.label_, metin[ent.start_char:ent.end_char]))

    ONCELIK = {"IBAN": 100, "EPOSTA": 90, "TELEFON": 85, "TUTAR": 80,
                "TC": 70, "ADRES": 60, "KISI": 50}
    eslesmeler.sort(key=lambda x: (x[0], -ONCELIK.get(x[2], 0)))

    son_bitis = 0
    secilen = []
    for bas, son, etiket, deger in eslesmeler:
        if bas >= son_bitis:
            secilen.append((bas, son, etiket, deger))
            son_bitis = son

    def maske_uret(etiket, deger):
        return yildizla(deger) if stil == "yildiz" else ETIKET_TOKEN[etiket]

    secilen.sort(key=lambda x: x[0], reverse=True)
    sonuc = metin
    for bas, son, etiket, deger in secilen:
        if not ayarlar.get(etiket, True):
            if etiket == "TC":
                sayac["TC_ATLA"] += 1
            continue

        if etiket == "TC":
            if tc_sansurlenmeli_mi(deger):
                sayac["TC_KIMLIK"] += 1
                sonuc = sonuc[:bas] + maske_uret("TC", deger) + sonuc[son:]
            else:
                sayac["TC_ATLA"] += 1
        else:
            sayac_anahtar = "KISI" if etiket == "KISI" else ("ADRES" if etiket == "ADRES" else etiket)
            sayac[sayac_anahtar] += 1
            sonuc = sonuc[:bas] + maske_uret(etiket, deger) + sonuc[son:]

    toplam = sum(v for k, v in sayac.items() if k != "TC_ATLA")
    return sonuc, sayac, toplam


class MaskelemeIstegi(BaseModel):
    metin: str
    maske_kisi: bool = True
    maske_adres: bool = True
    maske_tc: bool = True
    maske_iban: bool = True
    maske_telefon: bool = True
    maske_eposta: bool = True
    maske_tutar: bool = True
    stil: str = "etiket"

    def ayarlar(self):
        return {
            "KISI": self.maske_kisi, "ADRES": self.maske_adres,
            "TC": self.maske_tc, "IBAN": self.maske_iban,
            "TELEFON": self.maske_telefon, "EPOSTA": self.maske_eposta,
            "TUTAR": self.maske_tutar,
        }


@app.get("/durum")
def durum():
    return {"hazir": _durum["hazir"], "mesaj": _durum["mesaj"]}


@app.post("/maskele")
def maskele(istek: MaskelemeIstegi):
    if not _durum["hazir"] or nlp is None:
        return JSONResponse(
            status_code=503,
            content={"hata": "Model henuz hazir degil", "mesaj": _durum["mesaj"]}
        )
    temiz, sayac, toplam = maskele_metin(istek.metin, istek.ayarlar(), istek.stil)
    return {"maskelenmis": temiz, "sayac": sayac, "toplam": toplam}


@app.post("/maskele-pdf")
async def maskele_pdf(
    dosya: UploadFile = File(...),
    maske_kisi: bool = True, maske_adres: bool = True, maske_tc: bool = True,
    maske_iban: bool = True, maske_telefon: bool = True, maske_eposta: bool = True,
    maske_tutar: bool = True, stil: str = "etiket",
):
    if not _durum["hazir"] or nlp is None:
        return JSONResponse(status_code=503, content={"hata": "Model henuz hazir degil"})

    pdf_ayarlar = {
        "KISI": maske_kisi, "ADRES": maske_adres, "TC": maske_tc,
        "IBAN": maske_iban, "TELEFON": maske_telefon,
        "EPOSTA": maske_eposta, "TUTAR": maske_tutar,
    }

    try:
        import pdfplumber
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.enums import TA_LEFT
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError as e:
        return JSONResponse(status_code=500, content={"hata": f"Eksik kütüphane: {e}"})

    icerik = await dosya.read()
    toplam_sayac = {k: 0 for k in ["KISI", "TC_KIMLIK", "TC_ATLA", "IBAN",
                                     "TELEFON", "EPOSTA", "TUTAR", "ADRES"]}

    sayfalar = []
    with pdfplumber.open(io.BytesIO(icerik)) as pdf:
        for sayfa in pdf.pages:
            metin = sayfa.extract_text() or ""
            if metin.strip():
                maskelenmis, sayac, _ = maskele_metin(metin, pdf_ayarlar, stil)
                for k in toplam_sayac:
                    toplam_sayac[k] += sayac.get(k, 0)
                sayfalar.append(maskelenmis)
            else:
                sayfalar.append("")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    normal = ParagraphStyle(
        'TR',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=14,
        spaceAfter=4,
    )
    sayfa_baslik = ParagraphStyle(
        'SayfaBaslik',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor='#888899',
        spaceAfter=8,
        spaceBefore=16,
    )

    story = []
    for i, sayfa_metin in enumerate(sayfalar):
        if len(sayfalar) > 1:
            story.append(Paragraph(f"— Sayfa {i+1} —", sayfa_baslik))
        for satir in sayfa_metin.split('\n'):
            satir = satir.strip()
            if satir:
                satir = (satir.replace('&', '&amp;')
                              .replace('<', '&lt;')
                              .replace('>', '&gt;'))
                story.append(Paragraph(satir, normal))
            else:
                story.append(Spacer(1, 6))

    doc.build(story)
    buffer.seek(0)

    toplam = sum(v for k, v in toplam_sayac.items() if k != "TC_ATLA")
    dosya_adi = dosya.filename.replace('.pdf', '_maskelenmis.pdf')

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{dosya_adi}"',
            "X-Toplam-Maske": str(toplam),
            "X-Sayac": str(toplam_sayac),
        }
    )


@app.get("/", response_class=HTMLResponse)
def anasayfa():
    with open("index.html", encoding="utf-8") as f:
        return f.read()