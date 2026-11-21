"""Integrate read-only X List sync and task-time-gated links into bundled MEGA FAV sources.

This runs at Docker build time after restoring the original source bundle. No token is
contained in any repository file. It is safe to re-build without editing the bundle.
"""
from pathlib import Path

root = Path(__file__).resolve().parent
p = root / 'app.py'
s = p.read_text(encoding='utf-8')

needle = "initialize()\n\n\n@app.get('/healthz'"
assert s.count(needle) == 1, 'X patch startup anchor missing'
s = s.replace(needle, """initialize()
from x_list_sync import init_x_tables, start_x_poller, list_feed_context, dashboard_stats, sync_once, active_task
init_x_tables(DB_PATH)
start_x_poller(DB_PATH)


@app.get('/healthz'""")

needle = "    return render(request, 'feed.html', {'posts': posts"
assert s.count(needle) == 1, 'X patch feed anchor missing'
s = s.replace(needle, "    auto_x = list_feed_context(DB_PATH, period=period, q=q, page=page, max_per_page=MAX_LINKS_PER_PAGE)\n" + needle)
needle = "'q': q, 'page': page, 'has_next': page * MAX_LINKS_PER_PAGE < total})"
assert s.count(needle) == 1, 'X patch feed context missing'
s = s.replace(needle, "'q': q, 'page': page, 'has_next': page * MAX_LINKS_PER_PAGE < total, **auto_x})")

needle = "    return render(request, 'dashboard.html', {'active_members': active_members, 'active_editors': active_editors, 'visible_posts': visible_posts})"
assert s.count(needle) == 1, 'X patch dashboard anchor missing'
s = s.replace(needle, "    x_stats = dashboard_stats(DB_PATH, active_members)\n    return render(request, 'dashboard.html', {'active_members': active_members, 'active_editors': active_editors, 'visible_posts': visible_posts, **x_stats})")

needle = "@app.post('/admin/post')"
assert s.count(needle) == 1, 'X patch admin route anchor missing'
s = s.replace(needle, """@app.post('/admin/x-sync')
def manual_sync_x(request: Request, csrf: str = Form(...)):
    guard(request, csrf, ('owner',))
    status = sync_once(DB_PATH)
    if not status['ok']:
        return short_error(request, status['reason'], '/panel')
    return redirect('/panel?xsync=1')


""" + needle)
p.write_text(s, encoding='utf-8')

