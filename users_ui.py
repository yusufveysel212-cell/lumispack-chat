# -*- coding: utf-8 -*-
"""LUMISPAC - Kullanıcı Yönetimi UI Modülü (FAZ D)"""

USERS_CSS = r"""
.kul-liste{display:grid;gap:8px;margin-top:12px}
.kul-kart{background:var(--card2);border:1px solid var(--line);border-radius:12px;
  padding:12px 14px;display:flex;align-items:center;gap:14px;transition:.15s}
.kul-kart:hover{border-color:var(--red);transform:translateX(2px)}
.kul-kart.pasif{opacity:.55}
.kul-avatar{width:42px;height:42px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;color:#fff;font-weight:700;font-size:16px;flex:none}
.kul-bilgi{flex:1;min-width:0}
.kul-bilgi b{display:block;font-size:14.5px;color:var(--ink);margin-bottom:2px}
.kul-bilgi small{font-size:11.5px;color:var(--mut);display:block}
.kul-meta{display:flex;gap:10px;align-items:center;font-size:11.5px;color:var(--mut);margin-top:4px;flex-wrap:wrap}
.kul-meta .rozet{padding:2px 8px;border-radius:20px;font-size:10.5px;font-weight:600}
.kul-meta .rozet.aktif{background:#dcfce7;color:#166534}
.kul-meta .rozet.pasif{background:#fee2e2;color:#991b1b}
.kul-meta .rozet.dep{background:var(--card);color:var(--ink);border:1px solid var(--line)}
.kul-aksiyon{display:flex;gap:6px;flex:none;flex-wrap:wrap}
.kul-aksiyon button{padding:6px 10px;font-size:12px}
.kul-form label{display:block;margin-bottom:10px}
.kul-form label span{display:block;font-size:12px;color:var(--mut);margin-bottom:4px;font-weight:600}
.kul-form input,.kul-form select{width:100%}
.kul-form .ikili{display:grid;grid-template-columns:1fr 1fr;gap:10px}
"""

USERS_HTML = r"""
<div class="card" id="kullaniciKart" style="margin-top:16px">
 <h3 style="display:flex;align-items:center;gap:8px">
  <svg viewBox="0 0 24 24" style="width:18px;height:18px;stroke:var(--red);fill:none;stroke-width:2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>
  Kullanıcı Yönetimi
  <button class="btn p" style="margin-left:auto;padding:6px 12px;font-size:12px" onclick="kullaniciYeniModal()">+ Yeni Kullanıcı</button>
 </h3>
 <p class="k" style="margin:0 0 8px;font-size:12px">Kullanıcıların hangi departmana bağlı olduğunu ve aktiflik durumunu yönetin.</p>
 <div id="kulListesi" class="kul-liste">
  <div class="empty">Yükleniyor...</div>
 </div>
</div>
"""

