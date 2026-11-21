"""Prefill the manager-only manual import form from an iPhone Share Sheet Shortcut.

Managers can create a Shortcut that accepts a URL from the X share sheet,
URL-encodes it and opens /panel?xshare=<encoded-link>. Import still requires
an authenticated editor or owner plus an explicit M1-M4 selection and submit.
"""
from pathlib import Path

root = Path(__file__).resolve().parent
p = root / "templates" / "dashboard.html"
s = p.read_text(encoding="utf-8")
anchor = '<h2>Görev dilimini seç, bağlantıları ekle</h2>'
assert s.count(anchor) == 1, "X dashboard form not found"
s = s.replace(anchor, anchor + """
  <p class="subtle"><strong>iPhone Kestirmesi:</strong> X’te Paylaş → MEGA FAV dediğinde
    gönderinin bağlantısı bu alana otomatik gelir. Yalnızca görev seçip kaydetmen yeterli.
    Yönetici hesabıyla giriş yapmış olmalısın.</p>
  <p id="x-share-shortcut-status" role="status" aria-live="polite" hidden></p>""")

anchor = '</section>\n{% endif %}\n<section class="surface admin-card" style="margin-top:20px">\n  <span class="eyebrow">X LİSTESİ · GÜNLÜK ÖZET</span>'
# If markup context changes, keep patch strictly anchored to imported form input.
script = """
<script>
(function () {
  // Never save shared links on GET; an authorized user must pick a task and submit.
  var shared = new URLSearchParams(window.location.search).get('xshare');
  if (!shared) return;
  var field = document.getElementById('x-free-urls');
  var period = document.getElementById('x-free-period');
  var status = document.getElementById('x-share-shortcut-status');
  if (!field || !period || !status) return;  // Non-managers cannot import.
  var match = shared.match(/https?:\\/\\/(?:[a-z]+\\.)?(?:x\\.com|twitter\\.com)\\/[^\\s<>]+/i);
  if (!match) {
    status.textContent = 'Paylaşılan içerikte X gönderi bağlantısı bulunamadı.';
    status.hidden = false;
    status.scrollIntoView({block:'center', behavior:'smooth'});
    return;
  }
  field.value = match[0];
  status.textContent = 'X gönderi bağlantısı hazır. M1, M2, M3 veya M4 seçip "Bağlantıları ücretsiz ekle" düğmesine bas.';
  status.hidden = false;
  period.scrollIntoView({block:'center', behavior:'smooth'});
  period.focus();
})();
</script>
"""
needle = '<label for="x-free-urls">Gönderi bağlantıları (her satıra bir tane)</label>'
assert s.count(needle) == 1, "X manager form label missing"
# Insert script at end of form; avoid dependency on the rest of dashboard markup.
end_needle = '<button class="button primary" type="submit" style="margin-top:12px">Bağlantıları ücretsiz ekle</button>\n  </form>'
assert s.count(end_needle) == 1, "X submit form structure unexpected"
s = s.replace(end_needle, end_needle + script)
p.write_text(s, encoding="utf-8")
print("iPhone X Share Sheet prefill integrated into manager import form")
