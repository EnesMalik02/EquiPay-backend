# Group Management API
---

## 1. Grubu Sil

```
DELETE /groups/{group_id}
```

**Kurallar**
- Yalnızca `role = admin` olan üye yapabilir.
- Gruptaki **tüm bakiyeler sıfır** olmalıdır.
- Soft-delete'dir: `groups.deleted_at` doldurulur; `expenses`, `settlements`, `group_members` **olduğu gibi kalır**.

**Request**

| Parametre | Yer | Tür |
|-----------|-----|-----|
| `group_id` | path | UUID |

Body yok.

**Response**

| Durum | Açıklama |
|-------|----------|
| `204 No Content` | Grup silindi |
| `403 Forbidden` | Kullanıcı admin değil |
| `404 Not Found` | Grup bulunamadı |
| `409 Conflict` | Grupta açık borç var |

---

## 2. Gruptan Çık

```
POST /groups/{group_id}/leave
```

**Kurallar**
- Kullanıcının açık borcu/alacağı sıfır olmalı.
- **Admin** ise:
  - Başka aktif üye varsa → `409` döner, önce `PATCH .../members/{user_id}/role` ile yeni admin atanmalıdır.
  - Son üye ise → grup otomatik soft-delete edilir.
- Normal üye → `group_members.left_at` doldurulur.

**Request**

| Parametre | Yer | Tür |
|-----------|-----|-----|
| `group_id` | path | UUID |

Body yok.

**Response**

| Durum | Body | Açıklama |
|-------|------|----------|
| `200 OK` | `{"detail": "Gruptan başarıyla çıkıldı."}` | Normal çıkış |
| `200 OK` | `{"detail": "Son üyesiniz; grup silindi."}` | Son admin → grup silindi |
| `404 Not Found` | — | Grup veya üyelik bulunamadı |
| `409 Conflict` | — | Açık borç var **veya** önce admin ataması gerekiyor |

---

## 3. Üye Rolü Güncelle (Admin Atama)

```
PATCH /groups/{group_id}/members/{user_id}/role
```

**Kurallar**
- Yalnızca mevcut `admin` yapabilir.
- Gruptan çıkmadan önce başka birine admin atamak için kullanılır.

**Request Body**

```json
{ "role": "admin" }
```

| Alan | Tür | Değerler |
|------|-----|----------|
| `role` | string | `"admin"` veya `"member"` |

**Response**

| Durum | Açıklama |
|-------|----------|
| `200 OK` | `GroupMemberResponse` — güncellenmiş üye |
| `403 Forbidden` | İstek yapan admin değil |
| `404 Not Found` | Grup veya üye bulunamadı |

---

## Tablo Durumları Özeti

| İşlem | `groups` | `group_members` | `expenses` | `settlements` |
|-------|----------|-----------------|------------|---------------|
| Grubu Sil | `deleted_at` dolar | değişmez | değişmez | değişmez |
| Gruptan Çık | değişmez | `left_at` dolar | değişmez | değişmez |
| Son admin çıkar | `deleted_at` dolar | `left_at` dolar | değişmez | değişmez |

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
