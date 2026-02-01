# Katopu GenLab (Ultra) — Faz 0 Kanıtlı Envanter ve Uyum Matrisi

## 1) Kanıtlı tespitler (envanter)

### 1.1 Akış diyagramı (metin)
UI (Streamlit) **Lab / Fallback / Policy / Telemetry / Diagnostics / Rapor/Export** → API (`/nl/spec`, `/edit/apply`, `/run`, `/policy`, `/health`) → Ω motor (Omega engine) → PolicyEvaluator → sonuç/rapor üretimi (JSON/PDF/XLSX) akışı vardır. UI tarafında API kapalıysa local engine + policy ile fallback çalışır ve rapor/exports üretir. (Kanıtlar: UI modülleri ve API çağrı zinciri; `ui/app.py`, API uçları; `api/app/main.py`, local engine + report exporter; `ui/app.py`).

### 1.2 Mimari bileşenler (doğrulanmış)
- **API uçları**: `/health`, `/run`, `/nl/spec`, `/edit/apply`, `/policy` (FastAPI tanımları `api/app/main.py`).
- **UI modülleri**:
  - **Lab**: ana çalıştırma ve spec-first akış (`ui/app.py`, Lab sayfası ve run chain).
  - **Fallback**: API yoksa local apply + policy (`ui/app.py`, `local_apply_with_policy`, `enable_local_fallback`).
  - **Policy**: policy görüntüleme/düzenleme + audit tail (`ui/app.py`, Policy panel & tail). 
  - **Telemetry**: telemetry tail paneli (`ui/app.py`).
  - **Diagnostics**: API bağlantı testleri (`ui/app.py`).
  - **Rapor/Export**: PDF/XLSX/JSON export, rapor tarihçesi (`ui/app.py`, report helpers + export buttons).
- **UI çıktı sözleşme sürümleri**:
  - `katopu.ucp.ultra.final.v1` (contract) ve `ucp_ultra_core_v1` (engine) sürümleri tek kaynak olarak tanımlı (`src/katopu_shared/ids.py`).
  - UI status rozetlerinde bu sürümler gösteriliyor (`ui/app.py`).

## 2) Sözleşme uyumu matrisi (kanıtlı)

**Notlar**: 
- Unified schema `katopu.editop.v2` içinde deletion/insertion/substitution/conditional_substitution tanımları var (`src/katopu_core/unified_schema.py`).
- Omega engine (`apply_editspec`) yalnız `PREFIX_DELETE`, `SUFFIX_DELETE`, `POINT_MUTATION` op setini uyguluyor (`src/katopu_core/omega_engine.py`).
- Local engine (`local_apply`) editop.v2 op setini (deletion/insertion/substitution/conditional_substitution dahil) uyguluyor (`src/katopu_core/apply.py`).
- Policy allowlist ve op map mevcut; insert uzunluğu kontrolü `op.get("insert")` üzerinden yapılıyor (`src/katopu_policy/evaluator.py`).
- Testler: sadece prefix_deletion ve NLP parsing gibi sınırlı kapsama var (`tests/test_apply.py`, `tests/test_nlp_parse.py`).

| Op tipi | Şema vaat ediyor mu? | Motor uyguluyor mu? | Policy doğru denetliyor mu? | Test kapsıyor mu? |
|---|---|---|---|---|
| deletion | Evet: editop.v2 tanımı var (`unified_schema.py`) | **Local**: Evet (`apply.py`). **Omega**: Hayır (apply_editspec yalnız legacy op seti) (`omega_engine.py`) | allow_ops listesinde deletion var, ama API op stringi ile gelmiyor (`evaluator.py`) | Hayır (test yok) |
| insertion | Evet (`unified_schema.py`) | **Local**: Evet (`apply.py`). **Omega**: Hayır (`omega_engine.py`) | allow_ops listesinde insertion var; insert len kontrolü `insert` alanına bakıyor (editop.v2 `seq` kullanıyor) (`evaluator.py`) | Hayır (test yok) |
| substitution | Evet (`unified_schema.py`) | **Local**: Evet (`apply.py`). **Omega**: Hayır (`omega_engine.py`) | allow_ops listesinde substitution var; op mapping `POINT_MUTATION→substitution` (`evaluator.py`) | Hayır (test yok) |
| conditional_substitution | Evet (`unified_schema.py`) | **Local**: Evet (`apply.py`). **Omega**: Hayır (`omega_engine.py`) | allow_ops listesinde conditional_substitution var (`evaluator.py`) | Hayır (test yok) |
| PREFIX_DELETE | Eski spec (editspec.v1) op setinde var (`contract_utils.py`) | **Omega**: Evet (`omega_engine.py`) | allow_ops içinde PREFIX_DELETE ve map var (`evaluator.py`) | Kısmi: prefix delete test var (local_apply) (`tests/test_apply.py`) |
| SUFFIX_DELETE | Eski spec op setinde var (`contract_utils.py`) | **Omega**: Evet (`omega_engine.py`) | allow_ops içinde SUFFIX_DELETE ve map var (`evaluator.py`) | Hayır (test yok) |
| POINT_MUTATION | Eski spec op setinde var (`contract_utils.py`) | **Omega**: Evet (`omega_engine.py`) | allow_ops içinde POINT_MUTATION ve map var (`evaluator.py`) | Hayır (test yok) |

