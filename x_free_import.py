"""No-API bulk entry of X posts; X snowflake ids encode their UTC creation time.

Only processes URLs deliberately pasted by an authenticated founder. It does not
scrape X, claim list membership, or measure FAVs.
"""
import re
import sqlite3
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit
from x_list_sync import _connect, period_for_timestamp

URL_RE = re.compile(r'https?://[^\s<>"\']+', re.I)
POST_RE = re.compile(r'^/([A-Za-z0-9_]{1,15})/status/(\d{15,20})/?
X_EPOCH_MS = 1288834974657


def _from_url(raw):
    url = urlsplit(raw.strip().rstrip('.,;)]'))
    if url.scheme not in ('https', 'http') or (url.hostname or '').lower() not in ('x.com', 'www.x.com', 'mobile.x.com', 'twitter.com', 'www.twitter.com', 'mobile.twitter.com'):
        return None
    match = POST_RE.fullmatch(url.path)
    if not match:
        return None
    handle, post_id = match.group(1), match.group(2)
    posted_ms = (int(post_id) >> 22) + X_EPOCH_MS
    posted = datetime.fromtimestamp(posted_ms / 1000, tz=timezone.utc)
    if posted < datetime(2010, 11, 4, tzinfo=timezone.utc) or posted > datetime.now(timezone.utc) + timedelta(minutes=5):
        return None
    return post_id, handle, posted, 'https://x.com/' + handle + '/status/' + post_id


def import_free_urls(db_path, supplied):
    matches = URL_RE.findall(supplied or '')
    if not matches:
        raise ValueError('X gönderi bağlantısı bulunamadı. X listesini açıp her gönderinin Paylaş → Bağlantıyı kopyala seçeneğini kullan.')
    if any('/i/lists/' in item.lower() for item in matches):
        raise ValueError('Bu bir X liste bağlantısı. Liste adresi tek başına gönderileri içermez; listedeki her gönderinin bağlantısını ayrı ayrı kopyala.')
    if len(matches) > 200 or len(supplied) > 30000:
        raise ValueError('Tek seferde en fazla 200 gönderi bağlantısı eklenebilir.')
    checked = set()
    inserted = duplicates = excluded = invalid = 0
    now_iso = datetime.now(timezone.utc).isoformat(timespec='seconds')
    with _connect(db_path) as db:
        for raw in matches:
            parsed = _from_url(raw)
            if not parsed:
                invalid += 1
                continue
            post_id, handle, posted, canonical = parsed
            if post_id in checked:
                duplicates += 1
                continue
            checked.add(post_id)
            period = period_for_timestamp(posted.isoformat())
            if period is None:
                excluded += 1
                continue
            result = db.execute("""INSERT OR IGNORE INTO x_list_posts
                    (post_id,url,x_handle,period,posted_at,like_count,imported_at)
                    VALUES (?,?,?,?,?,NULL,?)""",
                    (post_id, canonical, handle, period, posted.isoformat(timespec='seconds'), now_iso))
            if result.rowcount:
                inserted += 1
            else:
                duplicates += 1
    if inserted == 0 and duplicates == 0 and excluded == 0 and invalid:
        raise ValueError('Hiçbir gönderi eklenmedi: bağlantı bir X gönderisine ait olmalı (örnek: https://x.com/kullanici/status/1234567890123456789). Liste/profil bağlantıları kabul edilmez.')
    return {'inserted': inserted, 'duplicates': duplicates, 'excluded': excluded, 'invalid': invalid}
, re.I)
X_EPOCH_MS = 1288834974657


def _from_url(raw):
    url = urlsplit(raw.strip().rstrip('.,;)]'))
    if url.scheme != 'https' or url.hostname not in ('x.com', 'www.x.com', 'twitter.com', 'www.twitter.com', 'mobile.twitter.com'):
        return None
    match = POST_RE.fullmatch(url.path)
    if not match:
        return None
    handle, post_id = match.group(1), match.group(2)
    posted_ms = (int(post_id) >> 22) + X_EPOCH_MS
    posted = datetime.fromtimestamp(posted_ms / 1000, tz=timezone.utc)
    if posted < datetime(2010, 11, 4, tzinfo=timezone.utc) or posted > datetime.now(timezone.utc) + timedelta(minutes=5):
        return None
    return post_id, handle, posted, 'https://x.com/' + handle + '/status/' + post_id


def import_free_urls(db_path, supplied):
    matches = URL_RE.findall(supplied or '')
    if not matches:
        raise ValueError('En az bir X gönderi bağlantısı yapıştır.')
    if len(matches) > 200 or len(supplied) > 30000:
        raise ValueError('Tek seferde en fazla 200 gönderi bağlantısı eklenebilir.')
    checked = set()
    inserted = duplicates = excluded = invalid = 0
    now_iso = datetime.now(timezone.utc).isoformat(timespec='seconds')
    with _connect(db_path) as db:
        for raw in matches:
            parsed = _from_url(raw)
            if not parsed:
                invalid += 1
                continue
            post_id, handle, posted, canonical = parsed
            if post_id in checked:
                duplicates += 1
                continue
            checked.add(post_id)
            period = period_for_timestamp(posted.isoformat())
            if period is None:
                excluded += 1
                continue
            result = db.execute("""INSERT OR IGNORE INTO x_list_posts
                    (post_id,url,x_handle,period,posted_at,like_count,imported_at)
                    VALUES (?,?,?,?,?,NULL,?)""",
                    (post_id, canonical, handle, period, posted.isoformat(timespec='seconds'), now_iso))
            if result.rowcount:
                inserted += 1
            else:
                duplicates += 1
    return {'inserted': inserted, 'duplicates': duplicates, 'excluded': excluded, 'invalid': invalid}