USERS_JS = r"""
let _kullanicilar = [];
let _duzenlenen_kul = null;

async function kullaniciYukle(){
  const el = document.getElementById('kulListesi');
  if(!el) return;
  try {
    if(!_departmanlar || !_departmanlar.length){
      try { await departmanYukle(); } catch(e){}
    }
    const d = await rptApi('/api/users');
    _kullanicilar = d.kullanicilar || [];
    _kullaniciRender();
  } catch(e){
    el.innerHTML = '<div class="empty" style="color:var(--red)">Yüklenemedi: ' + esc(e.message || e) + '</div>';
  }
}

function _kullaniciRender(){
  const el = document.getElementById('kulListesi');
  if(!el) return;
  if(!_kullanicilar.length){
    el.innerHTML = '<div class="empty">Henüz kullanıcı yok.</div>';
    return;
  }
  const mevcut = (window._mevcutKullanici && window._mevcutKullanici.id) || null;
  el.innerHTML = _kullanicilar.map(function(k){
    const dep = (_departmanlar || []).find(x => x.id === k.departman_id) || {ad:'?', ikon:'?', renk:'#666'};
    const bas = (k.ad_soyad || k.kullanici_adi || '?').trim().charAt(0).toUpperCase();
    const kendisi = (k.id === mevcut);
    const son = k.son_giris ? k.son_giris.replace('T',' ') : 'hiç girmemiş';
    return '<div class="kul-kart ' + (k.aktif ? '' : 'pasif') + '">' +
      '<div class="kul-avatar" style="background:' + esc(dep.renk||'#666') + '">' + esc(bas) + '</div>' +
      '<div class="kul-bilgi">' +
        '<b>' + esc(k.ad_soyad) + (kendisi ? ' <span class="badge" style="font-size:10px;background:var(--red);color:#fff">SİZ</span>' : '') + '</b>' +
        '<small>@' + esc(k.kullanici_adi) + (k.email ? ' · ' + esc(k.email) : '') + '</small>' +
        '<div class="kul-meta">' +
          '<span class="rozet dep">' + esc(dep.ikon||'') + ' ' + esc(dep.ad) + '</span>' +
          '<span class="rozet ' + (k.aktif ? 'aktif' : 'pasif') + '">' + (k.aktif ? '● Aktif' : '○ Pasif') + '</span>' +
          '<span>Son giriş: ' + esc(son) + '</span>' +
        '</div>' +
      '</div>' +
      '<div class="kul-aksiyon">' +
        '<button class="btn s" onclick="kullaniciDuzenleModal(\'' + k.id + '\')">✏️ Düzenle</button>' +
        '<button class="btn s" onclick="kullaniciSifreSifirla(\'' + k.id + '\', \'' + esc(k.ad_soyad) + '\')" title="Şifre sıfırla">🔑</button>' +
        '<button class="btn s" onclick="kullaniciAktifToggle(\'' + k.id + '\', ' + (k.aktif ? 'false' : 'true') + ')" title="' + (k.aktif ? 'Pasifleştir' : 'Aktifleştir') + '">' + (k.aktif ? '🚫' : '✅') + '</button>' +
        (!kendisi ? '<button class="btn s" onclick="kullaniciSil(\'' + k.id + '\', \'' + esc(k.ad_soyad) + '\')" style="color:var(--red)">🗑️</button>' : '') +
      '</div>' +
    '</div>';
  }).join('');
}

function kullaniciYeniModal(){
  _duzenlenen_kul = null;
  _kullaniciModalAc({departman_id:'', aktif:true, email:'', not:''}, 'YENİ KULLANICI');
}

function kullaniciDuzenleModal(uid){
  const k = _kullanicilar.find(x => x.id === uid);
  if(!k) return;
  _duzenlenen_kul = uid;
  _kullaniciModalAc(k, 'KULLANICI DÜZENLE');
}

function _kullaniciModalAc(k, baslik){
  const yeni = !_duzenlenen_kul;
  const depSecenek = (_departmanlar || []).map(function(d){
    return '<option value="' + esc(d.id) + '"' + (d.id === k.departman_id ? ' selected' : '') + '>' +
      esc((d.ikon||'') + ' ' + d.ad) + '</option>';
  }).join('');
  const html =
    '<h2 style="margin:0 0 16px">' + (yeni ? '👤 ' : '✏️ ') + esc(baslik) + '</h2>' +
    '<div class="kul-form">' +
      '<label><span>Kullanıcı Adı *</span>' +
        '<input class="f" id="kulKadi" value="' + esc(k.kullanici_adi||'') + '" placeholder="örn: ahmet.yilmaz" maxlength="40" autocomplete="off"></label>' +
      '<label><span>Ad Soyad *</span>' +
        '<input class="f" id="kulAd" value="' + esc(k.ad_soyad||'') + '" placeholder="örn: Ahmet Yılmaz" maxlength="80"></label>' +
      '<div class="ikili">' +
        '<label><span>E-posta</span>' +
          '<input class="f" id="kulEmail" type="email" value="' + esc(k.email||'') + '" placeholder="opsiyonel" maxlength="120"></label>' +
        '<label><span>Departman *</span>' +
          '<select class="f" id="kulDep"><option value="">— Seçin —</option>' + depSecenek + '</select></label>' +
      '</div>' +
      (yeni ?
        '<div class="ikili">' +
          '<label><span>Şifre * (min 6)</span>' +
            '<input class="f" id="kulSifre" type="password" placeholder="••••••" autocomplete="new-password"></label>' +
          '<label><span>Şifre Tekrar *</span>' +
            '<input class="f" id="kulSifre2" type="password" placeholder="••••••" autocomplete="new-password"></label>' +
        '</div>' : '') +
      '<label style="display:flex;align-items:center;gap:8px;margin-top:6px">' +
        '<input type="checkbox" id="kulAktif" ' + (k.aktif !== false ? 'checked' : '') + ' style="width:auto">' +
        '<span style="margin:0">Hesap aktif</span></label>' +
    '</div>' +
    '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">' +
      '<button class="btn" onclick="closeModal()">İptal</button>' +
      '<button class="btn p" onclick="kullaniciKaydet()">💾 Kaydet</button>' +
    '</div>';
  const mBody = document.getElementById('mBody');
  if(mBody){
    mBody.innerHTML = html;
    const modal = document.getElementById('modal');
    if(modal) modal.classList.add('on');
  }
}

async function kullaniciKaydet(){
  const kadi = (document.getElementById('kulKadi')?.value || '').trim().toLowerCase();
  const ad = (document.getElementById('kulAd')?.value || '').trim();
  const email = (document.getElementById('kulEmail')?.value || '').trim();
  const dep = document.getElementById('kulDep')?.value || '';
  const aktif = !!document.getElementById('kulAktif')?.checked;
  if(kadi.length < 3) return toast('Kullanıcı adı en az 3 karakter');
  if(!/^[a-z0-9._-]+$/.test(kadi)) return toast('Kullanıcı adı: harf, rakam, . _ - kullanın');
  if(!ad) return toast('Ad soyad zorunlu');
  if(!dep) return toast('Departman seçin');
  const body = {kullanici_adi:kadi, ad_soyad:ad, email:email, departman_id:dep, aktif:aktif};
  if(!_duzenlenen_kul){
    const s1 = document.getElementById('kulSifre')?.value || '';
    const s2 = document.getElementById('kulSifre2')?.value || '';
    if(s1.length < 6) return toast('Şifre en az 6 karakter');
    if(s1 !== s2) return toast('Şifreler uyuşmuyor');
    body.sifre = s1;
  }
  try {
    const url = _duzenlenen_kul ? '/api/users/' + _duzenlenen_kul : '/api/users';
    const method = _duzenlenen_kul ? 'PATCH' : 'POST';
    const r = await fetch(url, {
      method: method,
      headers: {'Content-Type':'application/json', 'X-Auth-Token': (typeof _authToken !== 'undefined' ? _authToken : '')},
      body: JSON.stringify(body),
    });
    const d = await r.json();
    if(!r.ok || d.status !== 'success'){
      return toast('❌ ' + (d.message || 'Kaydedilemedi'));
    }
    closeModal();
    toast('✅ Kullanıcı ' + (_duzenlenen_kul ? 'güncellendi' : 'oluşturuldu'));
    kullaniciYukle();
  } catch(e){
    toast('Hata: ' + (e.message || e));
  }
}

function kullaniciSil(uid, ad){
  modernConfirm({
    baslik: 'Kullaniciyi Sil',
    mesaj: '<b>' + esc(ad) + '</b> kullanicisini silmek uzeresiniz.',
    uyari: 'Bu islem geri alinamaz!',
    onayMetni: 'Evet, Sil',
    onayla: function(){ _kullaniciSilOnayla(uid, ad); }
  });
}

async function _kullaniciSilOnayla(uid, ad){
  try {
    const r = await fetch('/api/users/' + uid, {
      method: 'DELETE',
      headers: {'X-Auth-Token': (typeof _authToken !== 'undefined' ? _authToken : '')},
    });
    const d = await r.json();
    if(!r.ok || d.status !== 'success'){
      return toast(d.message || 'Silinemedi');
    }
    toast('Kullanici silindi');
    kullaniciYukle();
  } catch(e){
    toast('Hata: ' + (e.message || e));
  }
}

async function kullaniciAktifToggle(uid, yeniDurum){
  try {
    const r = await fetch('/api/users/' + uid, {
      method: 'PATCH',
      headers: {'Content-Type':'application/json', 'X-Auth-Token': (typeof _authToken !== 'undefined' ? _authToken : '')},
      body: JSON.stringify({aktif: yeniDurum}),
    });
    const d = await r.json();
    if(!r.ok || d.status !== 'success'){
      return toast('❌ ' + (d.message || 'Güncellenemedi'));
    }
    toast('✅ Kullanıcı ' + (yeniDurum ? 'aktifleştirildi' : 'pasifleştirildi'));
    kullaniciYukle();
  } catch(e){
    toast('Hata: ' + (e.message || e));
  }
}

function kullaniciSifreSifirla(uid, ad){
  const html =
    '<h2 style="margin:0 0 16px">🔑 ŞİFRE SIFIRLA</h2>' +
    '<p class="k" style="margin:0 0 12px;font-size:12.5px">' + esc(ad) + ' için yeni şifre belirleyin.</p>' +
    '<div class="kul-form">' +
      '<label><span>Yeni Şifre * (min 6)</span>' +
        '<input class="f" id="rsSifre" type="password" placeholder="••••••" autocomplete="new-password"></label>' +
      '<label><span>Yeni Şifre Tekrar *</span>' +
        '<input class="f" id="rsSifre2" type="password" placeholder="••••••" autocomplete="new-password"></label>' +
    '</div>' +
    '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">' +
      '<button class="btn" onclick="closeModal()">İptal</button>' +
      '<button class="btn p" onclick="kullaniciSifreSifirlaOnayla(\'' + uid + '\')">🔑 Sıfırla</button>' +
    '</div>';
  const mBody = document.getElementById('mBody');
  if(mBody){
    mBody.innerHTML = html;
    const modal = document.getElementById('modal');
    if(modal) modal.classList.add('on');
  }
}

async function kullaniciSifreSifirlaOnayla(uid){
  const s1 = document.getElementById('rsSifre')?.value || '';
  const s2 = document.getElementById('rsSifre2')?.value || '';
  if(s1.length < 6) return toast('Şifre en az 6 karakter');
  if(s1 !== s2) return toast('Şifreler uyuşmuyor');
  try {
    const r = await fetch('/api/users/' + uid + '/reset-password', {
      method: 'POST',
      headers: {'Content-Type':'application/json', 'X-Auth-Token': (typeof _authToken !== 'undefined' ? _authToken : '')},
      body: JSON.stringify({yeni_sifre: s1}),
    });
    const d = await r.json();
    if(!r.ok || d.status !== 'success'){
      return toast('❌ ' + (d.message || 'Sıfırlanamadı'));
    }
    closeModal();
    toast('✅ Şifre sıfırlandı');
  } catch(e){
    toast('Hata: ' + (e.message || e));
  }
}
"""