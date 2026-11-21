"""Read-only import of one X List into MEGA FAV; no automated engagement actions.

Requires X_BEARER_TOKEN on the Render service. Nothing is imported without X API access.
"""
import json
import os
import sqlite3
import threading
import time
from datetime import datetime, date, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

TR = ZoneInfo('Europe/Istanbul')
LIST_ID = os.environ.get('X_LIST_ID', '2053247091497963678').strip()
POLL_MINUTES = max(15, min(240, int(os.environ.get('X_SYNC_MINUTES', '60'))))
_SYNC_MUTEX = threading.Lock()


def _connect(db_path):
    con = sqlite3.connect(db_path, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA busy_timeout=15000')
    return con


def init_x_tables(db_path):
    with _connect(db_path) as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS x_list_posts (
          post_id TEXT PRIMARY KEY,
          url TEXT NOT NULL,
          x_handle TEXT NOT NULL,
          period TEXT NOT NULL CHECK (period IN ('M1','M2','M3','M4')),
          posted_at TEXT NOT NULL,
          like_count INTEGER,
          imported_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_x_posts_date ON x_list_posts(posted_at DESC);
        CREATE TABLE IF NOT EXISTS x_sync_state (
          id INTEGER PRIMARY KEY CHECK(id=1),
          last_check TEXT,
          last_success TEXT,
          last_error TEXT,
          last_imported INTEGER NOT NULL DEFAULT 0
        );
        INSERT OR IGNORE INTO x_sync_state(id) VALUES (1);
        """)
        # Existing deployments need this additive migration for manually selected daily tasks.
        columns = {row['name'] for row in con.execute('PRAGMA table_info(x_list_posts)')}
        if 'task_day' not in columns:
            con.execute('ALTER TABLE x_list_posts ADD COLUMN task_day TEXT')
        con.execute('CREATE INDEX IF NOT EXISTS idx_x_posts_task_day ON x_list_posts(task_day,period)')


def period_for_timestamp(posted):
    dt = datetime.fromisoformat(posted.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('timestamp needs timezone')
    now = dt.astimezone(TR)
    minutes = now.hour * 60 + now.minute
    if minutes < 12 * 60:
        return 'M1'
    if minutes < 17 * 60:
        return 'M2'
    if minutes < 22 * 60:
        return 'M3'
    if minutes < 23 * 60 + 30:
        return 'M4'
    return None  # No posting window between 23:30 and midnight.


def active_task(now=None):
    """Show links only within their matching posting period, Istanbul local time."""
    local = (now or datetime.now(TR)).astimezone(TR)
    minute = local.hour * 60 + local.minute
    if minute < 12 * 60:
        return 'M1', local.date()
    if minute < 17 * 60:
        return 'M2', local.date()
    if minute < 22 * 60:
        return 'M3', local.date()
    if minute < 23 * 60 + 30:
        return 'M4', local.date()
    return None, local.date()


def _date_bounds(local_date):
    start = datetime.combine(local_date, datetime.min.time(), tzinfo=TR).astimezone(timezone.utc)
    end = datetime.combine(local_date + timedelta(days=1), datetime.min.time(), tzinfo=TR).astimezone(timezone.utc)
    return start.isoformat(), end.isoformat()


def _fetch_pages(token):
    if not LIST_ID.isdecimal():
        raise ValueError('X_LIST_ID geçerli bir liste numarası değil.')
    results, next_token = [], None
    # Limit pagination to avoid runaway API use or oversized imports.
    for _ in range(3):
        params = {'max_results': '100', 'tweet.fields': 'created_at,author_id,public_metrics',
                  'expansions': 'author_id', 'user.fields': 'username'}
        if next_token:
            params['pagination_token'] = next_token
        endpoint = 'https://api.x.com/2/lists/' + LIST_ID + '/tweets?' + urlencode(params)
        request = Request(endpoint, headers={'Authorization': 'Bearer ' + token,
                                            'Accept': 'application/json', 'User-Agent': 'MegaFavReadOnly/1.0'})
        try:
            with urlopen(request, timeout=20) as response:
                payload = json.load(response)
        except HTTPError as exc:
            raise RuntimeError(f'X API HTTP {exc.code}; liste erişimi ve API kotasını kontrol edin.') from None
        except (URLError, TimeoutError) as exc:
            raise RuntimeError('X API erişilemiyor; bağlantı zaman aşımı.') from None
        users = {str(x.get('id')): x.get('username') for x in payload.get('includes', {}).get('users', [])}
        for item in payload.get('data') or []:
            handle = users.get(str(item.get('author_id')))
            if handle and item.get('created_at') and str(item.get('id', '')).isdigit():
                results.append((item, handle))
        next_token = (payload.get('meta') or {}).get('next_token')
        if not next_token:
            break
    return results


def sync_once(db_path):
    token = os.environ.get('X_BEARER_TOKEN', '').strip()
    if not token:
        return {'ok': False, 'reason': 'X API bağlantısı henüz kurulmadı.'}
    if not _SYNC_MUTEX.acquire(blocking=False):
        return {'ok': False, 'reason': 'Başka bir senkronizasyon sürüyor.'}
    checked_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
    try:
        try:
            incoming = _fetch_pages(token)
            with _connect(db_path) as con:
                count = 0
                for item, handle in incoming:
                    period = period_for_timestamp(item['created_at'])
                    if not period:
                        continue
                    post_id = str(item['id'])
                    when = datetime.fromisoformat(item['created_at'].replace('Z', '+00:00')).astimezone(timezone.utc).isoformat(timespec='seconds')
                    likes = (item.get('public_metrics') or {}).get('like_count')
                    if not isinstance(likes, int) or likes < 0:
                        likes = None
                    url = 'https://x.com/' + handle + '/status/' + post_id
                    result = con.execute("""INSERT OR IGNORE INTO x_list_posts
                      (post_id,url,x_handle,period,posted_at,like_count,imported_at)
                      VALUES (?,?,?,?,?,?,?)""", (post_id, url, handle, period, when, likes, checked_at))
                    count += result.rowcount
                    con.execute('UPDATE x_list_posts SET like_count=? WHERE post_id=?', (likes, post_id))
                con.execute("""UPDATE x_sync_state SET last_check=?,last_success=?,last_error=NULL,last_imported=? WHERE id=1""",
                            (checked_at, checked_at, count))
            return {'ok': True, 'imported': count}
        except (RuntimeError, ValueError, OSError, sqlite3.Error) as exc:
            with _connect(db_path) as con:
                con.execute('UPDATE x_sync_state SET last_check=?,last_error=? WHERE id=1',
                            (checked_at, str(exc)[:180]))
            return {'ok': False, 'reason': str(exc)}
    finally:
        _SYNC_MUTEX.release()


def start_x_poller(db_path):
    if not os.environ.get('X_BEARER_TOKEN', '').strip():
        return
    def worker():
        time.sleep(3)
        while True:
            status = sync_once(db_path)
            if status.get('ok'):
                print('MEGA_X_SYNC_OK imported=' + str(status.get('imported', 0)), flush=True)
            else:
                print('MEGA_X_SYNC_FAILED reason=' + str(status.get('reason', 'Bilinmeyen hata'))[:180], flush=True)
            time.sleep(POLL_MINUTES * 60)
    threading.Thread(target=worker, name='x-list-read-only-sync', daemon=True).start()


def _state(db_path):
    with _connect(db_path) as con:
        state = con.execute('SELECT * FROM x_sync_state WHERE id=1').fetchone()
    return {'enabled': bool(os.environ.get('X_BEARER_TOKEN', '').strip()),
            'last_success': state['last_success'] if state else None,
            'last_error': state['last_error'] if state else None,
            'last_imported': state['last_imported'] if state else 0,
            'interval': POLL_MINUTES}


def list_feed_context(db_path, period='', q='', page=1, max_per_page=50, day=''):
    task_period, today = active_task()
    selected_day = today
    if day:
        try:
            requested = date.fromisoformat(day)
            if today - timedelta(days=180) <= requested <= today:
                selected_day = requested
        except ValueError:
            pass
    start, end = _date_bounds(selected_day)
    clauses = ['(task_day = ? OR (task_day IS NULL AND posted_at >= ? AND posted_at < ?))']
    args = [selected_day.isoformat(), start, end]
    if period:
        clauses.append('period=?')
        args.append(period)
    if q:
        clauses.append('x_handle LIKE ?')
        args.append('%' + q.replace('%', '').replace('_', '') + '%')
    where = ' AND '.join(clauses)
    with _connect(db_path) as con:
        total = con.execute('SELECT COUNT(*) FROM x_list_posts WHERE ' + where, args).fetchone()[0]
        posts = con.execute("""SELECT post_id,url,x_handle,period,posted_at,like_count
                              FROM x_list_posts WHERE """ + where + """
                              ORDER BY posted_at ASC, post_id ASC LIMIT ? OFFSET ?""",
                            args + [max_per_page, (page - 1) * max_per_page]).fetchall()
    return {'x_posts': posts, 'x_total': total, 'x_has_next': page * max_per_page < total,
            'task_period': task_period, 'x_sync': _state(db_path),
            'x_selected_day': selected_day.isoformat(), 'x_today': today.isoformat()}


def dashboard_stats(db_path, active_members):
    today = datetime.now(TR).date()
    start, end = _date_bounds(today)
    with _connect(db_path) as con:
        result = con.execute("""SELECT COUNT(*) AS n, AVG(like_count) AS avg_likes,
                                      SUM(CASE WHEN like_count IS NOT NULL THEN 1 ELSE 0 END) AS metric_count
                                FROM x_list_posts WHERE task_day = ? OR (task_day IS NULL AND posted_at >= ? AND posted_at < ?)""", (today.isoformat(),start,end)).fetchone()
    count = result['n'] or 0
    with _connect(db_path) as con:
        recent_rows = con.execute('''SELECT post_id,url,x_handle,period,posted_at,imported_at,task_day
                                     FROM x_list_posts ORDER BY imported_at DESC,post_id DESC LIMIT 15''').fetchall()
        recent = [dict(row, local_day=(row['task_day'] or datetime.fromisoformat(row['posted_at'].replace('Z', '+00:00')).astimezone(TR).date().isoformat())) for row in recent_rows]
        saved_total = con.execute('SELECT COUNT(*) FROM x_list_posts').fetchone()[0]
    return {'x_today_count': count, 'x_saved_total': saved_total, 'x_recent_posts': recent,
            'x_posts_per_member': round(count / active_members, 2) if active_members else 0,
            'x_avg_likes': round(result['avg_likes'], 1) if result['metric_count'] else None,
            'x_sync': _state(db_path)}
