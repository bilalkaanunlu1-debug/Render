"""Deploy smoke tests for the free X link importer; no X calls are made."""
from datetime import datetime, timedelta, timezone
import tempfile
from pathlib import Path
from x_free_import import import_free_urls, _from_url, X_EPOCH_MS
from x_list_sync import init_x_tables, list_feed_context, TR

posted = datetime.now(timezone.utc) - timedelta(minutes=10)
identifier = str(((int(posted.timestamp() * 1000) - X_EPOCH_MS) << 22) + 5)
link = 'https://x.com/example/status/' + identifier
assert _from_url(link) is not None
assert _from_url(link + '?s=20') is not None
assert _from_url('https://x.com/i/lists/2053247091497963678') is None

with tempfile.TemporaryDirectory() as directory:
    db = str(Path(directory) / 'demo.sqlite')
    init_x_tables(db)
    saved = import_free_urls(db, link, 'M1')
    assert saved['inserted'] == 1, saved
    posts = list_feed_context(db, period='M1')['x_posts']
    assert len(posts) == 1 and posts[0]['period'] == 'M1'
    updated = import_free_urls(db, link, 'M3')
    assert updated['duplicates'] == 1
    posts = list_feed_context(db, period='M3')['x_posts']
    assert len(posts) == 1 and posts[0]['period'] == 'M3'
print('X manager import smoke tests OK')
