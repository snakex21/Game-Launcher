/* Game Launcher – UI (vanilla JS, no build step). All data comes from Go
   through window.gl.call(channel, payload); events through gl.on(). User
   data is always inserted with textContent (never innerHTML). */
(function () {
  'use strict'
  var T0 = performance.now()
  var gl = window.gl || { boot: null, call: function () { return Promise.reject(new Error('Brak połączenia z launcherem')) }, on: function () {} }

  // ------------------------------------------------------------ helpers
  function h(tag, attrs) {
    var el = document.createElement(tag)
    if (attrs) {
      for (var k in attrs) {
        var v = attrs[k]
        if (v === undefined || v === null || v === false) continue
        if (k === 'class') el.className = v
        else if (k === 'text') el.textContent = v
        else if (k.slice(0, 2) === 'on') el.addEventListener(k.slice(2), v)
        else if (k === 'style') el.style.cssText = v
        else if (k === 'value') el.value = v
        else if (k === 'checked') el.checked = !!v
        else el.setAttribute(k, v === true ? '' : v)
      }
    }
    for (var i = 2; i < arguments.length; i++) add(el, arguments[i])
    return el
  }
  function add(el, c) {
    if (c === null || c === undefined || c === false) return
    if (Array.isArray(c)) { c.forEach(function (x) { add(el, x) }); return }
    el.appendChild(typeof c === 'string' || typeof c === 'number' ? document.createTextNode(String(c)) : c)
  }
  function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el }
  function $(sel, root) { return (root || document).querySelector(sel) }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)) }
  function lc(s) { return String(s || '').toLocaleLowerCase('pl') }
  function cmp(a, b) { return String(a).localeCompare(String(b), 'pl', { sensitivity: 'base', numeric: true }) }
  function dur(sec) {
    sec = Math.max(0, Math.round(sec || 0))
    var hh = Math.floor(sec / 3600), mm = Math.floor((sec % 3600) / 60)
    if (hh === 0) return mm + ' min'
    return hh + ' h ' + (mm ? mm + ' min' : '')
  }
  function hours(sec) { return ((sec || 0) / 3600).toFixed(1).replace('.', ',') + ' h' }
  function dt(ts) {
    if (!ts) return '—'
    var d = new Date(ts * 1000)
    return d.toLocaleDateString('pl-PL') + ' ' + d.toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' })
  }
  function day(ts) { return ts ? new Date(ts * 1000).toLocaleDateString('pl-PL') : '—' }
  function iso(d) { var z = new Date(d.getTime() - d.getTimezoneOffset() * 60000); return z.toISOString().slice(0, 10) }
  function coverURL(g, w) { return '/media/cover?g=' + encodeURIComponent(g.name) + '&w=' + (w || 360) + '&v=' + encodeURIComponent(g.cover || '') }
  function call(ch, p) { return gl.call(ch, p) }
  function debounce(fn, ms) { var t; return function () { var a = arguments; clearTimeout(t); t = setTimeout(function () { fn.apply(null, a) }, ms) } }

  function toast(text, kind, title) {
    var el = h('div', { class: 'toast ' + (kind || '') }, title ? h('b', { text: title }) : null, text)
    $('#toasts').appendChild(el)
    setTimeout(function () { el.remove() }, kind === 'err' ? 9000 : 4500)
  }
  function fail(e) { toast(e && e.message ? e.message : String(e), 'err', e && e.title) }

  // ------------------------------------------------------------ modals
  var modalStack = []
  function modal(opts) {
    var back = h('div', { class: 'backdrop' })
    var box = h('div', { class: 'modal' + (opts.narrow ? ' narrow' : ''), role: 'dialog', 'aria-modal': 'true' })
    var close = function (v) {
      back.remove()
      modalStack.splice(modalStack.indexOf(m), 1)
      if (m.prevFocus && m.prevFocus.focus) m.prevFocus.focus()
      if (opts.onClose) opts.onClose(v)
    }
    var m = { el: box, close: close, prevFocus: document.activeElement, back: back }
    box.appendChild(h('header', null, h('h3', { text: opts.title }), opts.head || null, h('button', { class: 'x', title: 'Zamknij (Esc)', onclick: function () { close() } }, '×')))
    var body = h('div', { class: 'body' })
    add(body, opts.body)
    box.appendChild(body)
    if (opts.footer) box.appendChild(h('footer', null, opts.footer))
    back.appendChild(box)
    back.addEventListener('mousedown', function (e) { if (e.target === back && !opts.sticky) close() })
    $('#modal-root').appendChild(back)
    modalStack.push(m)
    m.body = body
    setTimeout(function () {
      var f = box.querySelector('[autofocus]') || box.querySelector('input,select,textarea,button.primary') || box.querySelector('button')
      if (f) f.focus()
    }, 0)
    return m
  }
  function confirmBox(text, okLabel, danger) {
    return new Promise(function (resolve) {
      var done = false
      var m = modal({
        title: 'Potwierdź', narrow: true, body: h('p', { class: 'pre', text: text }),
        footer: [h('button', { class: 'btn', onclick: function () { done = true; m.close(); resolve(false) } }, 'Anuluj'),
          h('button', { class: 'btn ' + (danger ? 'stop' : 'primary'), onclick: function () { done = true; m.close(); resolve(true) } }, okLabel || 'OK')],
        onClose: function () { if (!done) resolve(false) }
      })
    })
  }
  function promptBox(title, label, value, type) {
    return new Promise(function (resolve) {
      var done = false
      var inp = h('input', { type: type || 'text', value: value == null ? '' : value, autofocus: true })
      var ok = function () { done = true; m.close(); resolve(inp.value) }
      inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); ok() } })
      var m = modal({
        title: title, narrow: true, body: h('label', { class: 'field' }, label, inp),
        footer: [h('button', { class: 'btn', onclick: function () { done = true; m.close(); resolve(null) } }, 'Anuluj'), h('button', { class: 'btn primary', onclick: ok }, 'OK')],
        onClose: function () { if (!done) resolve(null) }
      })
    })
  }

  // ------------------------------------------------------------ state
  var S = {
    page: 'library',
    games: [], groups: {}, filters: [], customGenres: [], username: '',
    view: 'tiles', tiles: 5,
    q: '', group: '', genre: '', tag: '', type: '', sort: 'name', listSort: { key: 'name', dir: 1 },
    files: {}, filterMatches: {}, running: {},
    sel: 0
  }
  function applyBoot(b) {
    if (!b) return
    S.games = b.games || []
    S.groups = b.groups || {}
    S.filters = b.filters || []
    S.customGenres = b.customGenres || []
    S.username = b.username || ''
    if (b.view === 'list' || b.view === 'tiles') S.view = b.view
    if (b.tilesPerRow) S.tiles = b.tilesPerRow
    S.games.forEach(function (g) { if (g.running) S.running[g.name] = true })
  }
  function refreshLibrary() {
    return call('app.boot').then(function (b) {
      applyBoot(b)
      if (S.filters.length) return call('filters.meta').then(function (m) { S.filterMatches = m.matches || {} })
    }).then(function () { if (S.page === 'library' || S.page === 'home') render() }).catch(fail)
  }
  var refreshSoon = debounce(refreshLibrary, 150)

  function gameByName(n) { for (var i = 0; i < S.games.length; i++) if (S.games[i].name === n) return S.games[i]; return null }
  function allGenres() {
    var set = {}
    S.games.forEach(function (g) { (g.genres || []).forEach(function (x) { set[x] = 1 }) })
    S.customGenres.forEach(function (x) { set[x] = 1 })
    return Object.keys(set).sort(cmp)
  }
  function allTags() {
    var set = {}
    S.games.forEach(function (g) { (g.tags || []).forEach(function (x) { set[x] = 1 }) })
    return Object.keys(set).sort(cmp)
  }

  function filtered() {
    var q = lc(S.q)
    var inGroup = null
    if (S.group.indexOf('g:') === 0) inGroup = S.groups[S.group.slice(2)] || []
    if (S.group.indexOf('f:') === 0) inGroup = S.filterMatches[S.group.slice(2)] || []
    var list = S.games.filter(function (g) {
      if (inGroup && inGroup.indexOf(g.name) < 0) return false
      if (S.type && g.type !== S.type) return false
      if (q && lc(g.name).indexOf(q) < 0) return false
      if (S.genre && (g.genres || []).indexOf(S.genre) < 0) return false
      if (S.tag && !(g.tags || []).some(function (t) { return lc(t) === lc(S.tag) })) return false
      return true
    })
    var key = S.view === 'list' ? S.listSort.key : S.sort
    var dir = S.view === 'list' ? S.listSort.dir : (S.sort === 'name' ? 1 : -1)
    list.sort(function (a, b) {
      var r
      switch (key) {
        case 'name': r = cmp(a.name, b.name); break
        case 'added': r = (a.dateAdded || 0) - (b.dateAdded || 0); break
        case 'time': r = (a.playTime || 0) - (b.playTime || 0); break
        case 'rating': r = (a.rating == null ? -1 : a.rating) - (b.rating == null ? -1 : b.rating); break
        case 'last': r = (a.lastPlayed || 0) - (b.lastPlayed || 0); break
        case 'completion': r = (a.completion || 0) - (b.completion || 0); break
        case 'genres': r = cmp((a.genres || []).join(','), (b.genres || []).join(',')); break
        case 'tags': r = cmp((a.tags || []).join(','), (b.tags || []).join(',')); break
        case 'version': r = cmp(a.version || '', b.version || ''); break
        default: r = 0
      }
      return r * dir || cmp(a.name, b.name)
    })
    return list
  }

  // ------------------------------------------------------------ pages
  var main = $('#main')
  function go(page) {
    S.page = page
    $all('.nav').forEach(function (b) { b.classList.toggle('active', b.dataset.page === page) })
    render()
    main.scrollTop = 0
  }
  function render() {
    var fn = PAGES[S.page] || PAGES.library
    clear(main)
    fn(main)
  }
  $all('.nav').forEach(function (b) { b.addEventListener('click', function () { go(b.dataset.page) }) })

  var PAGES = {}

  // ---- library
  var io = 'IntersectionObserver' in window ? new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return
      var img = e.target
      io.unobserve(img)
      img.src = img.dataset.src
    })
  }, { root: main, rootMargin: '400px 0px' }) : null

  function coverEl(g, w, eager) {
    var c = h('div', { class: 'cover' })
    var ph = h('div', { class: 'ph', text: g.name })
    c.appendChild(ph)
    if (g.cover) {
      var img = h('img', { alt: '', decoding: 'async' })
      img.onload = function () { img.classList.add('loaded'); ph.remove() }
      img.onerror = function () { img.remove() }
      img.dataset.src = coverURL(g, w)
      if (io && !eager) io.observe(img); else img.src = img.dataset.src
      c.insertBefore(img, ph)
    }
    return c
  }

  function launchBtn(g) {
    var running = !!S.running[g.name]
    return h('button', {
      class: 'play' + (running ? ' stop' : ''), title: running ? 'Zamknij grę' : 'Uruchom (X na padzie)', tabindex: '-1',
      onclick: function (e) { e.stopPropagation(); running ? closeGame(g.name) : launchGame(g.name) }
    }, running ? '■' : '▶')
  }

  PAGES.library = function (root) {
    var head = h('div', { class: 'row' }, h('h1', { class: 'grow', text: 'Biblioteka' }),
      h('span', { class: 'muted', id: 'count' }))
    var search = h('input', { type: 'search', placeholder: 'Szukaj… (Ctrl+F)', value: S.q, id: 'search' })
    search.addEventListener('input', debounce(function () { S.q = search.value; S.sel = 0; drawItems() }, 120))
    search.addEventListener('keydown', function (e) { if (e.key === 'ArrowDown' || e.key === 'Enter') { e.preventDefault(); focusSel() } })

    var grp = h('select', { title: 'Grupa / filtr' }, h('option', { value: '', text: 'Wszystkie gry' }))
    var gnames = Object.keys(S.groups).sort(cmp)
    if (gnames.length) grp.appendChild(h('optgroup', { label: 'Grupy' }, gnames.map(function (n) { return h('option', { value: 'g:' + n, text: n + ' (' + S.groups[n].length + ')' }) })))
    if (S.filters.length) grp.appendChild(h('optgroup', { label: 'Filtry zaawansowane' }, S.filters.map(function (n) { return h('option', { value: 'f:' + n, text: n }) })))
    grp.value = S.group
    grp.onchange = function () { S.group = grp.value; S.sel = 0; drawItems() }

    var gen = h('select', { title: 'Gatunek' }, h('option', { value: '', text: 'Wszystkie gatunki' }), allGenres().map(function (x) { return h('option', { value: x, text: x }) }))
    gen.value = S.genre
    gen.onchange = function () { S.genre = gen.value; drawItems() }
    var tag = h('select', { title: 'Tag' }, h('option', { value: '', text: 'Wszystkie tagi' }), allTags().map(function (x) { return h('option', { value: x, text: x }) }))
    tag.value = S.tag
    tag.onchange = function () { S.tag = tag.value; drawItems() }
    var typ = h('select', { title: 'Typ' }, h('option', { value: '', text: 'Wszystkie typy' }), h('option', { value: 'pc', text: 'Gry PC' }), h('option', { value: 'emulator', text: 'Emulowane' }))
    typ.value = S.type
    typ.onchange = function () { S.type = typ.value; drawItems() }
    var sort = h('select', { title: 'Sortowanie' }, [['name', 'Nazwa'], ['last', 'Ostatnio grane'], ['added', 'Data dodania'], ['time', 'Czas gry'], ['rating', 'Ocena']].map(function (o) { return h('option', { value: o[0], text: o[1] }) }))
    sort.value = S.sort
    sort.onchange = function () { S.sort = sort.value; drawItems() }

    var seg = h('div', { class: 'seg', role: 'group', 'aria-label': 'Widok' },
      h('button', { class: S.view === 'tiles' ? 'on' : '', onclick: function () { setView('tiles') } }, '▦ Kafelki'),
      h('button', { class: S.view === 'list' ? 'on' : '', onclick: function () { setView('list') } }, '☰ Lista'))

    var tb = h('div', { class: 'toolbar' }, search, grp, gen, tag, typ, S.view === 'tiles' ? sort : null, seg,
      h('span', { class: 'grow' }),
      h('button', { class: 'btn', onclick: groupsDialog, title: 'Grupy i filtry' }, 'Grupy i filtry'),
      h('button', { class: 'btn', onclick: scanDialog }, '⟳ Skanuj foldery'),
      h('button', { class: 'btn primary', onclick: function () { gameForm(null) } }, '+ Dodaj grę'))
    root.appendChild(head)
    root.appendChild(tb)
    root.appendChild(h('div', { id: 'items' }))
    drawItems()
  }

  function setView(v) {
    S.view = v
    call('settings.save', { view: v }).catch(fail)
    render()
  }

  function drawItems() {
    var box = $('#items')
    if (!box) return
    clear(box)
    var list = filtered()
    var cnt = $('#count')
    if (cnt) cnt.textContent = list.length + ' z ' + S.games.length
    if (!S.games.length) {
      box.appendChild(h('div', { class: 'empty card' }, h('p', { text: 'Biblioteka jest pusta.' }),
        h('div', { class: 'row', style: 'justify-content:center' }, h('button', { class: 'btn primary', onclick: function () { gameForm(null) } }, '+ Dodaj pierwszą grę'), h('button', { class: 'btn', onclick: scanDialog }, 'Skanuj foldery'))))
      return
    }
    if (!list.length) {
      box.appendChild(h('div', { class: 'empty', text: 'Brak gier pasujących do filtrów. Wyczyść wyszukiwanie albo wybierz „Wszystkie gry”.' }))
      return
    }
    if (S.sel >= list.length) S.sel = list.length - 1
    if (S.view === 'list') return drawList(box, list)
    var grid = h('div', { class: 'grid', id: 'grid' })
    if (S.tiles) grid.style.setProperty('--tile-w', Math.max(150, Math.min(200, Math.floor((main.clientWidth - 60) / S.tiles) - 16)) + 'px')
    list.forEach(function (g, i) {
      var t = h('div', { class: 'tile', tabindex: i === S.sel ? '0' : '-1', 'data-i': i, 'data-name': g.name, role: 'button', 'aria-label': g.name })
      var c = coverEl(g, 360)
      if (S.running[g.name]) c.appendChild(h('span', { class: 'badge run', text: '● Działa' }))
      if (S.files[g.name] || g.missing) c.appendChild(h('span', { class: 'badge miss', title: 'Nie znaleziono pliku gry', text: '⚠ Brak pliku' }))
      if (g.type === 'emulator') c.appendChild(h('span', { class: 'badge emu', text: g.emulator || 'Emulator' }))
      c.appendChild(launchBtn(g))
      t.appendChild(c)
      t.appendChild(h('div', { class: 'meta' }, h('div', { class: 'name', title: g.name, text: g.name }),
        h('div', { class: 'sub' }, h('span', { text: dur(g.playTime) }), h('span', { text: g.completion ? Math.round(g.completion) + '%' : '' }))))
      t.addEventListener('click', function () { S.sel = i; details(g.name) })
      t.addEventListener('focus', function () { S.sel = i })
      t.addEventListener('contextmenu', function (e) { e.preventDefault(); S.sel = i; details(g.name) })
      grid.appendChild(t)
    })
    box.appendChild(grid)
  }

  function drawList(box, list) {
    var cols = [['name', 'Nazwa'], ['time', 'Czas gry'], ['last', 'Ostatnio'], ['completion', 'Ukończenie'], ['rating', 'Ocena'], ['genres', 'Gatunki'], ['version', 'Wersja'], ['tags', 'Tagi'], ['added', 'Dodano']]
    var thead = h('tr', null, cols.map(function (c) {
      var mark = S.listSort.key === c[0] ? (S.listSort.dir > 0 ? ' ▲' : ' ▼') : ''
      return h('th', { class: 'sort', onclick: function () {
        if (S.listSort.key === c[0]) S.listSort.dir = -S.listSort.dir
        else S.listSort = { key: c[0], dir: c[0] === 'name' || c[0] === 'genres' || c[0] === 'tags' || c[0] === 'version' ? 1 : -1 }
        drawItems()
      } }, c[1] + mark)
    }), h('th', null, ''))
    var tbody = h('tbody', { id: 'grid' })
    list.forEach(function (g, i) {
      var tr = h('tr', { tabindex: i === S.sel ? '0' : '-1', 'data-i': i, 'data-name': g.name, class: 'tile-row' },
        h('td', null, (S.running[g.name] ? '● ' : '') + g.name + ((S.files[g.name] || g.missing) ? ' ⚠' : '')),
        h('td', { class: 'num', text: dur(g.playTime) }),
        h('td', { text: g.lastPlayed ? day(g.lastPlayed) : '—' }),
        h('td', { class: 'num', text: Math.round(g.completion || 0) + '%' }),
        h('td', { class: 'num', text: g.rating == null ? '—' : String(g.rating) }),
        h('td', { text: (g.genres || []).join(', ') }),
        h('td', { text: g.version || '' }),
        h('td', { text: (g.tags || []).join(', ') }),
        h('td', { text: g.dateAdded ? dt(g.dateAdded) : '—' }),
        h('td', null, h('button', { class: 'btn small ' + (S.running[g.name] ? 'stop' : 'primary'), tabindex: '-1', onclick: function (e) { e.stopPropagation(); S.running[g.name] ? closeGame(g.name) : launchGame(g.name) } }, S.running[g.name] ? 'Zamknij' : 'Uruchom')))
      tr.addEventListener('click', function () { S.sel = i; details(g.name) })
      tr.addEventListener('focus', function () { S.sel = i })
      tbody.appendChild(tr)
    })
    box.appendChild(h('div', { class: 'card', style: 'padding:0;overflow:auto' }, h('table', null, h('thead', null, thead), tbody)))
  }

  function items() { return $all('#grid > [data-i]') }
  function focusSel() {
    var it = items()
    if (!it.length) return
    if (S.sel < 0) S.sel = 0
    if (S.sel >= it.length) S.sel = it.length - 1
    it.forEach(function (x, i) { x.tabIndex = i === S.sel ? 0 : -1 })
    it[S.sel].focus()
    it[S.sel].scrollIntoView({ block: 'nearest' })
  }
  function gridCols() {
    var g = $('#grid')
    if (!g || g.tagName === 'TBODY') return 1
    var cols = getComputedStyle(g).gridTemplateColumns.split(' ').length
    return Math.max(1, cols)
  }
  function moveSel(dx, dy) {
    var it = items()
    if (!it.length) return
    var cols = gridCols()
    var i = S.sel + dx + dy * cols
    S.sel = Math.max(0, Math.min(it.length - 1, i))
    focusSel()
  }
  function selName() { var it = items()[S.sel]; return it ? it.dataset.name : null }

  // ---- launching
  function launchGame(name, profile) {
    return call('game.launch', { name: name, profile: profile || '' }).then(function (r) {
      S.running[name] = true
      toast('Uruchamianie: ' + name + (r && r.profile && r.profile.indexOf('Default') !== 0 ? ' (' + r.profile + ')' : ''), 'ok')
      updateRunning(); redrawSoft()
    }).catch(fail)
  }
  function closeGame(name) {
    return confirmBox('Zamknąć grę „' + name + '”? Niezapisane postępy w grze zostaną utracone.', 'Zamknij grę', true).then(function (ok) {
      if (!ok) return
      return call('game.close', { name: name }).then(function () { toast('Zamykanie: ' + name) }).catch(fail)
    })
  }
  function updateRunning() {
    var names = Object.keys(S.running)
    $('#running').textContent = names.length ? '● ' + names.join(', ') : ''
  }
  function redrawSoft() {
    if (S.page === 'library') { var f = document.activeElement && document.activeElement.dataset && document.activeElement.dataset.i; drawItems(); if (f !== undefined) focusSel() }
    else if (S.page === 'home') render()
  }

  // ---- details
  function details(name) {
    call('game.get', { name: name }).then(function (d) { showDetails(d) }).catch(fail)
  }
  function showDetails(d) {
    var m
    var cover = coverEl(d, 480, true)
    var profiles = (d.profiles || []).filter(function (p) { return p.name })
    var profSel = null
    if (d.type === 'pc' && profiles.length > 1) {
      profSel = h('select', { title: 'Profil uruchamiania' }, profiles.map(function (p) { return h('option', { value: p.name, text: p.name }) }))
    }
    var runBtn = d.running
      ? h('button', { class: 'btn stop', onclick: function () { closeGame(d.name).then(function () { m.close() }) } }, '■ Zamknij grę')
      : h('button', { class: 'btn ok', autofocus: true, onclick: function () { launchGame(d.name, profSel ? (profSel.value === profiles[0].name ? '' : profSel.value) : '').then(function () { m.close() }) } }, '▶ Uruchom')
    var info = h('div', { class: 'kv' },
      h('span', { class: 'k', text: 'Czas gry' }), h('span', { text: dur(d.playTime) + (d.sessions ? ' (' + d.sessions + ' sesji)' : '') }),
      h('span', { class: 'k', text: 'Uruchomienia' }), h('span', { text: String(d.playCount || 0) }),
      h('span', { class: 'k', text: 'Ostatnio grane' }), h('span', { text: dt(d.lastPlayed) }),
      h('span', { class: 'k', text: 'Dodano' }), h('span', { text: dt(d.dateAdded) }),
      h('span', { class: 'k', text: 'Ukończenie' }), completionInput(d),
      h('span', { class: 'k', text: 'Ocena' }), h('span', { text: d.rating == null ? '—' : d.rating + ' / 10' }),
      h('span', { class: 'k', text: d.type === 'emulator' ? 'ROM' : 'Plik gry' }), h('span', { class: 'mono', text: (d.type === 'emulator' ? d.rom : d.exe) || '—' }),
      d.missing ? h('span', { class: 'k', text: '' }) : null, d.missing ? h('span', { style: 'color:var(--warn)', text: '⚠ Plik nie istnieje – zmień ścieżkę w edycji albo użyj „Przenieś ścieżki” w Ustawieniach.' }) : null,
      d.type === 'emulator' ? h('span', { class: 'k', text: 'Emulator' }) : null, d.type === 'emulator' ? h('span', { text: d.emulator || '—' }) : null,
      h('span', { class: 'k', text: 'Zapisy gry' }), h('span', { class: 'mono', text: d.savePath || '—' }),
      d.version ? h('span', { class: 'k', text: 'Wersja' }) : null, d.version ? h('span', { text: d.version }) : null,
      h('span', { class: 'k', text: 'Gatunki' }), chips(d.genres),
      h('span', { class: 'k', text: 'Tagi' }), chips(d.tags),
      h('span', { class: 'k', text: 'Grupy' }), groupChecks(d))

    var tabsBox = h('div')
    var tabs = [['about', 'Opis i notatki'], ['info', 'Info / wymagania'], ['check', 'Checklista'], ['saves', 'Zapisy'], ['shots', 'Screenshoty (' + d.screenshots + ')']]
    var tabBar = h('div', { class: 'tabs', role: 'tablist' })
    function show(id) {
      $all('button', tabBar).forEach(function (b) { b.classList.toggle('on', b.dataset.t === id) })
      clear(tabsBox)
      TAB[id](tabsBox, d)
    }
    tabs.forEach(function (t) { tabBar.appendChild(h('button', { 'data-t': t[0], onclick: function () { show(t[0]) } }, t[1])) })

    var head = h('div', { class: 'row' },
      h('span', { class: 'muted small', text: [d.releaseDate, (d.developers || []).join(', ')].filter(Boolean).join(' · ') }),
      d.website ? h('a', { href: d.website, class: 'small' }, 'Strona WWW') : null)

    m = modal({
      title: d.name, head: null,
      body: h('div', { class: 'details' },
        h('div', null, cover,
          h('div', { class: 'row', style: 'margin-top:10px' },
            h('button', { class: 'btn small', onclick: function () { coverAction(d.name, 'pick', m) } }, 'Własna okładka…'),
            d.hasRawgCover ? h('button', { class: 'btn small', onclick: function () { coverAction(d.name, 'rawg', m) } }, 'Okładka RAWG') : null,
            d.cover ? h('button', { class: 'btn small danger', onclick: function () { coverAction(d.name, 'clear', m) } }, 'Usuń okładkę') : null)),
        h('div', null, head, h('div', { class: 'row', style: 'margin:10px 0' }, runBtn, profSel,
          h('button', { class: 'btn', onclick: function () { m.close(); gameForm(d) } }, '✎ Edytuj'),
          h('button', { class: 'btn', onclick: function (e) { fetchRAWG(d.name, e.target, m) } }, '⇩ Dane z RAWG'),
          h('button', { class: 'btn', onclick: function () { call('app.openPath', { name: d.name, which: 'exe' }).catch(fail) } }, 'Folder gry'),
          d.savePath ? h('button', { class: 'btn', onclick: function () { call('app.openPath', { name: d.name, which: 'save' }).catch(fail) } }, 'Folder zapisów') : null),
          info, tabBar, tabsBox)),
      footer: [
        h('button', { class: 'btn danger', onclick: function () { deleteGame(d.name, m) } }, 'Usuń grę'),
        h('button', { class: 'btn', onclick: function () {
          confirmBox('Wyzerować czas gry, sesje i ukończenie gry „' + d.name + '”?', 'Resetuj', true).then(function (ok) {
            if (ok) call('game.resetStats', { name: d.name }).then(function () { m.close(); details(d.name) }).catch(fail)
          })
        } }, 'Resetuj statystyki'),
        h('span', { class: 'grow' }),
        h('button', { class: 'btn', onclick: function () { m.close() } }, 'Zamknij')]
    })
    show('about')
  }
  function chips(list) { return list && list.length ? h('div', { class: 'chips' }, list.map(function (x) { return h('span', { class: 'chip', text: x }) })) : h('span', { class: 'muted', text: '—' }) }
  function completionInput(d) {
    var inp = h('input', { type: 'number', min: 0, max: 100, step: 5, value: Math.round(d.completion || 0), style: 'width:80px' })
    inp.addEventListener('change', function () {
      var v = Math.max(0, Math.min(100, Number(inp.value) || 0))
      call('game.patch', { name: d.name, completion: v }).then(function () { toast('Zapisano ukończenie: ' + v + '%', 'ok') }).catch(fail)
    })
    return h('span', null, inp, ' %')
  }
  function groupChecks(d) {
    var names = Object.keys(S.groups).sort(cmp)
    if (!names.length) return h('span', { class: 'muted', text: 'brak grup (utwórz w „Grupy i filtry”)' })
    return h('div', { class: 'chips' }, names.map(function (n) {
      var cb = h('input', { type: 'checkbox', checked: (d.groups || []).indexOf(n) >= 0 })
      cb.onchange = function () { call('groups.toggleGame', { group: n, game: d.name, in: cb.checked }).then(refreshSoon).catch(fail) }
      return h('label', { class: 'check chip' }, cb, n)
    }))
  }
  function coverAction(name, action, m) {
    call('game.cover', { name: name, action: action }).then(function (ok) { if (ok) { m.close(); refreshLibrary().then(function () { details(name) }) } }).catch(fail)
  }
  function fetchRAWG(name, btn, m) {
    btn.disabled = true
    btn.textContent = 'Pobieranie…'
    call('game.rawg', { name: name, forceCover: false }).then(function (r) {
      toast('Pobrano dane RAWG' + (r.name ? ': ' + r.name : '') + (r.coverError ? '\nOkładka: ' + r.coverError : ''), r.coverError ? '' : 'ok')
      m.close(); refreshLibrary().then(function () { details(name) })
    }).catch(function (e) { btn.disabled = false; btn.textContent = '⇩ Dane z RAWG'; fail(e) })
  }
  function deleteGame(name, m) {
    var cb = h('input', { type: 'checkbox' })
    var done = false
    var box = modal({
      title: 'Usuń grę', narrow: true,
      body: [h('p', { text: 'Usunąć „' + name + '” z biblioteki? Pliki gry na dysku zostają.' }), h('label', { class: 'check' }, cb, 'Usuń też kopie zapisów z data\\games_saves')],
      footer: [h('button', { class: 'btn', onclick: function () { box.close() } }, 'Anuluj'),
        h('button', { class: 'btn stop', onclick: function () {
          if (done) return
          done = true
          call('game.delete', { name: name, deleteBackups: cb.checked }).then(function () { box.close(); m.close(); toast('Usunięto: ' + name); refreshLibrary() }).catch(fail)
        } }, 'Usuń')]
    })
  }

  var TAB = {}
  TAB.about = function (box, d) {
    if (d.description) box.appendChild(h('div', { class: 'card pre', style: 'margin-bottom:12px;max-height:220px;overflow:auto', text: d.description }))
    var ta = h('textarea', { placeholder: 'Twoje notatki…' })
    ta.value = d.notes || ''
    box.appendChild(h('label', { class: 'field' }, 'Notatki', ta))
    box.appendChild(h('div', { class: 'row', style: 'margin-top:8px' }, h('button', { class: 'btn primary', onclick: function () {
      call('game.patch', { name: d.name, notes: ta.value }).then(function () { d.notes = ta.value; toast('Zapisano notatki', 'ok') }).catch(fail)
    } }, 'Zapisz notatki')))
  }
  TAB.info = function (box, d) {
    box.appendChild(h('div', { class: 'kv' },
      h('span', { class: 'k', text: 'Platformy' }), chips(d.platforms),
      h('span', { class: 'k', text: 'Gatunki (RAWG)' }), chips(d.genresApi),
      h('span', { class: 'k', text: 'Tagi (RAWG)' }), chips((d.tagsApi || []).slice(0, 25)),
      h('span', { class: 'k', text: 'Wydawca' }), h('span', { text: (d.publishers || []).join(', ') || '—' })))
    if (d.requirements) {
      box.appendChild(h('h2', { text: 'Wymagania PC' }))
      box.appendChild(h('div', { class: 'card pre small', text: [d.requirements.minimum, d.requirements.recommended].filter(Boolean).join('\n\n') || '—' }))
    }
    if (!d.platforms || !d.platforms.length) box.appendChild(h('p', { class: 'muted', text: 'Brak danych – użyj „Dane z RAWG”.' }))
  }
  TAB.check = function (box, d) {
    var list = (d.checklist || []).slice()
    function save() { return call('game.patch', { name: d.name, checklist: list }).then(function () { d.checklist = list }).catch(fail) }
    function draw() {
      clear(box)
      if (!list.length) box.appendChild(h('p', { class: 'muted', text: 'Brak zadań.' }))
      list.forEach(function (it, i) {
        var cb = h('input', { type: 'checkbox', checked: it.done })
        cb.onchange = function () { it.done = cb.checked; save(); draw() }
        box.appendChild(h('div', { class: 'check-item' + (it.done ? ' done' : '') }, cb, h('span', { class: 'grow', text: it.task }),
          h('button', { class: 'btn small', onclick: function () { promptBox('Edytuj zadanie', 'Zadanie', it.task).then(function (v) { if (v && v.trim()) { it.task = v.trim(); save(); draw() } }) } }, 'Edytuj'),
          h('button', { class: 'btn small danger', onclick: function () { list.splice(i, 1); save(); draw() } }, 'Usuń')))
      })
      var inp = h('input', { type: 'text', placeholder: 'Nowe zadanie…', class: 'grow' })
      var addIt = function () { if (inp.value.trim()) { list.push({ task: inp.value.trim(), done: false }); save(); draw() } }
      inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') addIt() })
      box.appendChild(h('div', { class: 'row', style: 'margin-top:10px' }, inp, h('button', { class: 'btn primary', onclick: addIt }, 'Dodaj')))
    }
    draw()
  }
  TAB.saves = function (box, d) {
    function load() {
      call('saves.list', { name: d.name }).then(function (r) {
        clear(box)
        if (!r.valid) box.appendChild(h('p', { style: 'color:var(--warn)', text: d.savePath ? 'Folder zapisów nie istnieje: ' + d.savePath : 'Gra nie ma ustawionego folderu zapisów – ustaw go w edycji gry.' }))
        box.appendChild(h('div', { class: 'row', style: 'margin-bottom:10px' },
          h('button', { class: 'btn primary', disabled: !r.valid, onclick: function () {
            promptBox('Nowa kopia zapisów', 'Procent ukończenia (0–100)', Math.round(d.completion || 0), 'number').then(function (v) {
              if (v === null) return
              call('saves.create', { name: d.name, percent: Math.round(Number(v) || 0) }).then(function () { toast('Utworzono kopię zapisów', 'ok'); load() }).catch(fail)
            })
          } }, '+ Utwórz kopię'),
          h('button', { class: 'btn', onclick: function () { call('app.openPath', { which: 'backups' }).catch(fail) } }, 'Folder kopii'),
          h('span', { class: 'muted small', text: 'Kopie: data\\games_saves\\' + d.name })))
        if (!r.entries.length) { box.appendChild(h('p', { class: 'muted', text: 'Brak kopii zapisów.' })); return }
        var tb = h('tbody')
        r.entries.forEach(function (e) {
          tb.appendChild(h('tr', null, h('td', { text: e.auto ? 'AUTO' : e.percent + '%' }), h('td', { text: dt(e.modified) }), h('td', { text: e.name }), h('td', { class: 'num', text: e.files + ' pl.' }),
            h('td', null, h('div', { class: 'row' },
              h('button', { class: 'btn small primary', disabled: !d.savePath, onclick: function () {
                confirmBox('Wczytać kopię „' + e.name + '”?\nObecne zapisy gry zostaną nadpisane (najpierw zrobię ich kopię bezpieczeństwa).', 'Wczytaj', true).then(function (ok) {
                  if (ok) call('saves.restore', { name: d.name, id: e.id }).then(function (res) { toast('Wczytano kopię' + (res.safety ? '\nKopia bezpieczeństwa: ' + res.safety : ''), 'ok'); load() }).catch(fail)
                })
              } }, 'Wczytaj'),
              e.auto ? null : h('button', { class: 'btn small', onclick: function () {
                promptBox('Zmień procent', 'Procent ukończenia', e.percent, 'number').then(function (v) { if (v !== null) call('saves.percent', { name: d.name, id: e.id, percent: Math.round(Number(v) || 0) }).then(load).catch(fail) })
              } }, '%'),
              h('button', { class: 'btn small danger', onclick: function () {
                confirmBox('Usunąć kopię „' + e.name + '”?', 'Usuń', true).then(function (ok) { if (ok) call('saves.delete', { name: d.name, id: e.id }).then(load).catch(fail) })
              } }, 'Usuń')))))
        })
        box.appendChild(h('table', null, h('thead', null, h('tr', null, h('th', null, '%'), h('th', null, 'Data'), h('th', null, 'Nazwa'), h('th', null, 'Pliki'), h('th', null, ''))), tb))
      }).catch(fail)
    }
    load()
  }
  TAB.shots = function (box, d) {
    if (!d.screenshots) { box.appendChild(h('p', { class: 'muted', text: 'Brak screenshotów.' })); return }
    var g = h('div', { class: 'shots' })
    for (var i = 0; i < d.screenshots; i++) {
      var img = h('img', { alt: '', loading: 'lazy', src: '/media/shot?g=' + encodeURIComponent(d.name) + '&i=' + i + '&w=320' })
      img.onerror = function () { this.remove() }
      g.appendChild(img)
    }
    box.appendChild(g)
  }

  // ---- add/edit form
  function pickRow(inp, kind, title, folder) {
    return h('div', { class: 'pick' }, inp, h('button', { class: 'btn', type: 'button', onclick: function () {
      (folder ? call('dialog.pickFolder', { title: title }) : call('dialog.openFile', { title: title, kind: kind })).then(function (p) { if (p) { inp.value = p; inp.dispatchEvent(new Event('change')) } }).catch(fail)
    } }, 'Wybierz…'))
  }
  function gameForm(d) {
    var isEdit = !!d
    d = d || { type: 'pc', profiles: [{ name: 'Default', exe: '', args: '' }], genres: [], tags: [] }
    call('settings.get').then(function (st) {
      var emus = Object.keys(st.emulators || {}).sort(cmp)
      var name = h('input', { type: 'text', value: d.name || '', autofocus: !isEdit })
      var type = h('select', null, h('option', { value: 'pc', text: 'Gra PC' }), h('option', { value: 'emulator', text: 'Gra emulowana' }))
      type.value = d.type || 'pc'
      var exe = h('input', { type: 'text', value: d.exe || '' })
      var emu = h('select', null, emus.length ? emus.map(function (e) { return h('option', { value: e, text: e }) }) : h('option', { value: '', text: '(dodaj emulator w Ustawieniach)' }))
      if (d.emulator) emu.value = d.emulator
      var rom = h('input', { type: 'text', value: d.rom || '' })
      var emuArgs = h('input', { type: 'text', value: d.emuArgs || '' })
      var save = h('input', { type: 'text', value: d.savePath || '' })
      var cover = h('input', { type: 'text', value: '', placeholder: isEdit ? '(bez zmian)' : '' })
      var genres = h('input', { type: 'text', value: (d.genres || []).join(', '), list: 'genre-list' })
      var tags = h('input', { type: 'text', value: (d.tags || []).join(', ') })
      var rating = h('input', { type: 'number', min: 0, max: 10, step: 0.5, value: d.rating == null ? '' : d.rating })
      var version = h('input', { type: 'text', value: d.version || '' })
      var notes = h('textarea', null)
      notes.value = d.notes || ''
      var profs = (d.profiles && d.profiles.length ? d.profiles : [{ name: 'Default', exe: '', args: '' }]).map(function (p) { return { name: p.name, exe: p.exe || '', args: p.args || '' } })
      var profBox = h('div')
      function drawProfs() {
        clear(profBox)
        profs.forEach(function (p, i) {
          var n = h('input', { type: 'text', value: p.name, style: 'width:140px', disabled: i === 0 && /^default$/i.test(p.name) })
          var e = h('input', { type: 'text', value: p.exe, placeholder: 'exe (puste = główny plik gry)' })
          var a = h('input', { type: 'text', value: p.args, placeholder: 'argumenty, np. -windowed' })
          n.oninput = function () { p.name = n.value }
          e.onchange = e.oninput = function () { p.exe = e.value }
          a.oninput = function () { p.args = a.value }
          profBox.appendChild(h('div', { class: 'row', style: 'margin-bottom:6px' }, n, h('div', { class: 'grow' }, pickRow(e, 'exe', 'Plik exe profilu')), h('div', { class: 'grow' }, a),
            i === 0 ? h('span', { style: 'width:62px' }) : h('button', { class: 'btn small danger', type: 'button', onclick: function () { profs.splice(i, 1); drawProfs() } }, 'Usuń')))
        })
        profBox.appendChild(h('button', { class: 'btn small', type: 'button', onclick: function () { profs.push({ name: 'Profil ' + profs.length, exe: '', args: '' }); drawProfs() } }, '+ Dodaj profil'))
      }
      drawProfs()
      var pcBox = h('div', { class: 'full form' }, h('label', { class: 'field full' }, 'Plik gry (.exe)', pickRow(exe, 'exe', 'Wybierz plik gry')),
        h('div', { class: 'full' }, h('div', { class: 'muted small', style: 'margin-bottom:6px', text: 'Profile uruchamiania (gra startuje w swoim folderze)' }), profBox))
      var emuBox = h('div', { class: 'full form' }, h('label', { class: 'field' }, 'Emulator', emu), h('label', { class: 'field' }, 'Argumenty emulatora', emuArgs),
        h('label', { class: 'field full' }, 'Plik ROM / ISO', pickRow(rom, 'rom', 'Wybierz ROM/ISO')))
      function toggle() { pcBox.classList.toggle('hidden', type.value !== 'pc'); emuBox.classList.toggle('hidden', type.value === 'pc') }
      type.onchange = toggle
      toggle()
      exe.addEventListener('change', function () {
        if (!name.value.trim() && exe.value) {
          var parts = exe.value.split(/[\\/]/)
          name.value = parts.length > 1 ? parts[parts.length - 2] : parts[0].replace(/\.exe$/i, '')
        }
      })
      var dl = h('datalist', { id: 'genre-list' }, allGenres().map(function (g) { return h('option', { value: g }) }))
      var body = h('div', { class: 'form' }, dl,
        h('label', { class: 'field' }, 'Nazwa gry', name), h('label', { class: 'field' }, 'Typ', type),
        pcBox, emuBox,
        h('label', { class: 'field full' }, 'Folder zapisów gry (do kopii zapisów)', pickRow(save, '', 'Folder zapisów gry', true)),
        h('label', { class: 'field full' }, 'Okładka (plik obrazu – zostanie skopiowana do images\\)', pickRow(cover, 'image', 'Wybierz okładkę')),
        h('label', { class: 'field' }, 'Gatunki (po przecinku)', genres), h('label', { class: 'field' }, 'Tagi (po przecinku)', tags),
        h('label', { class: 'field' }, 'Ocena (0–10)', rating), h('label', { class: 'field' }, 'Wersja', version),
        h('label', { class: 'field full' }, 'Notatki', notes))
      var m = modal({
        title: isEdit ? 'Edytuj grę' : 'Dodaj grę', body: body, sticky: true,
        footer: [h('button', { class: 'btn', onclick: function () { m.close() } }, 'Anuluj'), h('button', { class: 'btn primary', onclick: submit }, 'Zapisz')]
      })
      function split(s) { return s.split(',').map(function (x) { return x.trim() }).filter(Boolean) }
      function submit() {
        var payload = {
          original: isEdit ? d.name : '', name: name.value.trim(), type: type.value, exe: exe.value.trim(), emulator: emu.value, rom: rom.value.trim(), emuArgs: emuArgs.value,
          savePath: save.value.trim(), genres: split(genres.value), tags: split(tags.value), rating: rating.value === '' ? null : Number(rating.value),
          version: version.value, notes: notes.value, profiles: profs
        }
        if (cover.value.trim()) payload.cover = cover.value.trim()
        if (!isEdit) payload.cover = cover.value.trim() || null
        if (payload.cover === null) delete payload.cover
        call('game.save', payload).then(function (n) { m.close(); toast((isEdit ? 'Zapisano: ' : 'Dodano: ') + n, 'ok'); refreshLibrary().then(function () { if (isEdit) details(n) }) }).catch(fail)
      }
    }).catch(fail)
  }

  // ---- scan
  function scanDialog() {
    var status = h('p', { class: 'muted', text: 'Szukam gier w folderach z Ustawień…' })
    var body = h('div', null, status)
    var importBtn = h('button', { class: 'btn primary', disabled: true }, 'Importuj zaznaczone')
    var m = modal({
      title: 'Skanowanie folderów', body: body, sticky: true,
      footer: [h('button', { class: 'btn', onclick: function () { call('scan.cancel'); m.close() } }, 'Zamknij'), importBtn],
      onClose: function () { gl.off && gl.off('scan:progress', onProg) }
    })
    function onProg(p) { status.textContent = 'Sprawdzam: ' + p.current }
    gl.on('scan:progress', onProg)
    call('scan.run').then(function (list) {
      clear(body)
      if (!list.length) { body.appendChild(h('p', { text: 'Nie znaleziono nowych gier. Foldery skanowania ustawisz w Ustawieniach → Skanowanie.' })); return }
      body.appendChild(h('p', { class: 'muted', text: 'Znaleziono ' + list.length + '. Sprawdź nazwy i pliki exe, odznacz to, czego nie chcesz dodać.' }))
      var tb = h('tbody')
      list.forEach(function (c) {
        var cb = h('input', { type: 'checkbox', checked: c.import })
        cb.onchange = function () { c.import = cb.checked }
        var nm = h('input', { type: 'text', value: c.name })
        nm.oninput = function () { c.name = nm.value }
        var ex = h('select', null, (c.exes || [c.exe]).map(function (p) { return h('option', { value: p, text: p.split(/[\\/]/).pop() }) }))
        ex.onchange = function () { c.exe = ex.value }
        tb.appendChild(h('tr', null, h('td', null, cb), h('td', null, nm), h('td', null, ex), h('td', { class: 'mono muted', text: c.folder })))
      })
      body.appendChild(h('table', null, h('thead', null, h('tr', null, h('th', null, ''), h('th', null, 'Nazwa'), h('th', null, 'Plik exe'), h('th', null, 'Folder'))), tb))
      importBtn.disabled = false
      importBtn.onclick = function () {
        var chosen = list.filter(function (c) { return c.import && c.name.trim() })
        call('scan.import', { games: chosen }).then(function (r) {
          toast('Dodano gier: ' + r.added + (r.skipped && r.skipped.length ? '\nPominięto: ' + r.skipped.join(', ') : ''), 'ok')
          m.close(); refreshLibrary()
        }).catch(fail)
      }
    }).catch(function (e) { clear(body); body.appendChild(h('p', { text: e.message })) })
  }

  // ---- groups & filters
  function groupsDialog() {
    call('filters.meta').then(function (meta) {
      var body = h('div')
      var m = modal({ title: 'Grupy i filtry zaawansowane', body: body, footer: [h('button', { class: 'btn', onclick: function () { m.close() } }, 'Zamknij')] })
      function draw() {
        clear(body)
        body.appendChild(h('h2', { text: 'Grupy statyczne' }))
        var gn = Object.keys(S.groups).sort(cmp)
        if (!gn.length) body.appendChild(h('p', { class: 'muted', text: 'Brak grup. Gry dodajesz do grup w szczegółach gry.' }))
        gn.forEach(function (n) {
          body.appendChild(h('div', { class: 'row check-item' }, h('span', { class: 'grow', text: n + ' (' + S.groups[n].length + ')' }),
            h('button', { class: 'btn small', onclick: function () { promptBox('Zmień nazwę grupy', 'Nazwa', n).then(function (v) { if (v && v.trim() && v !== n) call('groups.save', { old: n, name: v.trim() }).then(after).catch(fail) }) } }, 'Zmień nazwę'),
            h('button', { class: 'btn small danger', onclick: function () { confirmBox('Usunąć grupę „' + n + '”? Gry zostają w bibliotece.', 'Usuń', true).then(function (ok) { if (ok) call('groups.delete', { name: n }).then(after).catch(fail) }) } }, 'Usuń')))
        })
        body.appendChild(h('button', { class: 'btn', style: 'margin-top:8px', onclick: function () { promptBox('Nowa grupa', 'Nazwa grupy').then(function (v) { if (v && v.trim()) call('groups.save', { name: v.trim() }).then(after).catch(fail) }) } }, '+ Nowa grupa'))
        body.appendChild(h('h2', { text: 'Filtry zaawansowane' }))
        var fn = Object.keys(meta.saved).sort(cmp)
        if (!fn.length) body.appendChild(h('p', { class: 'muted', text: 'Brak filtrów.' }))
        fn.forEach(function (n) {
          body.appendChild(h('div', { class: 'row check-item' }, h('span', { class: 'grow', text: n + ' – ' + meta.saved[n].length + ' reguł, pasuje ' + (meta.matches[n] || []).length + ' gier' }),
            h('button', { class: 'btn small', onclick: function () { filterEditor(meta, n, after) } }, 'Edytuj'),
            h('button', { class: 'btn small danger', onclick: function () { confirmBox('Usunąć filtr „' + n + '”?', 'Usuń', true).then(function (ok) { if (ok) call('filters.delete', { name: n }).then(after).catch(fail) }) } }, 'Usuń')))
        })
        body.appendChild(h('button', { class: 'btn', style: 'margin-top:8px', onclick: function () { filterEditor(meta, '', after) } }, '+ Nowy filtr'))
        body.appendChild(h('h2', { text: 'Gatunki własne' }))
        var gin = h('input', { type: 'text', value: S.customGenres.join(', '), style: 'width:100%' })
        body.appendChild(h('div', { class: 'row' }, h('div', { class: 'grow' }, gin), h('button', { class: 'btn', onclick: function () {
          call('genres.save', { genres: gin.value.split(',').map(function (x) { return x.trim() }).filter(Boolean) }).then(after).catch(fail)
        } }, 'Zapisz gatunki')))
      }
      function after() { return refreshLibrary().then(function () { return call('filters.meta') }).then(function (mm) { meta = mm; draw() }) }
      draw()
    }).catch(fail)
  }
  function filterEditor(meta, name, done) {
    var rules = (meta.saved[name] || []).map(function (r) { return { field: r.field, operator: r.operator, value: r.value } })
    if (!rules.length) rules.push({ field: 'name', operator: 'zawiera', value: '' })
    var nameIn = h('input', { type: 'text', value: name || 'Nowy filtr' })
    var box = h('div')
    function kind(f) { for (var i = 0; i < meta.fields.length; i++) if (meta.fields[i].key === f) return meta.fields[i].kind; return 'text' }
    function draw() {
      clear(box)
      rules.forEach(function (r, i) {
        var f = h('select', null, meta.fields.map(function (x) { return h('option', { value: x.key, text: x.label }) }))
        f.value = r.field
        var ops = meta.operators[kind(r.field)] || []
        var o = h('select', null, ops.map(function (x) { return h('option', { value: x, text: x }) }))
        if (ops.indexOf(r.operator) < 0) r.operator = ops[0]
        o.value = r.operator
        var k = kind(r.field)
        var v
        if (r.field === 'game_type') { v = h('select', null, h('option', { value: 'pc', text: 'pc' }), h('option', { value: 'emulator', text: 'emulator' })); if (!r.value) r.value = 'pc' }
        else if (r.field === 'emulator_name') { v = h('select', null, (meta.emulators || []).map(function (x) { return h('option', { value: x, text: x }) })); if (!r.value && meta.emulators && meta.emulators.length) r.value = meta.emulators[0] }
        else v = h('input', { type: k === 'date' ? 'date' : k === 'number' ? 'number' : 'text', step: 'any', list: k === 'list' ? (r.field === 'genres' ? 'f-genres' : 'f-tags') : null })
        v.value = r.value || ''
        if (/ustawione$/.test(r.operator)) v.classList.add('hidden')
        f.onchange = function () { r.field = f.value; r.value = ''; draw() }
        o.onchange = function () { r.operator = o.value; draw() }
        v.oninput = v.onchange = function () { r.value = v.value }
        box.appendChild(h('div', { class: 'row', style: 'margin-bottom:6px' }, f, o, v, h('button', { class: 'btn small danger', onclick: function () { rules.splice(i, 1); draw() } }, 'Usuń')))
      })
      box.appendChild(h('button', { class: 'btn small', onclick: function () { rules.push({ field: 'name', operator: 'zawiera', value: '' }); draw() } }, '+ Reguła'))
    }
    draw()
    var m = modal({
      title: name ? 'Edytuj filtr' : 'Nowy filtr', narrow: false,
      body: [h('datalist', { id: 'f-genres' }, allGenres().map(function (g) { return h('option', { value: g }) })), h('datalist', { id: 'f-tags' }, allTags().map(function (g) { return h('option', { value: g }) })),
        h('label', { class: 'field' }, 'Nazwa filtra', nameIn), h('p', { class: 'muted small', text: 'Gra musi spełnić wszystkie reguły (AND). Teksty bez rozróżniania wielkości liter; czas gry w godzinach.' }), box],
      footer: [h('button', { class: 'btn', onclick: function () { m.close() } }, 'Anuluj'), h('button', { class: 'btn primary', onclick: function () {
        call('filters.save', { old: name, name: nameIn.value.trim(), rules: rules }).then(function () { m.close(); done() }).catch(fail)
      } }, 'Zapisz filtr')]
    })
  }

  // ---- home
  PAGES.home = function (root) {
    var hello = ['Cześć', 'Witaj', 'Miło Cię widzieć', 'Gotowy na grę', 'Hej'][new Date().getDay() % 5]
    root.appendChild(h('h1', { text: hello + (S.username ? ', ' + S.username : '') + '!' }))
    var recent = S.games.filter(function (g) { return g.lastPlayed }).sort(function (a, b) { return b.lastPlayed - a.lastPlayed }).slice(0, 6)
    var total = S.games.reduce(function (s, g) { return s + (g.playTime || 0) }, 0)
    root.appendChild(h('div', { class: 'cards' },
      stat(String(S.games.length), 'gier w bibliotece'), stat(hours(total), 'łączny czas gry'),
      stat(String(S.games.filter(function (g) { return g.completion >= 100 }).length), 'ukończonych'),
      stat(String(Object.keys(S.running).length), 'uruchomionych teraz')))
    root.appendChild(h('h2', { text: 'Ostatnio grane' }))
    if (!recent.length) root.appendChild(h('p', { class: 'muted', text: 'Jeszcze nic nie uruchomiono.' }))
    var grid = h('div', { class: 'grid', id: 'grid' })
    recent.forEach(function (g, i) {
      var t = h('div', { class: 'tile', tabindex: i === 0 ? '0' : '-1', 'data-i': i, 'data-name': g.name })
      var c = coverEl(g, 360)
      c.appendChild(launchBtn(g))
      t.appendChild(c)
      t.appendChild(h('div', { class: 'meta' }, h('div', { class: 'name', text: g.name }), h('div', { class: 'sub' }, h('span', { text: day(g.lastPlayed) }), h('span', { text: dur(g.playTime) }))))
      t.onclick = function () { details(g.name) }
      t.onfocus = function () { S.sel = i }
      grid.appendChild(t)
    })
    root.appendChild(grid)
    var pool = S.games.filter(function (g) { return !g.missing && !S.files[g.name] })
    if (pool.length) {
      root.appendChild(h('h2', { text: 'Może dziś?' }))
      var pick = pool.slice().sort(function () { return Math.random() - 0.5 }).slice(0, 4)
      root.appendChild(h('div', { class: 'row' }, pick.map(function (g) { return h('button', { class: 'btn', onclick: function () { details(g.name) } }, '🎲 ' + g.name) })))
    }
  }
  function stat(v, l) { return h('div', { class: 'card stat' }, h('div', { class: 'v', text: v }), h('div', { class: 'l', text: l })) }

  // ---- stats
  var statRange = { from: '', to: '' }
  PAGES.stats = function (root) {
    root.appendChild(h('h1', { text: 'Statystyki' }))
    var from = h('input', { type: 'date', value: statRange.from }), to = h('input', { type: 'date', value: statRange.to })
    var box = h('div')
    function preset(days) { var d = new Date(); to.value = iso(d); d.setDate(d.getDate() - days + 1); from.value = iso(d); load() }
    function load() {
      statRange = { from: from.value, to: to.value }
      call('stats.get', statRange).then(function (s) {
        from.value = s.from; to.value = s.to
        clear(box)
        var emus = Object.keys(s.emulators || {})
        box.appendChild(h('div', { class: 'cards' }, stat(hours(s.total), 'łącznie'), stat(hours(s.pc), 'gry PC'),
          emus.length ? stat(hours(emus.reduce(function (a, k) { return a + s.emulators[k] }, 0)), 'emulatory (' + emus.join(', ') + ')') : null,
          stat(s.played + ' / ' + s.games, 'granych gier'), stat(String(s.completed), 'ukończonych w 100%'), stat(hours(s.launcherUsage), 'czas w launcherze')))
        box.appendChild(h('h2', { text: 'Czas gry dziennie: ' + s.from + ' – ' + s.to + ' (' + hours(s.rangeTotal) + ')' }))
        var max = Math.max.apply(null, s.days.map(function (d) { return d.seconds }).concat([1]))
        var bars = h('div', { class: 'bars card' }, s.days.map(function (d) { return h('div', { class: 'b', style: 'height:' + Math.max(0.5, d.seconds / max * 100) + '%', title: d.day + ': ' + dur(d.seconds) }) }))
        box.appendChild(bars)
        box.appendChild(h('div', { class: 'row muted small', style: 'justify-content:space-between' }, h('span', { text: s.from }), h('span', { text: s.to })))
        var cols = h('div', { class: 'cols2', style: 'grid-template-columns:1fr 1fr;margin-top:8px' })
        cols.appendChild(table('W wybranym okresie', s.rangeGames.slice(0, 10), s.rangeGames.length ? s.rangeGames[0].seconds : 1))
        cols.appendChild(table('Najdłużej grane (cały czas)', s.top, s.top.length ? s.top[0].seconds : 1))
        box.appendChild(cols)
        var gk = Object.keys(s.genres || {}).sort(function (a, b) { return s.genres[b] - s.genres[a] }).slice(0, 10)
        if (gk.length) box.appendChild(table('Czas wg gatunku', gk.map(function (k) { return { name: k, seconds: s.genres[k] } }), s.genres[gk[0]] || 1))
      }).catch(fail)
    }
    function table(title, rows, max) {
      var c = h('div', { class: 'card' }, h('div', { style: 'font-weight:600;margin-bottom:8px', text: title }))
      if (!rows.length) c.appendChild(h('p', { class: 'muted', text: 'Brak danych.' }))
      rows.forEach(function (r) {
        c.appendChild(h('div', { style: 'margin-bottom:6px' }, h('div', { class: 'row small' }, h('span', { class: 'grow', text: r.name }), h('span', { class: 'muted', text: dur(r.seconds) })),
          h('div', { class: 'hbar' }, h('div', { style: 'width:' + (r.seconds / max * 100) + '%' }))))
      })
      return c
    }
    root.appendChild(h('div', { class: 'toolbar' }, h('span', { class: 'muted', text: 'Zakres:' }), from, '–', to, h('button', { class: 'btn primary', onclick: load }, 'Pokaż'),
      h('button', { class: 'btn', onclick: function () { preset(7) } }, '7 dni'), h('button', { class: 'btn', onclick: function () { preset(30) } }, '30 dni'),
      h('button', { class: 'btn', onclick: function () { preset(90) } }, '90 dni'), h('button', { class: 'btn', onclick: function () { preset(365) } }, 'Rok')))
    root.appendChild(box)
    load()
  }

  // ---- roadmap
  PAGES.roadmap = function (root) {
    root.appendChild(h('h1', { text: 'Roadmapa i przypomnienia' }))
    var box = h('div')
    root.appendChild(box)
    function draw(v) {
      clear(box)
      var game = h('select', null, S.games.map(function (g) { return h('option', { value: g.name, text: g.name }) }))
      var today = iso(new Date())
      var st = h('input', { type: 'date', value: today }), en = h('input', { type: 'date', value: today })
      box.appendChild(h('div', { class: 'toolbar card' }, h('span', { text: 'Dodaj:' }), game, st, '–', en, h('button', { class: 'btn primary', onclick: function () {
        call('roadmap.add', { game: game.value, start: st.value, end: en.value }).then(draw).catch(fail)
      } }, 'Dodaj do roadmapy')))
      box.appendChild(h('h2', { text: 'Obecne' }))
      if (!v.current.length) box.appendChild(h('p', { class: 'muted', text: 'Roadmapa jest pusta.' }))
      else {
        var tb = h('tbody')
        v.current.forEach(function (r) {
          var late = r.status === 'Nie ukończona na czas'
          tb.appendChild(h('tr', null, h('td', { text: r.game_name }), h('td', { text: r.start_date }), h('td', { text: r.end_date }),
            h('td', { style: late ? 'color:var(--warn)' : '', text: r.status }), h('td', { class: 'num', text: dur(r.time_spent) }),
            h('td', null, h('div', { class: 'row' }, h('button', { class: 'btn small ok', onclick: function () { call('roadmap.complete', { name: r.game_name }).then(function (x) { toast('Ukończono: ' + r.game_name, 'ok'); draw(x) }).catch(fail) } }, 'Ukończona'),
              h('button', { class: 'btn small danger', onclick: function () { confirmBox('Usunąć „' + r.game_name + '” z roadmapy?', 'Usuń', true).then(function (ok) { if (ok) call('roadmap.delete', { name: r.game_name }).then(draw).catch(fail) }) } }, 'Usuń')))))
        })
        box.appendChild(h('div', { class: 'card', style: 'padding:0' }, h('table', null, h('thead', null, h('tr', null, ['Gra', 'Start', 'Planowany koniec', 'Status', 'Czas', ''].map(function (x) { return h('th', { text: x }) }))), tb)))
      }
      box.appendChild(h('h2', { text: 'Archiwum (' + v.archive.length + ')' }))
      if (v.archive.length) {
        var ta = h('tbody')
        v.archive.slice().reverse().forEach(function (r) { ta.appendChild(h('tr', null, h('td', { text: r.game_name }), h('td', { text: r.start_date }), h('td', { text: r.completion_date || r.end_date }), h('td', { class: 'num', text: dur(r.time_spent) }))) })
        box.appendChild(h('div', { class: 'card', style: 'padding:0' }, h('table', null, h('thead', null, h('tr', null, ['Gra', 'Start', 'Ukończono', 'Czas'].map(function (x) { return h('th', { text: x }) }))), ta)))
      }
      box.appendChild(h('h2', { text: 'Przypomnienia' }))
      var when = h('input', { type: 'datetime-local' }), msg = h('input', { type: 'text', placeholder: 'Treść przypomnienia', class: 'grow' })
      box.appendChild(h('div', { class: 'toolbar' }, when, msg, h('button', { class: 'btn primary', onclick: function () { call('reminders.add', { when: when.value, message: msg.value }).then(draw).catch(fail) } }, 'Dodaj')))
      v.reminders.forEach(function (r, i) {
        box.appendChild(h('div', { class: 'check-item' + (r.notified ? ' done' : '') }, h('span', { class: 'grow', text: dt(r.time) + ' – ' + r.message }),
          h('button', { class: 'btn small danger', onclick: function () { call('reminders.delete', { index: i }).then(draw).catch(fail) } }, 'Usuń')))
      })
    }
    call('roadmap.get').then(draw).catch(fail)
  }

  // ---- achievements
  PAGES.achievements = function (root) {
    root.appendChild(h('h1', { text: 'Osiągnięcia' }))
    call('achievements.list').then(function (list) {
      var un = list.filter(function (a) { return a.unlocked }).length
      root.appendChild(h('p', { class: 'muted', text: 'Odblokowano ' + un + ' z ' + list.length + '.' }))
      if (!list.length) root.appendChild(h('p', { class: 'muted', text: 'Brak definicji (data\\config\\achievements_def.json).' }))
      var c = h('div', { class: 'cards', style: 'grid-template-columns:repeat(auto-fill,minmax(300px,1fr))' })
      list.forEach(function (a) {
        var hidden = a.hidden && !a.unlocked
        c.appendChild(h('div', { class: 'card ach ' + (a.unlocked ? 'on' : 'off') }, h('div', { class: 'medal', text: a.unlocked ? '★' : '☆' }),
          h('div', null, h('div', { style: 'font-weight:600', text: hidden ? 'Ukryte osiągnięcie' : a.name }), h('div', { class: 'small muted', text: hidden ? '???' : a.description }),
            h('div', { class: 'small', style: 'margin-top:4px', text: a.unlocked ? 'Odblokowano ' + day(a.timestamp) : (a.target ? 'Postęp: ' + Math.round(a.progress * 100) / 100 + ' / ' + a.target : '') }))))
      })
      root.appendChild(c)
    }).catch(fail)
  }

  // ---- music
  var audio = $('#audio')
  var M = { view: null, list: 'Muzyka wewnętrzna', queue: [], idx: -1 }
  function playIdx(i) {
    if (!M.queue.length) return
    M.idx = (i + M.queue.length) % M.queue.length
    var t = M.queue[M.idx]
    if (!t.exists) { toast('Brak pliku: ' + t.path, 'err'); return }
    audio.src = '/media/track/' + t.id
    audio.play().catch(function (e) { fail(e) })
    nowPlaying()
    if (S.page === 'music') render()
  }
  function stopMusic() { audio.pause(); audio.removeAttribute('src'); audio.load(); M.idx = -1; nowPlaying(); if (S.page === 'music') render() }
  function nextTrack(dir) {
    if (!M.queue.length) return
    if (M.view && M.view.shuffle && dir > 0) return playIdx(Math.floor(Math.random() * M.queue.length))
    playIdx(M.idx + (dir || 1))
  }
  audio.addEventListener('ended', function () {
    var rep = M.view ? M.view.repeat : 'none'
    if (rep === 'one') return playIdx(M.idx)
    if (M.idx + 1 >= M.queue.length && rep !== 'all' && !(M.view && M.view.shuffle)) { stopMusic(); return }
    nextTrack(1)
  })
  function nowPlaying() {
    var el = $('#nowplaying')
    var t = M.queue[M.idx]
    if (!t || M.idx < 0) { el.classList.add('hidden'); return }
    el.classList.remove('hidden')
    clear(el).appendChild(h('div', null, h('div', { class: 'muted', text: audio.paused ? '❚❚ Pauza' : '♫ Teraz gra' }), h('div', { text: t.title })))
    if ('mediaSession' in navigator) navigator.mediaSession.metadata = new MediaMetadata({ title: t.title, artist: 'Game Launcher' })
  }
  audio.addEventListener('play', nowPlaying)
  audio.addEventListener('pause', nowPlaying)
  if ('mediaSession' in navigator) {
    navigator.mediaSession.setActionHandler('nexttrack', function () { nextTrack(1) })
    navigator.mediaSession.setActionHandler('previoustrack', function () { nextTrack(-1) })
    navigator.mediaSession.setActionHandler('stop', stopMusic)
  }
  function musicKey(e) {
    // Alt+Space play/pause, Alt+→/← next/prev, Alt+S stop, Alt+↑/↓ volume (in-app; same defaults as the Python hotkeys)
    if (!e.altKey) return false
    if (e.code === 'Space') { audio.paused ? (M.idx < 0 ? playIdx(0) : audio.play()) : audio.pause(); return true }
    if (e.key === 'ArrowRight') { nextTrack(1); return true }
    if (e.key === 'ArrowLeft') { nextTrack(-1); return true }
    if (e.key === 's' || e.key === 'S') { stopMusic(); return true }
    if (e.key === 'ArrowUp' || e.key === 'ArrowDown') { audio.volume = Math.max(0, Math.min(1, audio.volume + (e.key === 'ArrowUp' ? 0.05 : -0.05))); call('music.state', { volume: audio.volume }); return true }
    return false
  }
  PAGES.music = function (root) {
    root.appendChild(h('h1', { text: 'Muzyka' }))
    call('music.list').then(function (v) {
      M.view = v
      if (M.idx < 0) audio.volume = v.volume || 0.5
      var lists = { 'Muzyka wewnętrzna': v.internal }
      Object.keys(v.playlists).sort(cmp).forEach(function (k) { lists[k] = v.playlists[k] })
      if (!lists[M.list]) M.list = 'Muzyka wewnętrzna'
      var left = h('div', { class: 'card' })
      Object.keys(lists).forEach(function (k) {
        left.appendChild(h('button', { class: 'list-btn' + (k === M.list ? ' on' : ''), onclick: function () { M.list = k; render() } }, k + ' (' + lists[k].length + ')'))
      })
      left.appendChild(h('div', { class: 'row', style: 'margin-top:10px' },
        h('button', { class: 'btn small', onclick: function () { promptBox('Nowa playlista', 'Nazwa').then(function (n) { if (n && n.trim()) call('music.savePlaylist', { name: n.trim(), tracks: [] }).then(function () { M.list = n.trim(); render() }).catch(fail) }) } }, '+ Playlista'),
        h('button', { class: 'btn small', onclick: function () { call('music.addFolder', { playlist: M.list === 'Muzyka wewnętrzna' ? '' : M.list }).then(function (r) { if (r) render() }).catch(fail) } }, '+ Folder')))
      var tracks = lists[M.list]
      var right = h('div', { class: 'card' })
      var isPl = M.list !== 'Muzyka wewnętrzna'
      right.appendChild(h('div', { class: 'row', style: 'margin-bottom:8px' }, h('b', { class: 'grow', text: M.list }),
        h('button', { class: 'btn small primary', onclick: function () { M.queue = tracks; playIdx(0) } }, '▶ Odtwórz'),
        isPl ? h('button', { class: 'btn small danger', onclick: function () { confirmBox('Usunąć playlistę „' + M.list + '”? Pliki zostają.', 'Usuń', true).then(function (ok) { if (ok) call('music.deletePlaylist', { name: M.list }).then(function () { M.list = 'Muzyka wewnętrzna'; render() }).catch(fail) }) } }, 'Usuń playlistę') : null))
      if (!tracks.length) right.appendChild(h('p', { class: 'muted', text: isPl ? 'Pusta playlista. Dodaj folder albo utwory z „Muzyka wewnętrzna”.' : 'Brak plików w folderze internal_music.' }))
      var playlists = Object.keys(v.playlists)
      tracks.forEach(function (t, i) {
        var cur = M.queue === tracks && M.idx === i
        var addSel = null
        if (!isPl && playlists.length) {
          addSel = h('select', { class: 'small', title: 'Dodaj do playlisty' }, h('option', { value: '', text: '+ do playlisty…' }), playlists.map(function (p) { return h('option', { value: p, text: p }) }))
          addSel.onclick = function (e) { e.stopPropagation() }
          addSel.onchange = function () {
            var p = addSel.value
            if (!p) return
            var ids = v.playlists[p].map(function (x) { return x.id }).concat([t.id])
            call('music.savePlaylist', { old: p, name: p, tracks: ids }).then(function () { toast('Dodano do „' + p + '”', 'ok'); render() }).catch(fail)
          }
        }
        var rm = isPl ? h('button', { class: 'btn small', onclick: function (e) {
          e.stopPropagation()
          var ids = tracks.filter(function (_, j) { return j !== i }).map(function (x) { return x.id })
          call('music.savePlaylist', { old: M.list, name: M.list, tracks: ids }).then(render).catch(fail)
        } }, 'Usuń') : null
        right.appendChild(h('div', { class: 'track' + (cur ? ' cur' : '') + (t.exists ? '' : ' missing'), tabindex: '0', title: t.path, onclick: function () { M.queue = tracks; playIdx(i) },
          onkeydown: function (e) { if (e.key === 'Enter') { M.queue = tracks; playIdx(i) } } }, h('span', { class: 'muted', style: 'width:28px', text: cur ? '♫' : String(i + 1) }), h('span', { class: 'grow', text: t.title }), addSel, rm))
      })
      var vol = h('input', { type: 'range', min: 0, max: 1, step: 0.01, value: audio.volume })
      vol.oninput = function () { audio.volume = Number(vol.value) }
      vol.onchange = function () { call('music.state', { volume: audio.volume }) }
      var rep = h('select', null, h('option', { value: 'none', text: 'Bez powtarzania' }), h('option', { value: 'all', text: 'Powtarzaj listę' }), h('option', { value: 'one', text: 'Powtarzaj utwór' }))
      rep.value = v.repeat || 'none'
      rep.onchange = function () { v.repeat = rep.value; call('music.state', { repeat: rep.value }) }
      var sh = h('input', { type: 'checkbox', checked: v.shuffle })
      sh.onchange = function () { v.shuffle = sh.checked; call('music.state', { shuffle: sh.checked }) }
      var player = h('div', { class: 'card player' },
        h('button', { class: 'btn', title: 'Poprzedni (Alt+←)', onclick: function () { nextTrack(-1) } }, '⏮'),
        h('button', { class: 'btn primary', title: 'Odtwórz/pauza (Alt+Spacja)', onclick: function () { audio.paused ? (M.idx < 0 ? (M.queue = tracks, playIdx(0)) : audio.play()) : audio.pause() } }, audio.paused ? '▶' : '❚❚'),
        h('button', { class: 'btn', title: 'Stop (Alt+S)', onclick: stopMusic }, '■'),
        h('button', { class: 'btn', title: 'Następny (Alt+→)', onclick: function () { nextTrack(1) } }, '⏭'),
        h('span', { class: 'grow', text: M.idx >= 0 && M.queue[M.idx] ? M.queue[M.idx].title : 'Nic nie gra' }),
        h('label', { class: 'check' }, sh, 'Losowo'), rep, h('span', { class: 'muted', text: 'Głośność' }), vol)
      root.appendChild(h('div', { class: 'cols2' }, left, right))
      root.appendChild(player)
    }).catch(fail)
  }

  // ---- chat
  PAGES.chat = function (root) {
    root.appendChild(h('h1', { text: 'Czat' }))
    root.appendChild(h('div', { class: 'card', style: 'margin-bottom:14px' }, h('p', { style: 'margin:0', text: 'Klient czatu (Socket.IO) nie jest jeszcze przeniesiony do wersji Go. Poniżej: skonfigurowane serwery i archiwum lokalnego serwera (tylko odczyt, plik nie jest zmieniany).' })))
    call('chat.archive').then(function (v) {
      root.appendChild(h('h2', { text: 'Serwery czatu' }))
      v.servers.forEach(function (s) { root.appendChild(h('div', { class: 'check-item' }, h('span', { class: 'grow', text: s.name + (s.id === v.active ? '  (aktywny)' : '') }), h('span', { class: 'mono muted', text: s.url }))) })
      root.appendChild(h('h2', { text: 'Archiwum: data\\chat\\chat.db' }))
      if (v.error) { root.appendChild(h('p', { style: 'color:var(--warn)', text: v.error })); return }
      var a = v.archive
      root.appendChild(h('div', { class: 'cards' }, stat(String(a.users), 'użytkowników'), stat(String(a.messages), 'wiadomości'), stat(String(a.private), 'prywatnych'), stat(String(a.rooms.length), 'pokoi')))
      if (a.rooms.length) root.appendChild(h('p', { class: 'muted', text: 'Pokoje: ' + a.rooms.map(function (r) { return r.name + (r.locked ? ' 🔒' : '') + ' (' + r.messages + ')' }).join(', ') }))
      a.recent.forEach(function (m) {
        root.appendChild(h('div', { class: 'check-item' }, h('span', { class: 'muted small', style: 'width:150px', text: m.timestamp.slice(0, 16) }),
          h('b', { text: m.sender }), h('span', { class: 'muted small', text: m.room ? '#' + m.room : '→ ' + m.receiver }), h('span', { class: 'grow', text: m.content + (m.attachment ? ' 📎 ' + m.attachment : '') + (m.edited ? ' (edytowano)' : '') })))
      })
    }).catch(fail)
  }

  // ---- settings
  PAGES.settings = function (root) {
    root.appendChild(h('h1', { text: 'Ustawienia' }))
    var box = h('div')
    root.appendChild(box)
    call('settings.get').then(function (s) { drawSettings(box, s) }).catch(fail)
  }
  function section(title, desc) {
    var c = h('div', { class: 'card', style: 'margin-bottom:14px' }, h('h2', { style: 'margin-top:0', text: title }))
    if (desc) c.appendChild(h('p', { class: 'muted small', style: 'margin-top:-4px', text: desc }))
    return c
  }
  function drawSettings(box, s) {
    clear(box)
    function save(p) { return call('settings.save', p).then(function (n) { toast('Zapisano', 'ok'); refreshSoon(); drawSettings(box, n) }).catch(fail) }

    var user = h('input', { type: 'text', value: s.username || '' })
    var tiles = h('input', { type: 'number', min: 2, max: 12, value: s.tilesPerRow || 5, style: 'width:80px' })
    var view = h('select', null, h('option', { value: 'tiles', text: 'Kafelki' }), h('option', { value: 'list', text: 'Lista' }))
    view.value = s.view || 'tiles'
    var ab = h('input', { type: 'checkbox', checked: s.autoBackupOnExit })
    var c1 = section('Ogólne')
    c1.appendChild(h('div', { class: 'form' }, h('label', { class: 'field' }, 'Nazwa użytkownika', user), h('label', { class: 'field' }, 'Widok biblioteki', view),
      h('label', { class: 'field' }, 'Kafelków w rzędzie', tiles), h('label', { class: 'check', style: 'align-self:end' }, ab, 'Automatyczna kopia zapisów po wyjściu z gry')))
    c1.appendChild(h('div', { class: 'row', style: 'margin-top:10px' }, h('button', { class: 'btn primary', onclick: function () {
      S.tiles = Number(tiles.value) || 5; S.view = view.value
      save({ username: user.value, view: view.value, tilesPerRow: Number(tiles.value) || 5, autoBackupOnExit: ab.checked })
    } }, 'Zapisz')))
    box.appendChild(c1)

    var c2 = section('Skanowanie folderów z grami', 'Foldery przeszukiwane przez „Skanuj foldery” w bibliotece. Każdy podfolder z plikiem .exe gry jest proponowany do dodania.')
    var folders = (s.scanFolders || []).slice()
    var fl = h('div')
    function drawF() {
      clear(fl)
      if (!folders.length) fl.appendChild(h('p', { class: 'muted', text: 'Brak folderów.' }))
      folders.forEach(function (f, i) { fl.appendChild(h('div', { class: 'check-item' }, h('span', { class: 'grow mono', text: f }), h('button', { class: 'btn small danger', onclick: function () { folders.splice(i, 1); drawF() } }, 'Usuń'))) })
    }
    drawF()
    var rec = h('input', { type: 'checkbox', checked: s.scanRecursive })
    var ign = h('input', { type: 'text', value: (s.scanIgnore || []).join(', ') })
    c2.appendChild(fl)
    c2.appendChild(h('div', { class: 'row', style: 'margin:8px 0' }, h('button', { class: 'btn', onclick: function () { call('dialog.pickFolder', { title: 'Folder z grami' }).then(function (p) { if (p && folders.indexOf(p) < 0) { folders.push(p); drawF() } }).catch(fail) } }, '+ Dodaj folder'),
      h('label', { class: 'check' }, rec, 'Skanuj podfoldery (do 4 poziomów)')))
    c2.appendChild(h('label', { class: 'field' }, 'Pomijane nazwy folderów (po przecinku)', ign))
    c2.appendChild(h('div', { class: 'row', style: 'margin-top:10px' }, h('button', { class: 'btn primary', onclick: function () {
      save({ scanFolders: folders, scanRecursive: rec.checked, scanIgnore: ign.value.split(',').map(function (x) { return x.trim() }).filter(Boolean) })
    } }, 'Zapisz'), h('button', { class: 'btn', onclick: function () { go('library'); scanDialog() } }, 'Skanuj teraz')))
    box.appendChild(c2)

    var c3 = section('Emulatory')
    Object.keys(s.emulators).sort(cmp).forEach(function (n) {
      c3.appendChild(h('div', { class: 'check-item' }, h('b', { text: n }), h('span', { class: 'grow mono muted', text: s.emulators[n] }),
        h('button', { class: 'btn small', onclick: function () { emuDialog(n, s.emulators[n], function (x) { drawSettings(box, x) }) } }, 'Edytuj'),
        h('button', { class: 'btn small danger', onclick: function () { confirmBox('Usunąć emulator „' + n + '”?', 'Usuń', true).then(function (ok) { if (ok) call('emulators.delete', { name: n }).then(function (x) { drawSettings(box, x) }).catch(fail) }) } }, 'Usuń')))
    })
    c3.appendChild(h('button', { class: 'btn', style: 'margin-top:8px', onclick: function () { emuDialog('', '', function (x) { drawSettings(box, x) }) } }, '+ Dodaj emulator'))
    box.appendChild(c3)

    var c4 = section('Klucze API', 'Klucze są zapisywane w data\\config\\local_settings.json (nie trafiają do gita) i nigdy nie są wyświetlane. Można je też podać zmiennymi GL_RAWG_API_KEY i GL_LASTFM_API_KEY.')
    ;[['rawg_api_key', 'RAWG (okładki i opisy gier)'], ['lastfm_api_key', 'Last.fm (okładki muzyki)'], ['github_token', 'GitHub (kopia w chmurze)']].forEach(function (k) {
      var st = s.secrets[k[0]]
      var inp = h('input', { type: 'password', placeholder: st ? '•••••• (ustawiony – wpisz nowy, aby zmienić)' : 'wklej klucz', autocomplete: 'off', disabled: st === 'zmienna' })
      c4.appendChild(h('div', { class: 'row', style: 'margin-bottom:8px' }, h('span', { style: 'width:220px', text: k[1] }), h('div', { class: 'grow' }, inp),
        h('span', { class: 'muted small', style: 'width:150px', text: st === 'zmienna' ? 'ze zmiennej środowiskowej' : st === 'nieczytelny' ? 'nieczytelny (inny komputer) – wpisz ponownie' : st ? 'ustawiony (DPAPI)' : 'brak' }),
        h('button', { class: 'btn', disabled: st === 'zmienna', onclick: function () { call('settings.setSecret', { key: k[0], value: inp.value }).then(function (x) { toast('Zapisano klucz', 'ok'); drawSettings(box, x) }).catch(fail) } }, 'Zapisz')))
    })
    box.appendChild(c4)

    var r = s.remote
    var c5 = section('Pilot WWW (telefon / przeglądarka)', 'Lista gier i uruchamianie z innego urządzenia. Dostęp tylko z tokenem; domyślnie wyłącznie z tego komputera (127.0.0.1). Port pilota musi być inny niż port czatu (5000).')
    var en = h('input', { type: 'checkbox', checked: r.enabled })
    var port = h('input', { type: 'number', value: r.port, min: 1024, max: 65535, style: 'width:100px' })
    var lan = h('input', { type: 'checkbox', checked: r.lan })
    c5.appendChild(h('div', { class: 'row' }, h('label', { class: 'check' }, en, 'Włączony'), h('span', { text: 'Port' }), port, h('label', { class: 'check' }, lan, 'Dostęp z sieci lokalnej (LAN)'),
      h('button', { class: 'btn primary', onclick: function () { call('remote.apply', { enabled: en.checked, port: Number(port.value), lan: lan.checked }).then(function () { return call('settings.get') }).then(function (x) { drawSettings(box, x) }).catch(fail) } }, 'Zastosuj'),
      h('button', { class: 'btn', disabled: !r.enabled, onclick: function () { confirmBox('Wygenerować nowy token? Stare linki przestaną działać.', 'Generuj').then(function (ok) { if (ok) call('remote.regenerate').then(function () { return call('settings.get') }).then(function (x) { drawSettings(box, x) }).catch(fail) }) } }, 'Nowy token')))
    c5.appendChild(h('p', { class: 'small', style: r.running ? 'color:var(--ok)' : 'color:var(--muted)', text: r.running ? '● Działa' : (r.error ? 'Błąd: ' + r.error : 'Zatrzymany') }))
    ;(r.urls || []).forEach(function (u) { c5.appendChild(h('div', { class: 'mono', text: u })) })
    box.appendChild(c5)

    var c6 = section('Przenośność', 'Ścieżki gier na dysku launchera są zapisywane bez litery dysku, więc po zmianie litery pendrive’a (E: → F:) gry dalej działają. Profil WebView2 też leży na tym dysku.')
    c6.appendChild(h('div', { class: 'kv' }, h('span', { class: 'k', text: 'Folder launchera' }), h('span', { class: 'mono', text: s.appDir }),
      h('span', { class: 'k', text: 'Dysk launchera' }), h('span', { text: s.launcherDrive || '—' }),
      h('span', { class: 'k', text: 'Profil WebView2' }), h('span', { class: 'mono', text: s.webview2Profile || '(domyślny)' }),
      h('span', { class: 'k', text: 'Wersja' }), h('span', { text: s.version }),
      h('span', { class: 'k', text: 'Czas w launcherze' }), h('span', { text: hours(s.totalUsage) + ', dni z rzędu: ' + s.consecutiveDays })))
    var from = h('input', { type: 'text', placeholder: 'np. E:\\Gry' }), to = h('input', { type: 'text', placeholder: 'np. F:\\Gry' })
    c6.appendChild(h('h2', { text: 'Przenieś ścieżki gier' }))
    c6.appendChild(h('div', { class: 'row' }, from, '→', to, h('button', { class: 'btn', onclick: function () {
      call('game.relocate', { from: from.value, to: to.value }).then(function (n) { toast('Zmieniono ścieżek: ' + n, 'ok'); refreshLibrary() }).catch(fail)
    } }, 'Zamień prefiks we wszystkich grach'), h('button', { class: 'btn', onclick: function () { call('app.openPath', { which: 'data' }).catch(fail) } }, 'Otwórz folder danych')))
    box.appendChild(c6)

    var c7 = section('Sterowanie')
    c7.appendChild(h('div', { class: 'kv small' },
      h('span', { class: 'kbd', text: 'strzałki' }), h('span', { text: 'poruszanie po bibliotece' }), h('span', { class: 'kbd', text: 'Enter' }), h('span', { text: 'szczegóły gry' }),
      h('span', { class: 'kbd', text: 'Ctrl+Enter / P' }), h('span', { text: 'uruchom zaznaczoną grę' }), h('span', { class: 'kbd', text: 'Ctrl+F lub /' }), h('span', { text: 'szukaj' }),
      h('span', { class: 'kbd', text: 'Esc' }), h('span', { text: 'zamknij okno / wróć' }), h('span', { class: 'kbd', text: 'Ctrl+1…8' }), h('span', { text: 'zakładki' }),
      h('span', { class: 'kbd', text: 'Alt+Spacja, Alt+←/→, Alt+S' }), h('span', { text: 'muzyka: pauza, poprzedni/następny, stop' }),
      h('span', { class: 'kbd', text: 'Pad: D-pad / gałka' }), h('span', { text: 'poruszanie' }), h('span', { class: 'kbd', text: 'Pad: A / B' }), h('span', { text: 'otwórz / wróć' }),
      h('span', { class: 'kbd', text: 'Pad: X / Y' }), h('span', { text: 'uruchom grę / szukaj' }), h('span', { class: 'kbd', text: 'Pad: LB / RB' }), h('span', { text: 'poprzednia / następna zakładka' })))
    box.appendChild(c7)
  }
  function emuDialog(name, path, done) {
    var n = h('input', { type: 'text', value: name }), p = h('input', { type: 'text', value: path })
    var m = modal({
      title: name ? 'Edytuj emulator' : 'Dodaj emulator', narrow: true,
      body: [h('label', { class: 'field' }, 'Nazwa (np. PCSX2)', n), h('label', { class: 'field', style: 'margin-top:10px' }, 'Plik emulatora', pickRow(p, 'exe', 'Plik emulatora'))],
      footer: [h('button', { class: 'btn', onclick: function () { m.close() } }, 'Anuluj'), h('button', { class: 'btn primary', onclick: function () {
        call('emulators.save', { old: name, name: n.value, path: p.value }).then(function (x) { m.close(); done(x) }).catch(fail)
      } }, 'Zapisz')]
    })
  }

  // ------------------------------------------------------------ keyboard
  var ORDER = ['home', 'library', 'stats', 'roadmap', 'achievements', 'music', 'chat', 'settings']
  document.addEventListener('keydown', function (e) {
    if (musicKey(e)) { e.preventDefault(); return }
    var tag = (e.target.tagName || '').toLowerCase()
    var typing = tag === 'input' || tag === 'textarea' || tag === 'select'
    if (e.key === 'Escape') {
      if (modalStack.length) { e.preventDefault(); modalStack[modalStack.length - 1].close(); return }
      if (typing) { e.target.blur(); focusSel(); return }
    }
    if (modalStack.length) return
    if (e.ctrlKey && e.key >= '1' && e.key <= '8') { e.preventDefault(); go(ORDER[Number(e.key) - 1]); return }
    if ((e.ctrlKey && (e.key === 'f' || e.key === 'F')) || (!typing && e.key === '/')) {
      e.preventDefault()
      if (S.page !== 'library') go('library')
      var s = $('#search'); if (s) { s.focus(); s.select() }
      return
    }
    if (typing) return
    if (S.page !== 'library' && S.page !== 'home') return
    var k = e.key
    if (k === 'ArrowRight') { e.preventDefault(); moveSel(1, 0) }
    else if (k === 'ArrowLeft') { e.preventDefault(); moveSel(-1, 0) }
    else if (k === 'ArrowDown') { e.preventDefault(); moveSel(0, 1) }
    else if (k === 'ArrowUp') { e.preventDefault(); moveSel(0, -1) }
    else if (k === 'Home') { e.preventDefault(); S.sel = 0; focusSel() }
    else if (k === 'End') { e.preventDefault(); S.sel = 1e9; focusSel() }
    else if (k === 'PageDown') { e.preventDefault(); moveSel(0, 3) }
    else if (k === 'PageUp') { e.preventDefault(); moveSel(0, -3) }
    else if ((k === 'Enter' && e.ctrlKey) || k === 'p' || k === 'P') { var n = selName(); if (n) { e.preventDefault(); S.running[n] ? closeGame(n) : launchGame(n) } }
    else if (k === 'Enter' || k === ' ') { var nm = selName(); if (nm) { e.preventDefault(); details(nm) } }
  })

  // ------------------------------------------------------------ gamepad
  var pad = { prev: {}, repeatAt: {}, active: false }
  function padPress(btn, now, held) {
    // first press, then auto-repeat for directions
    if (!held) { delete pad.repeatAt[btn]; return false }
    if (!pad.prev[btn]) { pad.repeatAt[btn] = now + 380; return true }
    if (pad.repeatAt[btn] && now >= pad.repeatAt[btn]) { pad.repeatAt[btn] = now + 110; return true }
    return false
  }
  function key(k, opts) { document.activeElement && document.activeElement.dispatchEvent(new KeyboardEvent('keydown', Object.assign({ key: k, bubbles: true }, opts || {}))) }
  function padFocusNext(dir) {
    var root = modalStack.length ? modalStack[modalStack.length - 1].el : main
    var f = $all('button:not([disabled]),input:not([disabled]),select,textarea,[tabindex="0"],a[href]', root).filter(function (x) { return x.offsetParent !== null })
    if (!f.length) return
    var i = f.indexOf(document.activeElement)
    f[(i + dir + f.length) % f.length].focus()
  }
  function pollPad() {
    var pads = navigator.getGamepads ? navigator.getGamepads() : []
    var p = null
    for (var i = 0; i < pads.length; i++) if (pads[i] && pads[i].connected) { p = pads[i]; break }
    if (p) {
      var now = performance.now()
      var b = function (i) { return !!(p.buttons[i] && p.buttons[i].pressed) }
      var ax = p.axes[0] || 0, ay = p.axes[1] || 0
      var st = {
        up: b(12) || ay < -0.55, down: b(13) || ay > 0.55, left: b(14) || ax < -0.55, right: b(15) || ax > 0.55,
        a: b(0), b: b(1), x: b(2), y: b(3), lb: b(4), rb: b(5), start: b(9)
      }
      var inGrid = !modalStack.length && (S.page === 'library' || S.page === 'home') && items().length
      ;['up', 'down', 'left', 'right'].forEach(function (d) {
        if (padPress(d, now, st[d])) {
          if (inGrid) moveSel(d === 'left' ? -1 : d === 'right' ? 1 : 0, d === 'up' ? -1 : d === 'down' ? 1 : 0)
          else padFocusNext(d === 'up' || d === 'left' ? -1 : 1)
        }
      })
      if (st.a && !pad.prev.a) {
        if (inGrid && selName()) details(selName())
        else if (document.activeElement) document.activeElement.click()
      }
      if (st.b && !pad.prev.b) { if (modalStack.length) modalStack[modalStack.length - 1].close(); else if (S.page !== 'library') go('library') }
      if (st.x && !pad.prev.x) { var n = selName(); if (n && !modalStack.length) { S.running[n] ? closeGame(n) : launchGame(n) } }
      if (st.y && !pad.prev.y && !modalStack.length) { if (S.page !== 'library') go('library'); var s = $('#search'); if (s) s.focus() }
      if (st.lb && !pad.prev.lb && !modalStack.length) go(ORDER[(ORDER.indexOf(S.page) + ORDER.length - 1) % ORDER.length])
      if (st.rb && !pad.prev.rb && !modalStack.length) go(ORDER[(ORDER.indexOf(S.page) + 1) % ORDER.length])
      pad.prev = st
    }
    if (pad.active) requestAnimationFrame(pollPad)
  }
  window.addEventListener('gamepadconnected', function () { if (!pad.active) { pad.active = true; toast('Pad podłączony'); requestAnimationFrame(pollPad) } })
  window.addEventListener('gamepaddisconnected', function () { var any = navigator.getGamepads && Array.prototype.some.call(navigator.getGamepads(), function (x) { return x }); if (!any) pad.active = false })

  // ------------------------------------------------------------ events from Go
  gl.on('library:changed', function () { refreshSoon() })
  gl.on('library:files', function (m) { S.files = m || {}; redrawSoft() })
  gl.on('game:started', function (e) { S.running[e.name] = true; updateRunning(); if (e.detected) toast('Wykryto uruchomioną grę: ' + e.name); redrawSoft() })
  gl.on('game:stopped', function (e) {
    delete S.running[e.name]; updateRunning()
    var msg = 'Sesja: ' + dur(e.seconds)
    if (e.autosaved) msg += '\nAutomatyczna kopia zapisów: ' + e.autosaved + ' plików'
    if (e.autosaveError) msg += '\nKopia zapisów nie powiodła się: ' + e.autosaveError
    if (e.openTasks) msg += '\nOtwarte zadania na checkliście: ' + e.openTasks
    toast(msg, 'ok', 'Koniec gry: ' + e.name)
    refreshSoon()
  })
  gl.on('reminder', function (e) { toast(e.message, '', '⏰ Przypomnienie') })
  gl.on('achievement', function (e) { toast(e.name, 'ok', '★ Nowe osiągnięcie') })
  gl.on('roadmap:changed', function () { if (S.page === 'roadmap') render() })

  // ------------------------------------------------------------ start
  applyBoot(gl.boot)
  updateRunning()
  var sp = gl.boot && gl.boot.startPage || ''
  if (sp.indexOf('game:') === 0) { go('library'); details(sp.slice(5)) }
  else if (sp.indexOf('modal:') === 0) { go('library'); ({ scan: scanDialog, groups: groupsDialog, add: function () { gameForm(null) } }[sp.slice(6)] || function () {})() }
  else go(PAGES[sp] ? sp : 'library')
  ;(gl.boot && gl.boot.warnings || []).forEach(function (w) { toast(w, 'err') })
  if (gl.boot && gl.boot.remapped) toast('Zmieniła się litera dysku launchera – przemapowano ścieżek: ' + gl.boot.remapped, 'ok')
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      focusSel()
      call('app.painted', { games: S.games.length, jsMs: performance.now() - T0 }).catch(function () {})
      if (S.filters.length) call('filters.meta').then(function (m) { S.filterMatches = m.matches || {} }).catch(function () {})
    })
  })
})()
