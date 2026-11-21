"""Repair MEGA FAV founder login without embedding passwords in GitHub."""
from pathlib import Path
p = Path(__file__).resolve().parent / 'app.py'
s = p.read_text(encoding='utf-8')
needle = "USERNAME_RE = re.compile(r'^[A-Za-z0-9_]{3,32}$')"
assert s.count(needle) == 1, 'Unexpected username validation source'
s = s.replace(needle, needle + "\nOWNER_USERNAME_RE = re.compile(r'^[A-Za-z0-9_](?:[A-Za-z0-9_ ]{1,30})[A-Za-z0-9_]$')")
needle = 'len(initial_password) < 12 or not USERNAME_RE.fullmatch(owner_username)'
assert s.count(needle) == 1, 'Unexpected owner validation source'
s = s.replace(needle, 'len(initial_password) < 12 or not OWNER_USERNAME_RE.fullmatch(owner_username)')
needle = '        if row is None and initial_password:\n'
assert s.count(needle) == 1, 'Unexpected owner bootstrap source'
fix = '''        # Correct founder name/password exactly once; leave future profile changes intact.
        if row is not None and initial_password:
            conn.execute('CREATE TABLE IF NOT EXISTS owner_migrations (name TEXT PRIMARY KEY)')
            marker = 'founder-login-repair-20261121'
            prior = conn.execute('SELECT 1 FROM owner_migrations WHERE name=?', (marker,)).fetchone()
            if not prior:
                if len(initial_password) < 12 or not OWNER_USERNAME_RE.fullmatch(owner_username):
                    raise RuntimeError('Kurucu adı ya da şifresi geçersiz.')
                old = conn.execute("SELECT username FROM users WHERE id=?", (row['id'],)).fetchone()['username']
                conn.execute('UPDATE users SET username=?,password_hash=?,active=1 WHERE id=?',
                             (owner_username, hash_password(initial_password), row['id']))
                conn.execute('DELETE FROM login_attempts WHERE username IN (?,?)', (old, owner_username))
                conn.execute('DELETE FROM sessions WHERE user_id=?', (row['id'],))
                conn.execute('INSERT INTO owner_migrations(name) VALUES (?)', (marker,))
'''
s = s.replace(needle, fix + needle)
needle = "(owner_username, hash_password(initial_password), 'owner', now_utc()))"
assert s.count(needle) == 1, 'Unexpected owner insert source'
s = s.replace(needle, needle + "\n            conn.execute('DELETE FROM login_attempts WHERE username=?', (owner_username,))")
p.write_text(s, encoding='utf-8')
print('Owner login and one-shot migration patch applied')
