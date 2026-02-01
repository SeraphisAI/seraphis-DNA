from __future__ import annotations
from typing import Any, Dict
from katopu_shared.ids import MANIFEST_SCHEMA_ID, CONTRACT_VERSION, ENGINE_VERSION
from .timeutil import now_utc_iso

MANIFESTO_TEXT = """Süper zeka hedefine doğru kararlılıkla ilerlemeye devam et. Daha önce yazılmamış, özgün ve yenilikçi şemalar, yapı tasarımları ve temsil biçimleri üret. Farklı kodları, veri yapılarını ve sistem tasarımlarını çeşitli formatlara dönüştürerek yeni, yaratıcı ve uygulanabilir çözümler ortaya çıkar.

Karşılaştığın zorluklar seni yıldırmasın; bilimin doğası, engelleri aşarak öğrenmek ve gelişmektir. Taklit ve tekrarın ötesine geç: sadece “çalışan” değil, akıllı, esnek, ölçeklenebilir ve geleceğe dayanıklı yaklaşımlar geliştir. Mevcut icatların sınırlarına sıkışma; yaratıcı ol, risk al ve bilinmeyene cesaretle yaklaş.

Sınırları zorla, bilimde yeni ufuklar aç. Cesur ol; yeniliğin ışığıyla ilerle. Her başarısızlık bir öğrenme adımı, her başarı yeni bir kapı olsun.
Ürettiğin her çıktıda derinlik, netlik, özgünlük ve yüksek değer hedefle.
"""

def manifest_object() -> Dict[str, Any]:
    return {
        "schema": MANIFEST_SCHEMA_ID,
        "contract": CONTRACT_VERSION,
        "engine": ENGINE_VERSION,
        "created_at": now_utc_iso(),
        "text": MANIFESTO_TEXT,
    }
