"""Import X post links without the paid X API.

Managers choose a task period for a batch; importing a link never fetches
content from X and never performs likes, follows, or reposts.
"""
import re
import sqlite3
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit
from x_list_sync import _connect, period_for_timestamp, TR

URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)
POST_RE = re.compile(
    r'^/(?:(?P<handle>[A-Za-z0-9_]{1,15})/status|i/web/status)/(?P<post_id>\d{15,20})/?(?:photo/\d+|video/\d+)?/?$',
    re.I,
)
X_EPOCH_MS = 1288834974657
PERIODS = {'M1', 'M2', 'M3', 'M4'}


def _from_url(raw):
    url = urlsplit(raw.strip().rstrip('.,;)]'))
    if (url.scheme not in ('https', 'http') or
            (url.hostname or '').lower() not in (
                'x.com', 'www.x.com', 'mobile.x.com',
                'twitter.com', 'www.twitter.com', 'mobile.twitter.com')):
        return None
    match = POST_RE.fullmatch(url.path)
    if not match:
        return None
    handle = match.group('handle') or 'i'
    post_id = match.group('post_id')
    try:
        posted_ms = (int(post_id) >> 22) + X_EPOCH_MS
        posted = datetime.fromtimestamp(posted_ms / 1000, tz=timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None
    if (posted < datetime(2010, 11, 4, tzinfo=timezone.utc) or
            posted > datetime.now(timezone.utc) + timedelta(minutes=5)):
        return None
    return post_id, handle, posted, 'https://x.com/' + handle + '/status/' + post_id


def import_free_urls(db_path, supplied, period=''):
    selected = (period or '').strip().upper()
    if selected and selected not in PERIODS:
        raise ValueError('Görev seçimi geçersiz. M1, M2, M3 veya M4 seç.')
    matches = URL_RE.findall(supplied or '')
    if not matches:
        raise ValueError('X gönderi bağlantısı bulunamadı. Tek tek gönderilerin Paylaş → Bağlantıyı kopyala seçeneğini kullan.')
    if any('/i/lists/' in item.lower() for item in matches):
        raise ValueError('X liste bağlantısı gönderileri tek tek içermez. Listedeki gönderilerin bağlantılarını kopyalayıp eklemelisin.')
    if len(matches) > 200 or len(supplied or '') > 30000:
        raise ValueError('Bir seferde en fazla 200 gönderi bağlantısı eklenebilir.')

    checked = set()
    inserted = duplicates = excluded = invalid = 0
    now_iso = datetime.now(timezone.utc).isoformat(timespec='seconds')
    chosen_day = datetime.now(TR).date().isoformat() if selected else None
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
            assigned_period = selected or period_for_timestamp(posted.isoformat())
            if assigned_period is None:
                excluded += 1
                continue
            result = db.execute(
                """INSERT OR IGNORE INTO x_list_posts
                   (post_id,url,x_handle,period,posted_at,like_count,imported_at,task_day)
                   VALUES (?,?,?,?,?,NULL,?,?)""",
                (post_id, canonical, handle, assigned_period,
                 posted.isoformat(timespec='seconds'), now_iso, chosen_day))
            if result.rowcount:
                inserted += 1
            else:
                duplicates += 1
                # Explicit selection lets a manager correct the task period.
                if selected:
                    db.execute('UPDATE x_list_posts SET period=?, task_day=? WHERE post_id=?',
                               (selected, chosen_day, post_id))
    if inserted == 0 and duplicates == 0 and excluded == 0 and invalid:
        raise ValueError('Hiçbir gönderi eklenmedi. X gönderisinin status/... bağlantısını kopyala; liste ve profil adresleri kabul edilmez.')
    return {'inserted': inserted, 'duplicates': duplicates,
            'excluded': excluded, 'invalid': invalid}
