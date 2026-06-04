import os

from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "").strip()

# Backend isteklerinin zaman aşımı (saniye). Render ücretsiz tier'da servis uykudan
# ~55 sn'de kalktığı için varsayılanı yüksek tutuyoruz; böylece soğuk açılışta
# istekler hata vermeden bekler. Env ile ayarlanabilir.
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "90"))

# n8n workflow'unun analiz sonucunu geri göndereceği backend adresi ve secret'ı.
# n8n harici bir servis olduğu için backend'in PUBLIC adresi gerekir (API_URL üretimde
# public backend URL'idir). WEBHOOK_SECRET backend'deki ile aynı olmalıdır.
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
WEBHOOK_CALLBACK_URL = os.getenv("WEBHOOK_CALLBACK_URL", f"{API_URL}/webhook/lead-score")
