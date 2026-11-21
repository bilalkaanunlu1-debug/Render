"""Enable manager-controlled, no-cost X post link batches and task tabs."""

from pathlib import Path

root = Path(__file__).resolve().parent
app = root / 'app.py'
s = app.read_text(encoding='utf-8')
old = """def import_x_without_api(request: Request, csrf: str = Form(...), urls: str = Form(...)):
    guard(request, csrf, ('owner',))"""
new = """def import_x_without_api(request: Request, csrf: str = Form(...), urls: str = Form(...), period: str = Form(...)):
    guard(request, csrf, ('owner', 'editor'))"""
assert s.count(old) == 1, 'X importer route signature not found'
s = s.replace(old, new)
old = "result = import_free_urls(DB_PATH, urls)"
assert s.count(old) == 1
s = s.replace(old, "result = import_free_urls(DB_PATH, urls, period)")
app.write_text(s, encoding='utf-8')

dash = root / 'templates' / 'dashboard.html'
s = dash.read_text(encoding='utf-8')
old = """{% if user.role == 'owner' %}
<section class="surface admin-card" style="margin-top:20px">
  <span class="eyebrow">ÜCRETSİZ YÖNTEM · X GÖNDERİLERİNİ TOPLU EKLE</span>"""
new = old.replace("user.role == 'owner'", "user.role in ('owner', 'editor')")
assert s.count(old) == 1, 'Manager import UI anchor missing'
s = s.replace(old, new)
old = '<h2>Bağlantıları yapıştır, saatleri otomatik ayır</h2>'
assert s.count(old) == 1
s = s.replace(old, '<h2>Görev dilimini seç, bağlantıları ekle</h2>')
old = '<label for="x-free-urls">X gönderi bağlantıları</label>'
new = """<label for="x-free-period">Bağlantıların gösterileceği görev</label>
    <select id="x-free-period" name="period" required>
      <option value="" selected disabled>Bir görev seç</option>
      <option value="M1">M1 · 00:00–12:00</option>
      <option value="M2">M2 · 12:00–17:00</option>
      <option value="M3">M3 · 17:00–22:00</option>
      <option value="M4">M4 · 22:00–23:30</option>
    </select>
    <p class="subtle">Seçtiğin göreve eklenen gönderiler bugünün üyeler listesinde sıralı görünür. X liste adresi değil, listedeki tekil gönderilerin bağlantıları eklenir.</p>
    <label for="x-free-urls">Gönderi bağlantıları (her satıra bir tane)</label>"""
assert s.count(old) == 1, 'Manager selector anchor missing'
s = s.replace(old, new)
s = s.replace('Paylaşım saatini X gönderi kimliğinden hesaplayıp M1–M4’e otomatik ayırırız.',
              'M1–M4 seçimini sen yaparsın; bağlantılar bu görev altında listelenir.')
dash.write_text(s, encoding='utf-8')

feed = root / 'templates' / 'feed.html'
s = feed.read_text(encoding='utf-8')
old = '<h2>M1–M4 görev bağlantıları</h2>'
new = """<h2>M1–M4 görev bağlantıları</h2>
  <nav aria-label="X gönderi görevleri" style="display:flex;gap:8px;flex-wrap:wrap;margin:12px 0">
    {% for p in ['M1', 'M2', 'M3', 'M4'] %}
    <a class="button {% if period == p %}primary{% else %}outline{% endif %}" href="/?period={{p}}&day={{x_selected_day}}">{{p}}</a>
    {% endfor %}
    <a class="button outline" href="/?day={{x_selected_day}}">Tümü</a>
  </nav>"""
assert s.count(old) == 1, 'X feed header not found'
s = s.replace(old, new)
feed.write_text(s, encoding='utf-8')
print('Manager-selected X batches and member M1-M4 tabs integrated')