p = root / 'templates' / 'feed.html'
s = p.read_text(encoding='utf-8')
needle = '<div class="stats">'
assert s.count(needle) == 1, 'Feed stats anchor missing'
s = s.replace(needle, """<section class="surface admin-card" style="margin-top:18px">
  <span class="eyebrow">X LİSTESİ · OTOMATİK BAĞLANTILAR</span>
  <h2>M1–M4 görev bağlantıları</h2>
  <p class="subtle">Liste gönderileri saatine göre otomatik sınıflanır. Görev bağlantısı sadece kendi görev saatinde açılır (Türkiye saati). X üzerindeki beğeni işlemi üyeye aittir.</p>
  {% if not x_sync.enabled %}<p class="subtle"><strong>Otomatik aktarım beklemede:</strong> Render ortamına X_BEARER_TOKEN eklenmedi. Liste bağlantısını yukarıdan açabilirsin; otomatik gönderi sayısı şu an sıfır olabilir.</p>
  {% elif x_sync.last_error %}<p class="subtle">Son eşitleme hatası: {{x_sync.last_error}}</p>
  {% else %}<p class="subtle">Otomatik kontrol açık · {{x_sync.interval}} dakikada bir · Son başarılı kontrol: {{x_sync.last_success or 'Henüz yapılmadı' }}</p>{% endif %}
  <p><strong>Şu an açık görev:</strong> {{task_period or 'Görev saatleri dışında'}} · <strong>Gösterilen gün:</strong> {{x_selected_day}}</p>
  {% if x_posts %}<div class="post-list">
    {% for post in x_posts %}
    <article class="post">
      <div class="avatar">{{post.x_handle[0]|upper}}</div>
      <div class="post-main">
        <div class="post-top"><strong>@{{post.x_handle}}</strong><span class="period-badge">{{post.period}}</span></div>
        <div class="post-meta">{{format_dt(post.posted_at)}} · X gönderisi {% if post.like_count is not none %}· {{post.like_count}} beğeni{% endif %}</div>
        <div class="post-url">{{post.url}}</div>
      </div>
      {% if task_period == post.period %}<a class="button post-open" target="_blank" rel="noopener noreferrer" href="{{post.url}}">Bağlantıyı aç ↗</a>
      {% else %}<span class="button outline" aria-disabled="true">Görev saatinde açılır</span>{% endif %}
    </article>
    {% endfor %}
  </div>
  <p class="subtle">Gösterilen otomatik bağlantı: {{x_total}}{% if x_has_next %} · <a href="/?period={{period}}&q={{q|urlencode}}&page={{page + 1}}">Sonraki sayfa</a>{% endif %}</p>
  {% else %}<p class="subtle">Bugüne ait aktarılmış X gönderisi bulunmuyor. API bağlantısı yoksa bu alan boş kalır; gönderi uydurulmaz.</p>{% endif %}
</section>
""" + needle)
needle = '<a class="post-url" href="{{post.url}}" target="_blank" rel="noopener noreferrer">{{post.url}}</a>'
assert s.count(needle) == 1, 'Manual post text anchor missing'
s = s.replace(needle, '<span class="post-url">{{post.url}}</span>')
needle = '<a class="button post-open" target="_blank" rel="noopener noreferrer" href="{{post.url}}">X’te aç <span>↗</span></a>'
assert s.count(needle) == 1, 'Manual post action anchor missing'
s = s.replace(needle, """{% if task_period == post.period %}<a class="button post-open" target="_blank" rel="noopener noreferrer" href="{{post.url}}">Bağlantıyı aç ↗</a>{% else %}<span class="button outline" aria-disabled="true">Görev saatinde açılır</span>{% endif %}""")
needle = 'Aşağıdaki M1–M4 sekmeleri ise yöneticilerin panele eklediği bağlantıları gösterir.'
assert s.count(needle) == 1
s = s.replace(needle, 'Aşağıda X listesinden otomatik aktarılan bağlantılar ile yöneticilerin ekledikleri saatlerine göre gösterilir.')
p.write_text(s, encoding='utf-8')

p = root / 'templates' / 'dashboard.html'
s = p.read_text(encoding='utf-8')
needle = '<section class="surface admin-card" style="margin-top:20px"><span class="eyebrow">GÖREV DÖNEMLERİ</span>'
assert s.count(needle) == 1, 'Dashboard X stats anchor missing'
s = s.replace(needle, """<section class="surface admin-card" style="margin-top:20px">
  <span class="eyebrow">X LİSTESİ · GÜNLÜK ÖZET</span>
  <h2>Bugünkü otomatik gönderiler: {{x_today_count}}</h2>
  <div class="stats">
    <div class="stat"><div><strong>{{x_posts_per_member}}</strong><small>Aktif üye başına günlük gönderi</small></div></div>
    <div class="stat"><div><strong>{{x_avg_likes if x_avg_likes is not none else '—'}}</strong><small>Günlük gönderi başına ortalama X beğenisi (FAV)</small></div></div>
  </div>
  {% if not x_sync.enabled %}<p class="subtle">Otomatik aktarım henüz etkin değil. Render Environment bölümüne X_BEARER_TOKEN eklenmeli.</p>
  {% elif x_sync.last_error %}<p class="subtle">X aktarım sorunu: {{x_sync.last_error}}</p>
  {% else %}<p class="subtle">X senkronizasyonu: {{x_sync.interval}} dakikada bir · Son başarılı: {{x_sync.last_success or 'Henüz yok'}}</p>{% endif %}
  {% if user.role == 'owner' %}<form method="post" action="/admin/x-sync"><input type="hidden" name="csrf" value="{{csrf}}"><button type="submit" class="button outline">Listeyi şimdi eşitle</button></form>{% endif %}
  <p class="subtle">Ortalama beğeni sayısı X’in genel gönderi metriğidir; üyelerin tek tek beğenip beğenmediğini göstermez.</p>
</section>
""" + needle)
s = s.replace('Yöneticiler tarafından eklenen gerçek gönderiler burada görünür. X listesinin tamamı üstteki bağlantıyla açılır.', 'X listesinden otomatik gelen ve yöneticilerin eklediği bağlantılar görev saatinde açılır.')
p.write_text(s, encoding='utf-8')
print('MEGA FAV X List sync, periods, dashboard, and link-time gating integrated')
