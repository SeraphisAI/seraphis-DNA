# Katopu GenLab — ULTRA UI + Fallback + Policy Panel (v0.2.0)

Bu proje **in-silico** (metin tabanlı) DNA edit simülasyonu yapar.
- Wet-lab / patojen tasarımı gibi yüksek riskli içerikler hedeflenmez.
- **Policy pack** belirli niyet desenlerini bloklar ve (opsiyonel) loglarda sequence maskeler.

## Neler var?

- **API** (FastAPI): `/health`, `/run`, `/nl/spec`, `/edit/apply` ve `/policy`...
- **UI** (Streamlit):
  - **Lab**: tek seferde çalıştır + "Spec Üret" + "Edit Uygula"
  - **Fallback**: API yoksa *local engine* ile çalıştırma (policy check dahil)
  - **Policy**: base + override policy görüntüleme/düzenleme + audit tail
  - **Telemetry**: telemetry tail + hızlı istatistik
  - **Diagnostics**: bağlantı testi, hızlı komutlar

## Hızlı Başlat (Docker)

```bash
cd infra
docker compose up -d --build
```

- UI: http://localhost:8501
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

Kapatmak için:
```bash
cd infra
docker compose down
```

## Windows (PowerShell)

- `windows_shortcuts/start_katopu.ps1` çalıştırın.
- `windows_shortcuts/api_examples.ps1` örnek çağrılar içerir.

> PowerShell'de `curl` alias çakışmaları yüzünden `curl.exe` veya `Invoke-RestMethod` kullanın.

## Policy Override (UI Policy Panel)

- Base policy dosyası: `policy/policies/default.policy.json`
- Override dosyası (UI üzerinden yazılır): `data/policy_override.json`
  - Override var ise API/UI otomatik bunu yükler.
  - Override’ı silmek için Policy tabında "Override sıfırla".

> Güvenlik için: `KATOPU_POLICY_MUTABLE=false` iken API tarafındaki `POST /policy/*` endpoint'leri kapalıdır.

## Telemetry

Telemetry varsayılan kapalı.

`.env` (infra dizininde) içine:
- `KATOPU_TELEMETRY_ENABLED=true`
- `KATOPU_TELEMETRY_SAMPLE_RATE=0.1`

Dosyalar `/data/` altında tutulur (docker volume ile kalıcı):
- `/data/telemetry.jsonl`
- `/data/policy_audit.log`

## Test

Yerelde:
```bash
pip install -r requirements-dev.txt
pytest -q
```

## Migration

Örnek:
```bash
python -m migrations.migrate --in export.json --out export_v0_2_0.json --to 0.2.0
```