## 3) Dead code / kablosu takılmamış vaatler

- **TelemetryEmitter** sınıfı tanımlı, fakat API/engine akışında kullanılmıyor; UI sadece log tail okuyor (`src/katopu_telemetry/emitter.py`, `ui/app.py`).
- **PolicyAudit** yazıcısı tanımlı, fakat `PolicyEvaluator.evaluate()` içinde audit write çağrısı yok; UI sadece log tail okuyor (`src/katopu_policy/audit.py`, `src/katopu_policy/evaluator.py`, `ui/app.py`).
- **API config ayarları** (telemetry/policy override vb.) `api/app/config.py` içinde tanımlı ama `api/app/main.py` içinde doğrudan env okunuyor; `Settings` kullanılmıyor (`api/app/config.py`, `api/app/main.py`).

## 4) En kritik teknik borçlar (öncelikli)
1. **EditSpec ↔ EditOp uyumsuzluğu**: `validate_editspec` yalnızca legacy op setini kabul ediyor; unified schema editop.v2 opset’i API yolunda uygulanmıyor (`contract_utils.py`, `omega_engine.py`, `apply.py`).
2. **Tek motor hedefi kırık**: Local engine editop.v2 için çalışıyor, Omega engine legacy opset’e kilitli (`apply.py`, `omega_engine.py`).
3. **Policy override ve audit/telemetry kablosu** eksik: UI override yazsa da API policy merge / audit write / telemetry emit yapılmıyor (`ui/app.py`, `api/app/main.py`, `katopu_policy/audit.py`, `katopu_telemetry/emitter.py`).
4. **Insertion limit kontrolünde alan adı**: `allow_op` insert uzunluğu kontrolü `insert` alanına bakıyor; editop.v2 `seq` kullanıyor (`katopu_policy/evaluator.py`, `katopu_core/apply.py`).
5. **PDF diff anomalisine açık**: PDF rapor `common_affix_diff` üzerinden “Added/Removed” yazıyor; tek karakter ghost sorunu için alternatif yöntem yok (`ui/app.py`).

## 5) Faz 0 yapılacaklar + PR sırası (kopya plan)
1. **PR-1**: Envanter + matrisi + test baseline (bu doküman). 
2. **PR-2**: EditOp v2 standardizasyon + compat normalizer; `validate_editspec` genişlet. 
3. **PR-3**: Omega apply yolu tekleştirme (local_apply mantığını resmi yürütücüye bağla). 
4. **PR-4**: Policy override merge + /policy genişletme + insertion alan fix. 
5. **PR-5**: Telemetry + audit wiring (maskeli) + UI tail doğrulama. 
6. **PR-6**: PDF diff fix + regresyon test.

## 6) Kabul kriterleri checklist (Faz 0)
- [ ] EditSpec opset’i editop.v2 ile uyumlu; eski format compat layer ile çalışıyor.
- [ ] Unified schema opset’i (deletion/insertion/substitution/conditional_substitution) API uçtan uca çalışıyor.
- [ ] Policy override gerçek merge ile API davranışını değiştiriyor.
- [ ] Telemetry/audit event’leri maskeli ve gerçek akışta yazılıyor.
- [ ] PDF rapor “(yok) g” anomalisi testle yakalanıp düzeltilmiş.

## 7) Test sonuçları (baseline)
- `pytest -q` **başarısız**: `httpx` bağımlılığı eksik (Network erişimi kapalı olduğundan `pip install -r requirements-dev.txt` de başarısız). (test logu: yerel çalışma çıktısı).

## 8) Güvenlik/gizlilik doğrulaması
- Mask/redaction fonksiyonu mevcut: `mask_sequence` ve `mask_dict` sequence alanlarını yıldız veya kısmi gösterir (`src/katopu_privacy/mask.py`).
- Audit/telemetry kablolu olmadığı için şu an bu maskeleme kullanıma alınmıyor (telemetry/audit callsite yok; `katopu_telemetry/emitter.py`, `katopu_policy/audit.py`).
