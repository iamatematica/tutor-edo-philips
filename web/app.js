/* Tutor de Ecuaciones Diferenciales · front sin build ni frameworks. */
(function () {
  'use strict';

  var CLAVE_TOKEN = 'tutor-edo.v1.token';
  var CLAVE_ID = 'tutor-edo.v1.id';
  var BIENVENIDA = 'Hola. Escribí la ecuación con la que estás trabajando, o contame dónde te trabaste. ' +
    'Si no sabés por dónde empezar, tocá **Pista**.';

  var $ = function (sel) { return document.querySelector(sel); };
  var vistaLogin = $('#vista-login');
  var vistaChat = $('#vista-chat');
  var formLogin = $('#form-login');
  var errorLogin = $('#error-login');
  var listaMensajes = $('#mensajes');
  var formMensaje = $('#form-mensaje');
  var campoMensaje = $('#campo-mensaje');
  var botonPista = $('#boton-pista');
  var botonEnviar = $('#boton-enviar');
  var avisoChat = $('#aviso-chat');
  var esperando = false;

  /* ---------- almacenamiento (puede fallar en modo privado o en iframes) ---------- */
  function leer(clave) { try { return window.localStorage.getItem(clave); } catch (e) { return null; } }
  function escribir(clave, valor) {
    try {
      if (valor === null) window.localStorage.removeItem(clave);
      else window.localStorage.setItem(clave, valor);
    } catch (e) { /* sin persistencia: la sesión dura lo que dure la pestaña */ }
  }
  var sesion = { token: leer(CLAVE_TOKEN), id: leer(CLAVE_ID) };

  /* ---------- API ---------- */
  function api(metodo, ruta, cuerpo) {
    var opciones = { method: metodo, headers: {} };
    if (sesion.token) opciones.headers.Authorization = 'Bearer ' + sesion.token;
    if (cuerpo !== undefined) {
      opciones.headers['Content-Type'] = 'application/json';
      opciones.body = JSON.stringify(cuerpo);
    }
    return fetch(ruta, opciones).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (datos) {
        if (!r.ok) {
          var err = new Error(mensajeDeError(datos, r.status));
          err.status = r.status;
          throw err;
        }
        return datos;
      });
    }, function () {
      var err = new Error('No hay conexión. Revisá internet y probá de nuevo.');
      err.status = 0;
      throw err;
    });
  }

  function mensajeDeError(datos, status) {
    if (datos && typeof datos.detail === 'string') return datos.detail;
    if (status === 422) return 'Revisá lo que escribiste.';
    return 'Algo falló. Probá de nuevo en un momento.';
  }

  /* ---------- matemática ---------- */
  var MACROS = {
    '\\neq': '\\mathrel{\\text{\\char"2260}}',
    '\\ne': '\\mathrel{\\text{\\char"2260}}',
    '\\lim': '\\mathop{\\text{lím}}\\limits',
    '\\sen': '\\operatorname{sen}'
  };
  var hayKatex = typeof window.katex !== 'undefined';
  if (!hayKatex) window.__katexFailed = true;

  function escapar(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function formula(tex, display) {
    if (hayKatex) {
      try {
        return window.katex.renderToString(tex, {
          displayMode: display, throwOnError: false, macros: MACROS, strict: 'ignore'
        });
      } catch (e) { /* cae al respaldo */ }
    }
    var html = TexARespaldo.convertir(tex);
    return display
      ? '<span class="mfall mfall-display">' + html + '</span>'
      : '<span class="mfall">' + html + '</span>';
  }

  // Texto sin fórmulas: escapado, **negrita**, `código` y saltos de línea.
  function prosa(s) {
    return escapar(s)
      .replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`\n]+)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br>');
  }

  var RE_MATE = /\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)|\$([^$\n]+?)\$/g;

  function renderizar(texto) {
    var html = '';
    var ultimo = 0;
    var trasDisplay = false;
    var m;
    RE_MATE.lastIndex = 0;
    while ((m = RE_MATE.exec(texto)) !== null) {
      var display = m[1] !== undefined || m[2] !== undefined;
      var antes = texto.slice(ultimo, m.index);
      // Los saltos pegados a una fórmula en display ya los pone el bloque.
      if (trasDisplay) antes = antes.replace(/^[ \t]*\n/, '');
      if (display) antes = antes.replace(/\n[ \t]*$/, '');
      html += prosa(antes);
      html += formula(m[1] || m[2] || m[3] || m[4], display);
      trasDisplay = display;
      ultimo = RE_MATE.lastIndex;
    }
    var resto = texto.slice(ultimo);
    if (trasDisplay) resto = resto.replace(/^[ \t]*\n/, '');
    return html + prosa(resto);
  }

  /* Conversor mínimo TeX → HTML para cuando KaTeX no carga: nunca LaTeX crudo a la vista. */
  var TexARespaldo = (function () {
    var SIMBOLOS = {
      cdot: '·', times: '×', pm: '±', mp: '∓', to: '→', rightarrow: '→', Rightarrow: '⇒',
      Leftrightarrow: '⇔', implies: '⇒', iff: '⇔', le: '≤', leq: '≤', ge: '≥', geq: '≥',
      ne: '≠', neq: '≠', approx: '≈', equiv: '≡', infty: '∞', int: '∫', partial: '∂',
      alpha: 'α', beta: 'β', gamma: 'γ', delta: 'δ', Delta: 'Δ', epsilon: 'ε', varepsilon: 'ε',
      theta: 'θ', lambda: 'λ', mu: 'μ', pi: 'π', rho: 'ρ', sigma: 'σ', tau: 'τ', phi: 'φ',
      varphi: 'φ', omega: 'ω', Omega: 'Ω', prime: '′', circ: '°', degree: '°', ldots: '…',
      dots: '…', cdots: '⋯', quad: ' ', qquad: '  ', ',': ' ', ';': ' ',
      ':': ' ', '!': '', ' ': ' ', '{': '{', '}': '}', '%': '%', '$': '$', '\\': '<br>',
      lbrace: '{', rbrace: '}', vert: '|', mid: '|', in: '∈', cdotp: '·', displaystyle: '',
      textstyle: '', limits: '', left: '', right: '', big: '', Big: '', bigl: '', bigr: ''
    };
    var FUNCIONES = { ln: 'ln', log: 'log', sen: 'sen', sin: 'sen', cos: 'cos', tan: 'tan', tg: 'tg',
      exp: 'exp', lim: 'lím', max: 'máx', min: 'mín' };

    function convertir(tex) {
      var p = { s: tex, i: 0 };
      return secuencia(p, null);
    }

    function secuencia(p, cierre) {
      var out = '';
      while (p.i < p.s.length) {
        var c = p.s[p.i];
        if (cierre && c === cierre) { p.i++; return out; }
        out += atomo(p);
      }
      return out;
    }

    function grupo(p) {
      saltarEspacios(p);
      if (p.s[p.i] === '{') { p.i++; return secuencia(p, '}'); }
      return atomo(p);
    }

    function textoCrudo(p) {
      saltarEspacios(p);
      if (p.s[p.i] !== '{') return escapar(p.s[p.i++] || '');
      var prof = 0, ini = ++p.i;
      while (p.i < p.s.length) {
        if (p.s[p.i] === '{') prof++;
        else if (p.s[p.i] === '}') { if (prof === 0) break; prof--; }
        p.i++;
      }
      var t = p.s.slice(ini, p.i);
      p.i++;
      return escapar(t);
    }

    function saltarEspacios(p) { while (p.s[p.i] === ' ') p.i++; }

    function atomo(p) {
      var c = p.s[p.i];
      if (c === '\\') return comando(p);
      if (c === '{') { p.i++; return secuencia(p, '}'); }
      if (c === '^' || c === '_') {
        p.i++;
        var cont = grupo(p);
        return c === '^' ? '<sup>' + cont + '</sup>' : '<sub>' + cont + '</sub>';
      }
      p.i++;
      if (/[A-Za-z]/.test(c)) return '<i>' + c + '</i>';
      if (c === "'") return '′';
      if (c === '-') return '−';
      if (c === '=' || c === '+' || c === '<' || c === '>') return ' ' + escapar(c) + ' ';
      if (c === '~') return ' ';
      return escapar(c);
    }

    function comando(p) {
      p.i++;
      var m = /^[A-Za-z]+/.exec(p.s.slice(p.i));
      var nombre = m ? m[0] : p.s[p.i];
      p.i += nombre ? nombre.length : 1;
      if (nombre === 'frac' || nombre === 'dfrac' || nombre === 'tfrac') {
        var num = grupo(p), den = grupo(p);
        return '<span class="frac"><span class="num">' + num + '</span><span class="den">' + den + '</span></span>';
      }
      if (nombre === 'sqrt') {
        var indice = '';
        if (p.s[p.i] === '[') {
          var fin = p.s.indexOf(']', p.i);
          indice = '<sup>' + escapar(p.s.slice(p.i + 1, fin)) + '</sup>';
          p.i = fin + 1;
        }
        return indice + '√<span class="raiz">' + grupo(p) + '</span>';
      }
      if (nombre === 'text' || nombre === 'mathrm' || nombre === 'operatorname' || nombre === 'textrm') {
        return '<span>' + textoCrudo(p) + '</span>';
      }
      if (nombre === 'mathbf' || nombre === 'textbf') return '<b>' + grupo(p) + '</b>';
      if (nombre === 'mathit' || nombre === 'textit') return '<i>' + grupo(p) + '</i>';
      if (nombre === 'char') { // \char"2260 de la macro de ≠
        var hex = /^"([0-9A-Fa-f]+)/.exec(p.s.slice(p.i));
        if (hex) { p.i += hex[0].length; return '&#x' + hex[1] + ';'; }
        return '';
      }
      if (nombre === 'mathrel' || nombre === 'mathop' || nombre === 'mathbin') return grupo(p);
      if (Object.prototype.hasOwnProperty.call(FUNCIONES, nombre)) return FUNCIONES[nombre] + ' ';
      if (Object.prototype.hasOwnProperty.call(SIMBOLOS, nombre)) return SIMBOLOS[nombre];
      return escapar(nombre || '');
    }

    return { convertir: convertir };
  })();

  /* ---------- vistas ---------- */
  function mostrar(vista) {
    vistaLogin.hidden = vista !== 'login';
    vistaChat.hidden = vista !== 'chat';
  }

  function irALogin(mensaje) {
    sesion = { token: null, id: null };
    escribir(CLAVE_TOKEN, null);
    escribir(CLAVE_ID, null);
    listaMensajes.innerHTML = '';
    mostrar('login');
    if (mensaje) { errorLogin.textContent = mensaje; errorLogin.hidden = false; }
    $('#campo-id').focus();
  }

  function burbuja(rol, texto, opciones) {
    opciones = opciones || {};
    var div = document.createElement('div');
    var esTutor = rol === 'assistant';
    div.className = 'msg ' + (esTutor ? 'msg-tutor' : 'msg-vos') + (opciones.pista ? ' msg-pista' : '');
    var quien = document.createElement('div');
    quien.className = 'msg-quien';
    quien.textContent = esTutor ? 'Tutor' : 'Vos';
    var cuerpo = document.createElement('div');
    cuerpo.className = 'msg-texto';
    cuerpo.innerHTML = opciones.html || renderizar(texto);
    div.appendChild(quien);
    div.appendChild(cuerpo);
    listaMensajes.appendChild(div);
    return div;
  }

  function alFinal(el) {
    if (el && el.scrollIntoView) el.scrollIntoView({ block: 'end', behavior: 'smooth' });
  }

  function ponerEtiquetaPista(etiqueta) {
    botonPista.textContent = etiqueta === 'Otra pista' ? 'Otra pista' : 'Pista';
  }

  function ocupado(si) {
    esperando = si;
    botonPista.disabled = si;
    botonEnviar.disabled = si;
  }

  function avisar(texto) {
    avisoChat.textContent = texto || '';
    avisoChat.hidden = !texto;
  }

  function crecer() {
    campoMensaje.style.height = 'auto';
    campoMensaje.style.height = campoMensaje.scrollHeight + 'px';
    campoMensaje.style.overflowY = campoMensaje.scrollHeight > campoMensaje.clientHeight + 2 ? 'auto' : 'hidden';
  }

  /* ---------- flujo ---------- */
  function abrirChat() {
    $('#badge-id').textContent = sesion.id || '';
    mostrar('chat');
    return api('GET', '/api/historial').then(function (datos) {
      listaMensajes.innerHTML = '';
      if (!datos.mensajes.length) burbuja('assistant', BIENVENIDA);
      datos.mensajes.forEach(function (m) { burbuja(m.rol, m.texto, { pista: m.pista }); });
      ponerEtiquetaPista(datos.etiqueta_pista);
      alFinal(listaMensajes.lastElementChild);
    }).catch(function (err) {
      if (err.status === 401) irALogin(err.message);
      else avisar(err.message);
    });
  }

  function enviar(pista) {
    if (esperando) return;
    var texto = campoMensaje.value.trim();
    if (!pista && !texto) { campoMensaje.focus(); return; }
    avisar('');
    ocupado(true);

    var propia = burbuja('user', pista ? 'Pista' : texto, { pista: pista });
    if (!pista) { campoMensaje.value = ''; crecer(); }
    var espera = burbuja('assistant', '', {
      html: 'Pensando<span class="puntos"><span>.</span><span>.</span><span>.</span></span>'
    });
    espera.classList.add('pensando');
    alFinal(espera);

    api('POST', '/api/mensaje', pista ? { texto: '', pista: true } : { texto: texto, pista: false })
      .then(function (datos) {
        espera.remove();
        alFinal(burbuja('assistant', datos.respuesta));
        ponerEtiquetaPista(datos.etiqueta_pista);
      })
      .catch(function (err) {
        espera.remove();
        propia.remove();
        if (err.status === 401) { irALogin(err.message); return; }
        if (!pista && !campoMensaje.value) { campoMensaje.value = texto; crecer(); }
        avisar(err.message);
      })
      .then(function () { ocupado(false); });
  }

  formLogin.addEventListener('submit', function (e) {
    e.preventDefault();
    var id = $('#campo-id').value.trim();
    var codigo = $('#campo-codigo').value.trim();
    if (!id || !codigo) {
      errorLogin.textContent = 'Completá el identificador y el código.';
      errorLogin.hidden = false;
      return;
    }
    errorLogin.hidden = true;
    var boton = $('#boton-entrar');
    boton.disabled = true;
    api('POST', '/api/login', { id: id, codigo: codigo }).then(function (datos) {
      sesion = { token: datos.token, id: datos.id };
      escribir(CLAVE_TOKEN, datos.token);
      escribir(CLAVE_ID, datos.id);
      $('#campo-codigo').value = '';
      return abrirChat();
    }).catch(function (err) {
      errorLogin.textContent = err.message;
      errorLogin.hidden = false;
    }).then(function () { boton.disabled = false; });
  });

  formMensaje.addEventListener('submit', function (e) { e.preventDefault(); enviar(false); });

  campoMensaje.addEventListener('input', crecer);
  campoMensaje.addEventListener('keydown', function (e) {
    // En computadora Enter envía y Shift+Enter baja de línea; en el celular Enter baja de línea.
    var tactil = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
    if (e.key === 'Enter' && !e.shiftKey && !tactil && !e.isComposing) {
      e.preventDefault();
      enviar(false);
    }
  });

  document.addEventListener('click', function (e) {
    var t = e.target.closest('[data-accion]');
    if (!t) return;
    if (t.dataset.accion === 'pista') enviar(true);
    if (t.dataset.accion === 'salir') {
      api('POST', '/api/logout').catch(function () {}).then(function () { irALogin(); });
    }
  });

  if (sesion.token) abrirChat();
  else mostrar('login');

  // Para pruebas automatizadas del renderizado.
  window.__tutor = { renderizar: renderizar, respaldo: TexARespaldo.convertir };
})();
