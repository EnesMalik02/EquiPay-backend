# 1. Aşama: Python 3.13 tabanlı hafif imajı kullanıyoruz
FROM python:3.13-slim

# Python'un logları anında çıktı vermesini sağlar ve bytecode derlemesini optimize eder
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1

# Çalışma dizini
WORKDIR /app

# Astral'ın ultra hızlı paket yöneticisi olan 'uv'yi imaja dahil ediyoruz
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Bağımlılık dosyalarını (pyproject.toml ve uv.lock) kopyalıyoruz.
# Önce bu dosyaları kopyalamak, kod değişse bile bağımlılık katmanının cache'den gelmesini sağlar.
COPY pyproject.toml uv.lock ./

# Sadece bağımlılıkları yüklüyoruz (Proje kodunu henüz kopyalamadan)
RUN uv sync --frozen --no-install-project --no-dev

# Tüm proje dosyalarını kopyalıyoruz
COPY . .

# Projenin kendisini yüklüyoruz
RUN uv sync --frozen --no-dev

# Python yoluna /app dizinini ekleyerek src.main importlarını garantiye alıyoruz
ENV PYTHONPATH=/app

# Render varsayılan olarak 10000 portunu bekler. 
# Eğer Render dashboard'dan farklı bir port ayarlamadıysanız 10000 en güvenli tercihtir.
EXPOSE 8000

# Uygulamayı 'uv run' üzerinden başlatıyoruz
CMD ["sh", "-c", "uv run gunicorn src.main:app \
    --workers ${WEB_CONCURRENCY:-4} \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 60"]