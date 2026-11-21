"""Patch the bundled FastAPI application for optional zero-cost bulk X link import."""
from pathlib import Path

root = Path(__file__).resolve().parent
app = root / 'app.py'
s = app.read_text(encoding='utf-8')
anchor = "@app.post('/admin/x-sync')"
assert s.count(anchor) == 1
replacement = """@app.post('/admin/x-free-import')
def import_x_without_api(request: Request, csrf: str = Form(...), urls: str = Form(...)):
    guard(request, csrf, ('owner',))
    from x_free_import import import_free_urls
    try:
        result = import_free_urls(DB_PATH, urls)
    except (ValueError, OverflowError, sqlite3.Error) as ex:
        return short_error(request, str(ex), '/panel')
    return redirect('/panel?freeimport=' + str(result['inserted']) +
                    '&duplicates=' + str(result['duplicates']) +
                    '&excluded=' + str(result['excluded']) +
                    '&invalid=' + str(result['invalid']))


""" + anchor
s = s.replace(anchor, replacement)
app.write_text(s, encoding='utf-8')

p = root / 'templates' / 'dashboard.html'
s = p.read_text(encoding='utf-8')
anchor = '<section class="surface admin-card" style="margin-top:20px">\n  <span class="eyebrow">X LİSTESİ · GÜNLÜK ÖZET</span>'
assert s.count(anchor) == 1
html = """{% if user.role == 'owner' %}
<section class="surface admin-card" style="margin-top:20px">
  <span class="eyebrow">ÜCRETSİZ YÖNTEM · X GÖNDERİLERİNİ TOPLU EKLE</span>
  <h2>Bağlantıları yapıştır, saatleri otomatik ayır</h2>
  <p class="subtle">Ücretsiz: X listesini açıp gönderi bağlantılarını kopyala. Her satıra bir bağlantı yapıştır (en çok 200). Paylaşım saatini X gönderi kimliğinden hesaplayıp M1–M4'e otomatik ayırırız. X listesini kendiliğinden taramaz; beğeni sayılarını ölçmez.</p>
  <form method="post" action="/admin/x-free-import">
    <input type="hidden" name="csrf" value="{{csrf}}">
    <label for="x-free-urls">X gönderi bağlantıları</label>
    <textarea id="x-free-urls" name="urls" rows="6" maxlength="30000" required placeholder="https://x.com/kullanici/status/1234567890123456789"></textarea>
    <button class="button primary" type="submit" style="margin-top:12px">Bağlantıları ücretsiz ekle</button>
  </form>
  {% if request.query_params.get('freeimport') is not none %}
    <p><strong>{{request.query_params.get('freeimport')}} yeni bağlantı eklendi.</strong>
    Mevcut: {{request.query_params.get('duplicates', '0')}}, görev dışı: {{request.query_params.get('excluded', '0')}}, geçersiz: {{request.query_params.get('invalid', '0')}}.</p>
  {% endif %}
  <p class="subtle">M1: 00.00–12.00 · M2: 12.00–17.00 · M3: 17.00–22.00 · M4: 22.00–23.30 (Türkiye saati)</p>
</section>
{% endif %}
"""
s = s.replace(anchor, html + anchor)
s = s.replace('Bugünkü otomatik gönderiler: {{x_today_count}}', 'Bugün panele eklenen liste gönderileri: {{x_today_count}}')
s = s.replace('Otomatik aktarım henüz etkin değil. Render Environment bölümüne X_BEARER_TOKEN eklenmeli.',
              'Ücretsiz toplu bağlantı ekleme açık. API üzerinden otomatik tarama kapalı.')
s = s.replace("{% if user.role == 'owner' %}<form method=\"post\" action=\"/admin/x-sync\">",
              "{% if user.role == 'owner' and x_sync.enabled %}<form method=\"post\" action=\"/admin/x-sync\">")
s = s.replace('Günlük gönderi başına ortalama X beğenisi (FAV)', 'X genel FAV ortalaması (API verisi varsa)')
p.write_text(s, encoding='utf-8')

p = root / 'templates' / 'feed.html'
s = p.read_text(encoding='utf-8')
s = s.replace('X LİSTESİ · OTOMATİK BAĞLANTILAR', 'X LİSTESİ · KAYDEDİLEN BAĞLANTILAR')
s = s.replace('Liste gönderileri saatine göre otomatik sınıflanır.', 'Panele eklenen liste bağlantıları paylaşım saatine göre otomatik sınıflanır.')
s = s.replace('Otomatik aktarım beklemede:</strong> Render ortamına X_BEARER_TOKEN eklenmedi. Liste bağlantısını yukarıdan açabilirsin; otomatik gönderi sayısı şu an sıfır olabilir.',
              'Ücretsiz bağlantı aktarımı açık.</strong> Yönetici tarafından eklenen gerçek gönderiler gösterilir; X listesinden kendiliğinden çekme kapalı.')
s = s.replace('Gösterilen otomatik bağlantı: {{x_total}}', 'Gösterilen liste bağlantısı: {{x_total}}')
s = s.replace('Bugüne ait aktarılmış X gönderisi bulunmuyor. API bağlantısı yoksa bu alan boş kalır; gönderi uydurulmaz.',
              'Bugün için toplu eklenmiş liste bağlantısı bulunmuyor. Kurucu, X gönderilerinin bağlantılarını ücretsiz ekleyebilir.')
p.write_text(s, encoding='utf-8')
print('Free X bulk link import integrated without X API calls')
