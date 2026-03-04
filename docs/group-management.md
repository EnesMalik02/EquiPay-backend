# Group Management API

---

## 1. Grubu Sil

```
DELETE /groups/{group_id}
```

**Koşullar**
- İstek yapan kullanıcının `role = admin` olması gerekir.
- Gruptaki **tüm bakiyelerin sıfır** olması gerekir (ödenmemiş harcama kalmamalı).
- İşlem **geri alınamaz**; tüm veriler silinir.

**Request**

| Parametre | Yer | Tür | Açıklama |
|-----------|-----|-----|----------|
| `group_id` | path | UUID | Silinecek grubun ID'si |

Body yok.

**Response**

| Durum | Açıklama |
|-------|----------|
| `204 No Content` | Grup silindi |
| `403 Forbidden` | Kullanıcı admin değil |
| `404 Not Found` | Grup bulunamadı |
| `409 Conflict` | Grupta ödenmemiş bakiye var |

---

## 2. Gruptan Çık

```
POST /groups/{group_id}/leave
```

**Koşullar**
- Grubun **kurucusu** çıkamaz (önce başka admini atayın veya grubu silin).
- Kullanıcının gruba karşı **net bakiyesi sıfır** olmalı (ne borcu ne alacağı).
- Çıkış sonrası `left_at` doldurulur; `left_at IS NOT NULL` eski üye anlamına gelir.

**Request**

| Parametre | Yer | Tür | Açıklama |
|-----------|-----|-----|----------|
| `group_id` | path | UUID | Çıkılacak grubun ID'si |

Body yok.

**Response**

| Durum | Body | Açıklama |
|-------|------|----------|
| `200 OK` | `{"detail": "Gruptan başarıyla çıkıldı."}` | Başarılı |
| `403 Forbidden` | — | Kurucu çıkmaya çalışıyor |
| `404 Not Found` | — | Grup veya üyelik bulunamadı |
| `409 Conflict` | — | Bakiye sıfır değil |
