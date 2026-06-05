# 🤖 Yapay Zeka Projesi

Doğal dil işleme (NLP) tabanlı bu uygulama, FastAPI ile geliştirilmiş bir web servisi sunar. SpaCy Transformers ile eğitilmiş model üzerinden tahmin yapılabilmekte ve tarayıcı arayüzü ile kullanılabilmektedir.

---

## 📋 Ön Koşullar

- **Python 3.11** kurulu olmalıdır → [python.org](https://www.python.org/downloads/)

---

## 🚀 Kurulum

### 1. Projeyi Klonla

```bash
git clone https://github.com/Chesteak/Personal-Data-Masking
cd proje-adi
```

### 2. Sanal Ortam Oluştur

```bash
python -m venv venv
```

### 3. Sanal Ortamı Aktif Et

```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 4. Bağımlılıkları Yükle

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 📁 Dizin Yapısı

```
proje/
├── main.py               # Uygulama kaynak kodu
├── requirements.txt      # Bağımlılık listesi
├── index.html            # Tarayıcı arayüzü
├── model_best_fixed/     # Eğitimli model dosyaları
└── venv/                 # Sanal ortam (git'e eklenmez)
```

---

## ▶️ Uygulamayı Başlat

```bash
uvicorn main:app --reload
```

Uygulama başlatıldıktan sonra tarayıcıdan şu adrese gidin:

```
http://127.0.0.1:8000
```

---

## 📦 Kullanılan Kütüphaneler

| Kütüphane | Açıklama |
|---|---|
| `fastapi` | Web API framework |
| `uvicorn` | ASGI sunucusu |
| `spacy` | Doğal dil işleme |
| `spacy-transformers` | Transformer tabanlı NLP modelleri |
| `pydantic` | Veri doğrulama |
| `python-multipart` | Form verisi desteği |

---

## ⚠️ Notlar

- `model_best_fixed/` klasörü büyük dosyalar içeriyorsa Git LFS kullanılması önerilir.
- `venv/` klasörü `.gitignore` ile versiyon kontrolüne dahil edilmemiştir.
