/* Panel docente del tutor · sin build ni frameworks. Lee /api/metricas con la clave de docente. */
(function () {
  'use strict';

  var CLAVE = 'tutor-edo.v1.docente';
  var ERRORES = {
    E01: 'Exponente leído como orden',
    E02: 'Constante sumando o en el exponente',
    E03: 'Condición inicial antes de integrar',
    E04: 'Verifica con un punto, no derivando',
    E05: 'Olvida el ½ al integrar e^{2x}',
    E06: 'P sin signo o sin dividir',
    E07: 'Método u·v mal aplicado',
    E08: 'Homogéneas: y = ux mal derivada o K sin x',
    E09: 'Física: valor final, τ, L, signos',
    E10: 'Pide la respuesta directa'
  };
  var PEDIDOS = { orientacion: 'Orientación', respuesta: 'Respuesta', verificacion: 'Verificación', conversacion: 'Conversación' };
  var COLOR_PEDIDO = { orientacion: '', respuesta: 'violeta', verificacion: 'verde', conversacion: 'ambar' };
  var ESTADOS = { avanzando: 'avanzando', trabado: 'trabado', resuelto_por_estudiante: 'resuelto' };

  var $ = function (s) { return document.querySelector(s); };
  var datos = null;
  var orden = { col: 'id', dir: 1 };

  function leer() { try { return window.sessionStorage.getItem(CLAVE); } catch (e) { return null; } }
  function escribir(v) {
    try { if (v === null) window.sessionStorage.removeItem(CLAVE); else window.sessionStorage.setItem(CLAVE, v); }
    catch (e) { /* sin almacenamiento: la clave dura lo que dure la página */ }
  }
  var clave = leer();

  /* ---------- API ---------- */
  function pedir(ruta) {
    return fetch(ruta, { headers: { 'X-Docente-Key': clave || '' }, cache: 'no-store' }).then(function (r) {
      if (r.ok) return r;
      return r.json().catch(function () { return {}; }).then(function (d) {
        var err = new Error(typeof d.detail === 'string' ? d.detail : 'Algo falló. Probá de nuevo.');
        err.status = r.status;
        throw err;
      });
    }, function () {
      var err = new Error('No hay conexión con el servidor.');
      err.status = 0;
      throw err;
    });
  }
  function pedirJson(ruta) { return pedir(ruta).then(function (r) { return r.json(); }); }

  /* ---------- utilidades ---------- */
  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function num(x, dec) {
    if (x === null || x === undefined) return '—';
    return Number(x).toLocaleString('es-AR', { maximumFractionDigits: dec === undefined ? 1 : dec });
  }
  function pct(x) { return x === null || x === undefined ? '—' : Math.round(x * 100) + ' %'; }
  function minutos(m) {
    if (!m) return '0 min';
    if (m < 60) return num(m, 0) + ' min';
    return Math.floor(m / 60) + ' h ' + Math.round(m % 60) + ' min';
  }
  function fechaSemana(iso) { var p = iso.split('-'); return p[2] + '/' + p[1]; }

  function avisar(t) { var a = $('#aviso-panel'); a.textContent = t || ''; a.hidden = !t; }

  /* ---------- matemática (KaTeX; si no carga, el TeX queda en monoespaciada) ---------- */
  var MACROS = {
    '\\neq': '\\mathrel{\\text{\\char"2260}}', '\\ne': '\\mathrel{\\text{\\char"2260}}',
    '\\lim': '\\mathop{\\text{lím}}\\limits', '\\sen': '\\operatorname{sen}'
  };
  function formula(tex, display) {
    if (window.katex) {
      try {
        return window.katex.renderToString(tex, { displayMode: display, throwOnError: false, macros: MACROS, strict: 'ignore' });
      } catch (e) { /* respaldo */ }
    }
    return '<code class="tex-crudo">' + esc(display ? '$$' + tex + '$$' : '$' + tex + '$') + '</code>';
  }
  function prosa(s) {
    return esc(s).replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`\n]+)`/g, '<code>$1</code>').replace(/\n/g, '<br>');
  }
  var RE_MATE = /\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)|\$([^$\n]+?)\$/g;
  function renderizar(texto) {
    var html = '', ultimo = 0, m;
    RE_MATE.lastIndex = 0;
    while ((m = RE_MATE.exec(texto)) !== null) {
      html += prosa(texto.slice(ultimo, m.index));
      html += formula(m[1] || m[2] || m[3] || m[4], m[1] !== undefined || m[2] !== undefined);
      ultimo = RE_MATE.lastIndex;
    }
    return html + prosa(texto.slice(ultimo));
  }

  /* ---------- vistas ---------- */
  function mostrar(vista) {
    $('#vista-clave').hidden = vista !== 'clave';
    $('#vista-panel').hidden = vista !== 'panel';
  }
  function irAClave(mensaje) {
    clave = null;
    escribir(null);
    datos = null;
    mostrar('clave');
    var e = $('#error-clave');
    e.textContent = mensaje || '';
    e.hidden = !mensaje;
    $('#campo-clave').focus();
  }
  function pestana(nombre) {
    document.querySelectorAll('[data-pestana]').forEach(function (b) {
      b.setAttribute('aria-selected', b.dataset.pestana === nombre ? 'true' : 'false');
    });
    document.querySelectorAll('[data-hoja]').forEach(function (h) { h.hidden = h.dataset.hoja !== nombre; });
  }

  function barras(cont, filas, color) {
    var max = Math.max.apply(null, filas.map(function (f) { return f.valor; }).concat([0]));
    if (!max) { cont.innerHTML = '<p class="vacio">Todavía no hay datos.</p>'; return; }
    cont.innerHTML = filas.map(function (f) {
      var ancho = f.valor ? Math.max(1, Math.round(100 * f.valor / max)) : 0;
      return '<div class="barra-fila"><span class="barra-rotulo" title="' + esc(f.rotulo) + '">' + esc(f.rotulo) +
        '</span><span class="barra-pista"><span class="barra-relleno ' + (f.color || color || '') +
        '" style="display:block;width:' + ancho + '%"></span></span><span class="barra-valor">' +
        esc(f.texto || num(f.valor, 0)) + '</span></div>';
    }).join('');
  }

  /* ---------- Curso ---------- */
  function pintarCurso() {
    var c = datos.curso;
    var tiles = [
      [c.estudiantes_activos + ' / ' + c.estudiantes, 'estudiantes que usaron el tutor'],
      [num(c.ingresos, 0), 'ingresos (sesiones)'],
      [minutos(c.minutos), 'conectados en total'],
      [num(c.turnos, 0), 'turnos'],
      [num(c.turnos_por_sesion), 'turnos por sesión'],
      [num(c.ejercicios_abordados, 0), 'ejercicios del banco abordados'],
      [num(c.resoluciones, 0), 'ejercicios resueltos por los estudiantes'],
      [pct(c.proporcion_orientacion), 'orientación (vs. pedido de respuesta)'],
      [num(c.escalon_promedio), 'pista más alta, en promedio (0 a 4)']
    ];
    $('#tiles').innerHTML = tiles.map(function (t) {
      return '<div class="tile"><div class="tile-valor">' + esc(t[0]) + '</div><div class="tile-rotulo">' + esc(t[1]) + '</div></div>';
    }).join('');

    var k = datos.costo;
    var p = k.proporcion_tope || 0;
    $('#costo').innerHTML =
      '<div class="costo-grande">US$ ' + num(k.costo_mes_usd, 2) + ' <small>en el mes</small></div>' +
      '<div class="medidor' + (p >= 1 ? ' excedido' : p >= 0.75 ? ' alto' : '') + '" role="img" aria-label="' +
      pct(p) + ' del tope mensual"><div style="width:' + Math.min(100, Math.round(p * 100)) + '%"></div></div>' +
      '<ul class="costo-detalle">' +
      '<li>' + pct(p) + ' del tope mensual de US$ ' + num(k.tope_mensual_usd, 0) + ' fijado en la consola de la API.</li>' +
      '<li>Hoy: ' + num(k.turnos_dia, 0) + ' turnos ≈ US$ ' + num(k.costo_dia_usd, 2) + '.</li>' +
      '<li>Mes: ' + num(k.turnos_mes, 0) + ' turnos × US$ ' + num(k.costo_medio_turno_usd, 4) + ' por turno.</li>' +
      '<li>Es una estimación: el gasto real está en la consola de la API.</li></ul>';

    barras($('#semanas'), datos.semanas.map(function (s, i) {
      return { rotulo: 'Sem. del ' + fechaSemana(s), valor: c.ingresos_por_semana[i] };
    }));
    var totalPedidos = Object.keys(PEDIDOS).reduce(function (a, t) { return a + c.pedidos[t]; }, 0);
    barras($('#pedidos'), Object.keys(PEDIDOS).map(function (t) {
      return { rotulo: PEDIDOS[t], valor: c.pedidos[t], color: COLOR_PEDIDO[t],
        texto: totalPedidos ? pct(c.pedidos[t] / totalPedidos) : '0' };
    }));
    barras($('#dispositivos'), [
      { rotulo: 'Celular', valor: c.dispositivos.celular },
      { rotulo: 'Computadora', valor: c.dispositivos.computadora, color: 'ambar' }
    ]);
  }

  /* ---------- Estudiantes ---------- */
  var COLUMNAS = [
    { id: 'id', rotulo: 'Estudiante', valor: function (f) { return f.id; } },
    { id: 'ingresos', rotulo: 'Ingresos', valor: function (f) { return f.ingresos; } },
    { id: 'minutos', rotulo: 'Minutos', valor: function (f) { return f.minutos; } },
    { id: 'turnos', rotulo: 'Turnos', valor: function (f) { return f.turnos; } },
    { id: 'tps', rotulo: 'Turnos/sesión', valor: function (f) { return f.turnos_por_sesion; } },
    { id: 'cel', rotulo: 'Celular', valor: function (f) { return f.dispositivos.celular; } },
    { id: 'pc', rotulo: 'Compu', valor: function (f) { return f.dispositivos.computadora; } },
    { id: 'abordados', rotulo: 'Abordados', valor: function (f) { return f.ejercicios_abordados; } },
    { id: 'resueltos', rotulo: 'Resueltos', valor: function (f) { return f.ejercicios_resueltos; } },
    { id: 'orient', rotulo: 'Orientación', valor: function (f) { return f.proporcion_orientacion; }, formato: pct },
    { id: 'resp', rotulo: 'Pide respuesta', valor: function (f) { return f.pedidos.respuesta; } },
    { id: 'escalon', rotulo: 'Escalón prom.', valor: function (f) { return f.escalon_promedio; } },
    { id: 'errores', rotulo: 'Errores', valor: function (f) { return totalErrores(f); }, html: celdaErrores, clase: 'texto' },
    { id: 'ultima', rotulo: 'Última actividad', valor: function (f) { return f.ultima_actividad; } }
  ];
  function totalErrores(f) {
    return Object.keys(f.errores).reduce(function (a, c) { return a + f.errores[c]; }, 0);
  }
  function celdaErrores(f) {
    var cods = Object.keys(f.errores).sort(function (a, b) { return f.errores[b] - f.errores[a]; });
    if (!cods.length) return '—';
    return cods.map(function (c) {
      return '<span class="chip-error" title="' + esc(ERRORES[c] || '') + '">' + esc(c) + ' ×' + f.errores[c] + '</span>';
    }).join('');
  }
  function comparar(a, b) {
    if (a === b) return 0;
    if (a === null || a === undefined) return 1;
    if (b === null || b === undefined) return -1;
    return a < b ? -1 : 1;
  }

  function pintarEstudiantes() {
    var col = COLUMNAS.filter(function (c) { return c.id === orden.col; })[0];
    var filas = datos.estudiantes.slice().sort(function (a, b) {
      var r = comparar(col.valor(a), col.valor(b));
      return r === 0 ? comparar(a.id, b.id) : (r * (col.valor(a) === null || col.valor(b) === null ? 1 : orden.dir));
    });
    var thead = '<thead><tr>' + COLUMNAS.map(function (c) {
      var sort = c.id === orden.col ? (orden.dir > 0 ? 'ascending' : 'descending') : 'none';
      return '<th scope="col" data-col="' + c.id + '" aria-sort="' + sort + '"' + (c.clase ? ' class="' + c.clase + '"' : '') + '>' + esc(c.rotulo) + '</th>';
    }).join('') + '</tr></thead>';
    var tbody = '<tbody>' + filas.map(function (f) {
      return '<tr' + (f.turnos ? '' : ' class="inactivo"') + '>' + COLUMNAS.map(function (c) {
        var v;
        if (c.id === 'id') v = '<button type="button" class="enlace-est" data-ver="' + esc(f.id) + '">' + esc(f.id) + '</button>';
        else if (c.id === 'minutos') v = esc(num(f.minutos, 0));
        else if (c.html) v = c.html(f);
        else if (c.formato) v = esc(c.formato(c.valor(f)));
        else { var x = c.valor(f); v = esc(typeof x === 'number' ? num(x) : (x === null ? '—' : x)); }
        return '<td' + (c.clase ? ' class="' + c.clase + '"' : '') + '>' + v + '</td>';
      }).join('') + '</tr>';
    }).join('') + '</tbody>';
    $('#tabla-estudiantes').innerHTML = thead + tbody;

    var semanas = datos.semanas;
    var t = $('#tabla-semanas');
    if (!semanas.length) { t.innerHTML = '<tbody><tr><td>Todavía no hubo ingresos.</td></tr></tbody>'; return; }
    t.innerHTML = '<thead><tr><th scope="col">Estudiante</th>' + semanas.map(function (s) {
      return '<th scope="col">Sem. ' + esc(fechaSemana(s)) + '</th>';
    }).join('') + '<th scope="col">Total</th></tr></thead><tbody>' +
      datos.estudiantes.map(function (f) {
        return '<tr' + (f.ingresos ? '' : ' class="inactivo"') + '><td class="codigo">' + esc(f.id) + '</td>' +
          f.ingresos_por_semana.map(function (n) { return '<td>' + (n || '·') + '</td>'; }).join('') +
          '<td>' + f.ingresos + '</td></tr>';
      }).join('') + '</tbody><tfoot><tr><td>Curso</td>' +
      datos.curso.ingresos_por_semana.map(function (n) { return '<td>' + n + '</td>'; }).join('') +
      '<td>' + datos.curso.ingresos + '</td></tr></tfoot>';
  }

  /* ---------- Ejercicios y errores ---------- */
  function pintarEjercicios() {
    var ej = datos.ejercicios;
    $('#tabla-ejercicios').innerHTML = ej.length
      ? '<thead><tr><th>Ejercicio</th><th>Abordado por</th><th>Se trabaron</th><th>Turnos trabado</th><th>Lo resolvieron</th><th>Turnos</th><th>Escalón prom.</th></tr></thead><tbody>' +
        ej.map(function (e) {
          return '<tr><td class="codigo">' + esc(e.ejercicio) + '</td><td>' + e.abordado_por + '</td><td>' + e.trabados +
            '</td><td>' + e.turnos_trabado + '</td><td>' + e.resuelto_por + '</td><td>' + e.turnos + '</td><td>' +
            esc(num(e.escalon_promedio)) + '</td></tr>';
        }).join('') + '</tbody>'
      : '<tbody><tr><td>Todavía nadie trabajó un ejercicio del banco.</td></tr></tbody>';

    var er = datos.errores;
    var max = er.length ? er[0].veces : 0;
    $('#tabla-errores').innerHTML = er.length
      ? '<thead><tr><th>Código</th><th class="texto">Error</th><th>Veces</th><th>Estudiantes</th><th class="texto">Frecuencia</th></tr></thead><tbody>' +
        er.map(function (e) {
          return '<tr><td class="codigo">' + esc(e.codigo) + '</td><td class="texto">' + esc(ERRORES[e.codigo] || '') +
            '</td><td>' + e.veces + '</td><td>' + e.estudiantes + '</td><td class="texto"><span class="barra-pista" style="display:block"><span class="barra-relleno terra" style="display:block;width:' +
            Math.round(100 * e.veces / max) + '%"></span></span></td></tr>';
        }).join('') + '</tbody>'
      : '<tbody><tr><td>Todavía no se registraron errores.</td></tr></tbody>';
  }

  /* ---------- Conversaciones ---------- */
  function pintarSelector() {
    var sel = $('#selector-estudiante');
    var actual = sel.value;
    sel.innerHTML = '<option value="">Elegí un estudiante…</option>' + datos.estudiantes.map(function (f) {
      return '<option value="' + esc(f.id) + '">' + esc(f.id) + (f.turnos ? ' · ' + f.turnos + ' turnos' : ' · sin actividad') + '</option>';
    }).join('');
    sel.value = actual;
  }

  function chipsMeta(meta) {
    if (!meta) return '<div class="meta-docente"><span class="m-sin">sin metadato</span></div>';
    var chips = [];
    chips.push('<span>' + esc(meta.ejercicio || 'sin ejercicio') + '</span>');
    chips.push('<span' + (meta.tipo_pedido === 'respuesta' ? ' class="m-respuesta"' : '') + '>' + esc(PEDIDOS[meta.tipo_pedido] || meta.tipo_pedido) + '</span>');
    if (meta.escalon) chips.push('<span>pista ' + esc(meta.escalon) + '</span>');
    if (meta.error_detectado) chips.push('<span class="m-error" title="' + esc(ERRORES[meta.error_detectado] || '') + '">' + esc(meta.error_detectado) + '</span>');
    var clase = meta.estado === 'trabado' ? 'm-trabado' : meta.estado === 'resuelto_por_estudiante' ? 'm-resuelto' : '';
    chips.push('<span' + (clase ? ' class="' + clase + '"' : '') + '>' + esc(ESTADOS[meta.estado] || meta.estado) + '</span>');
    return '<div class="meta-docente">' + chips.join('') + '</div>';
  }

  function verConversacion(id) {
    pestana('conversaciones');
    var sel = $('#selector-estudiante');
    sel.value = id;
    var cont = $('#conversacion');
    if (!id) { cont.innerHTML = ''; return; }
    cont.innerHTML = '<p class="vacio">Cargando…</p>';
    pedirJson('/api/metricas/conversacion/' + encodeURIComponent(id)).then(function (c) {
      if (sel.value !== id) return;
      if (!c.sesiones.length) { cont.innerHTML = '<p class="vacio">' + esc(id) + ' todavía no entró al tutor.</p>'; return; }
      cont.innerHTML = c.sesiones.slice().reverse().map(function (s) {
        var msgs = s.mensajes.length ? s.mensajes.map(function (m) {
          var tutor = m.rol === 'assistant';
          return '<div class="msg ' + (tutor ? 'msg-tutor' : 'msg-vos') + (m.pista ? ' msg-pista' : '') + '">' +
            '<div class="msg-quien">' + (tutor ? 'Tutor' : esc(c.id)) + '<span class="msg-hora">' + esc(m.creado.slice(11)) + '</span></div>' +
            '<div class="msg-texto">' + renderizar(m.texto) + '</div>' + (tutor ? chipsMeta(m.meta) : '') + '</div>';
        }).join('') : '<p class="vacio">Entró pero no escribió.</p>';
        return '<section class="sesion"><div class="sesion-cabecera"><strong>Sesión del ' + esc(s.inicio) + '</strong>' +
          '<span>' + esc(minutos(s.minutos)) + '</span><span>' + s.turnos + ' turnos</span><span>' + esc(s.dispositivo) + '</span></div>' +
          '<div class="mensajes">' + msgs + '</div></section>';
      }).join('');
    }).catch(function (err) {
      if (err.status === 401) irAClave(err.message);
      else cont.innerHTML = '<p class="aviso">' + esc(err.message) + '</p>';
    });
  }

  /* ---------- CSV ---------- */
  function descargar(tabla, boton) {
    boton.disabled = true;
    pedir('/api/metricas/csv/' + encodeURIComponent(tabla)).then(function (r) {
      var disp = r.headers.get('Content-Disposition') || '';
      var m = /filename="([^"]+)"/.exec(disp);
      return r.blob().then(function (b) {
        var a = document.createElement('a');
        a.href = URL.createObjectURL(b);
        a.download = m ? m[1] : 'tutor-' + tabla + '.csv';
        document.body.appendChild(a);
        a.click();
        setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
      });
    }).catch(function (err) {
      if (err.status === 401) irAClave(err.message); else avisar(err.message);
    }).then(function () { boton.disabled = false; });
  }

  /* ---------- carga ---------- */
  function cargar() {
    avisar('');
    return pedirJson('/api/metricas').then(function (d) {
      datos = d;
      mostrar('panel');
      $('#generado').textContent = d.generado;
      pintarCurso();
      pintarEstudiantes();
      pintarEjercicios();
      pintarSelector();
      var sel = $('#selector-estudiante').value;
      if (sel && !$('[data-hoja="conversaciones"]').hidden) verConversacion(sel);
    }).catch(function (err) {
      if (err.status === 401 || err.status === 503 || err.status === 429) irAClave(err.message);
      else { mostrar('panel'); avisar(err.message); }
    });
  }

  $('#form-clave').addEventListener('submit', function (e) {
    e.preventDefault();
    var v = $('#campo-clave').value;
    if (!v) { irAClave('Escribí la clave.'); return; }
    clave = v;
    escribir(v);
    $('#campo-clave').value = '';
    var b = $('#boton-clave');
    b.disabled = true;
    cargar().then(function () { b.disabled = false; });
  });

  document.addEventListener('click', function (e) {
    var t = e.target.closest('[data-pestana],[data-accion],[data-ver],[data-csv],th[data-col]');
    if (!t) return;
    if (t.dataset.pestana) pestana(t.dataset.pestana);
    else if (t.dataset.accion === 'actualizar') cargar();
    else if (t.dataset.accion === 'salir') irAClave();
    else if (t.dataset.ver) verConversacion(t.dataset.ver);
    else if (t.dataset.csv) descargar(t.dataset.csv, t);
    else if (t.dataset.col) {
      orden = { col: t.dataset.col, dir: orden.col === t.dataset.col ? -orden.dir : (t.dataset.col === 'id' ? 1 : -1) };
      pintarEstudiantes();
    }
  });
  $('#selector-estudiante').addEventListener('change', function (e) { verConversacion(e.target.value); });

  if (clave) cargar(); else mostrar('clave');

  window.__panel = { renderizar: renderizar };
})();
