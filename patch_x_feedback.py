"""Make successful X link imports visible, including links posted on past days."""
from pathlib import Path
root=Path(__file__).resolve().parent
app=root/'app.py'
s=app.read_text(encoding='utf-8')
a="def feed(request: Request, period: str = '', q: str = '', page: int = 1):"
b="auto_x = list_feed_context(DB_PATH, period=period, q=q, page=page, max_per_page=MAX_LINKS_PER_PAGE)"
assert s.count(a)==1 and s.count(b)==1, 'Archive route anchor missing'
s=s.replace(a, "def feed(request: Request, period: str = '', q: str = '', page: int = 1, day: str = ''):")
s=s.replace(b, b[:-1]+", day=day)")
app.write_text(s,encoding='utf-8')

p=root/'templates'/'dashboard.html'
s=p.read_text(encoding='utf-8')
assert s.count('<h2>Bağlantıları yapıştır, saatleri otomatik ayır</h2>')==1
s=s.replace('<h2>Bağlantıları yapıştır, saatleri otomatik ayır</h2>', """<h2>Bağlantıları yapıştır, saatleri otomatik ayır</h2>
  {% if request.query_params.get('freeimport') is not none %}
  <div id="x-import-results" role="status">
    <p><strong>{{request.query_params.get('freeimport')}} yeni gönderi kaydedildi.</strong>
    {{request.query_params.get('duplicates', '0')}} zaten kayıtlı,
    {{request.query_params.get('excluded', '0')}} görev saati dışında,
    {{request.query_params.get('invalid', '0')}} geçersiz bağlantı.</p>
    {% if request.query_params.get('freeimport') == '0' %}
    <p><strong>Yeni gönderi görünmüyorsa:</strong> X liste adresi değil, tek bir gönderinin Paylaş → Bağlantıyı kopyala seçeneğini kullan. Eski tarihli kayıtlar da aşağıdaki listede görünür.</p>
    {% else %}<p>Eklenen bağlantıları aşağıdaki <strong>Son kaydedilenler</strong> bölümünde görebilirsin.</p>{% endif %}
  </div>
  {% endif %}""")
s=s.replace('Ücretsiz: X listesini açıp gönderi bağlantılarını kopyala.', 'Ücretsiz: X listesini değil, X listesindeki tekil gönderilerin Paylaş → Bağlantıyı kopyala seçeneğiyle bağlantılarını al.')
old_result="""  {% if request.query_params.get('freeimport') is not none %}
    <p><strong>{{request.query_params.get('freeimport')}} yeni bağlantı eklendi.</strong>
    Mevcut: {{request.query_params.get('duplicates', '0')}}, görev dışı: {{request.query_params.get('excluded', '0')}}, geçersiz: {{request.query_params.get('invalid', '0')}}.</p>
  {% endif %}"""
assert s.count(old_result)==1
s=s.replace(old_result,'')
anchor="""  <p class="subtle">M1: 00.00–12.00 · M2: 12.00–17.00 · M3: 17.00–22.00 · M4: 22.00–23.30 (Türkiye saati)</p>"""
assert s.count(anchor)==1
s=s.replace(anchor, anchor+"""
  <section id="x-recent-posts" style="margin-top:20px">
    <h3>Son kaydedilen X gönderileri (toplam {{x_saved_total}})</h3>
    {% if x_recent_posts %}<div class="post-list">
      {% for post in x_recent_posts %}
        <article class="post"><div class="post-main"><strong>@{{post.x_handle}} · {{post.period}}</strong>
          <div class="post-meta">{{format_dt(post.posted_at)}} · Paylaşım tarihi: {{post.local_day}}</div>
          <div class="post-url">{{post.url}}</div></div>
          <a class="button outline" href="/?day={{post.local_day}}&period={{post.period}}">Akışta göster ↗</a>
        </article>
      {% endfor %}</div>
    {% else %}<p class="subtle">Kayıtlı X gönderisi yok. Tekil bir gönderi bağlantısını eklemeyi dene.</p>{% endif %}
  </section>""")
s=s.replace('Bugün panele eklenen liste gönderileri: {{x_today_count}}', 'Bugün yayımlanmış kayıtlı X gönderileri: {{x_today_count}}')
s=s.replace('{{visible_posts}}', '{{visible_posts + x_saved_total}}')
p.write_text(s,encoding='utf-8')

p=root/'templates'/'feed.html'
s=p.read_text(encoding='utf-8')
assert s.count('{% if task_period == post.period %}')==2
s=s.replace('{% if task_period == post.period %}', '{% if task_period == post.period and x_selected_day == x_today %}')
old="<p><strong>Şu an açık görev:</strong> {{task_period or 'Görev saatleri dışında'}} · <strong>Gösterilen gün:</strong> {{x_selected_day}}</p>"
assert s.count(old)==1
s=s.replace(old, old+"""
  {% if x_selected_day != x_today %}<p class="subtle">Geçmiş gün arşivi görüntüleniyor. Gönderiler kayıtlıdır; görev bağlantısı yalnızca ait olduğu gün ve saatte açılır.</p>{% endif %}""")
s=s.replace('href="/?period={{period}}&q=', 'href="/?day={{x_selected_day}}&period={{period}}&q=')
p.write_text(s,encoding='utf-8')
print('Import results and historical X links visible on dashboard and archive')
