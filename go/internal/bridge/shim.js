// Game Launcher bridge (injected by webview.Init before page scripts).
// window.gl.call(channel, payload) -> Promise; window.gl.on(event, fn).
(function () {
  'use strict'
  var ORIGIN = __GL_ORIGIN__
  var TOKEN = __GL_TOKEN__
  var BOOT = __GL_BOOT__

  // The window shows only our own origin; never run the bridge elsewhere.
  if (window.location.origin !== ORIGIN) {
    if (/^https?:$/.test(window.location.protocol)) {
      try { window.stop() } catch (e) {}
      try { document.open(); document.write('Zablokowano: launcher nie wyświetla zewnętrznych stron.'); document.close() } catch (e) {}
    }
    return
  }
  if (window.top !== window) return

  var seq = 0
  var pending = Object.create(null)
  var listeners = Object.create(null)

  function call(channel, payload) {
    return new Promise(function (resolve, reject) {
      var id = ++seq
      pending[id] = { resolve: resolve, reject: reject }
      var json
      try {
        json = JSON.stringify(payload === undefined ? null : payload)
      } catch (err) { delete pending[id]; reject(err); return }
      try {
        window.__gl_invoke(TOKEN, id, channel, json)
      } catch (err) { delete pending[id]; reject(err) }
    })
  }

  Object.defineProperty(window, '__glSettle', {
    value: function (id, ok, payload) {
      var p = pending[id]
      if (!p) return
      delete pending[id]
      if (ok) { p.resolve(payload); return }
      var err = new Error((payload && payload.message) || 'Nieznany błąd')
      err.title = payload && payload.title
      err.confirm = payload && payload.confirm
      p.reject(err)
    },
    writable: false, configurable: false, enumerable: false
  })
  Object.defineProperty(window, '__glEmit', {
    value: function (name, data) {
      var list = listeners[name]
      if (!list) return
      list.slice().forEach(function (fn) {
        try { fn(data) } catch (err) { console.error('[gl] listener', name, err) }
      })
    },
    writable: false, configurable: false, enumerable: false
  })

  var gl = {
    boot: BOOT,
    call: call,
    on: function (name, fn) { (listeners[name] = listeners[name] || []).push(fn) },
    off: function (name, fn) { var l = listeners[name]; if (l) listeners[name] = l.filter(function (f) { return f !== fn }) }
  }
  Object.defineProperty(window, 'gl', { value: Object.freeze(gl), writable: false, configurable: false })

  // External links open in the default browser; the window never navigates away.
  function external(url) {
    try {
      var u = new URL(url, window.location.href)
      if (u.origin === ORIGIN) return false
      call('app.openURL', { url: u.href }).catch(function () {})
      return true
    } catch (e) { return true }
  }
  document.addEventListener('click', function (ev) {
    var el = ev.target
    while (el && el.nodeName !== 'A') el = el.parentNode
    if (!el || !el.getAttribute) return
    var href = el.getAttribute('href')
    if (!href || href.charAt(0) === '#') return
    var u
    try { u = new URL(href, window.location.href) } catch (e) { ev.preventDefault(); return }
    if (u.origin !== ORIGIN || el.target === '_blank') {
      ev.preventDefault()
      if (u.origin !== ORIGIN) external(u.href)
    }
  }, true)
  window.open = function (url) { if (url) external(String(url)); return null }
})()
