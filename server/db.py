"""Base SQLite del tutor (archivo datos/tutor.db, fuera del repo).

Tablas:
- estudiantes(id 'EST-NN', codigo_hash)
- sesiones(token_hash, estudiante_id, creada, expira)
- mensajes: cada turno del estudiante y del tutor. En los del tutor se guarda el
  bloque <meta> completo (meta_json) y sus campos por separado para el panel docente.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

ESQUEMA = """
CREATE TABLE IF NOT EXISTS estudiantes (
    id          TEXT PRIMARY KEY,
    codigo_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sesiones (
    token_hash    TEXT PRIMARY KEY,
    estudiante_id TEXT NOT NULL REFERENCES estudiantes(id),
    creada        TEXT NOT NULL,
    expira        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mensajes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante_id   TEXT NOT NULL REFERENCES estudiantes(id),
    rol             TEXT NOT NULL CHECK (rol IN ('user', 'assistant')),
    texto           TEXT NOT NULL,
    es_pista        INTEGER NOT NULL DEFAULT 0,
    -- solo en mensajes del tutor:
    texto_crudo     TEXT,
    meta_json       TEXT,
    meta_valido     INTEGER,
    ejercicio       TEXT,
    tipo_pedido     TEXT,
    escalon         INTEGER,
    error_detectado TEXT,
    estado          TEXT,
    modelo          TEXT,
    creado          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS mensajes_estudiante ON mensajes(estudiante_id, id);
"""


def ahora() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


class BaseDatos:
    def __init__(self, ruta: Path):
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with self.conexion() as c:
            c.executescript(ESQUEMA)

    @contextmanager
    def conexion(self) -> Iterator[sqlite3.Connection]:
        c = sqlite3.connect(self.ruta, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    # ---------- estudiantes ----------

    def guardar_estudiante(self, est_id: str, codigo_hash: str) -> None:
        with self.conexion() as c:
            c.execute(
                "INSERT INTO estudiantes(id, codigo_hash) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET codigo_hash = excluded.codigo_hash",
                (est_id, codigo_hash),
            )

    def codigo_hash(self, est_id: str) -> str | None:
        with self.conexion() as c:
            fila = c.execute("SELECT codigo_hash FROM estudiantes WHERE id = ?", (est_id,)).fetchone()
        return fila["codigo_hash"] if fila else None

    def ids_estudiantes(self) -> list[str]:
        with self.conexion() as c:
            return [f["id"] for f in c.execute("SELECT id FROM estudiantes ORDER BY id")]

    # ---------- sesiones ----------

    def crear_sesion(self, token_hash: str, est_id: str, horas: int) -> None:
        t = ahora()
        with self.conexion() as c:
            c.execute("DELETE FROM sesiones WHERE expira < ?", (iso(t),))
            c.execute(
                "INSERT INTO sesiones(token_hash, estudiante_id, creada, expira) VALUES (?, ?, ?, ?)",
                (token_hash, est_id, iso(t), iso(t + timedelta(hours=horas))),
            )

    def estudiante_de_sesion(self, token_hash: str) -> str | None:
        with self.conexion() as c:
            fila = c.execute(
                "SELECT estudiante_id FROM sesiones WHERE token_hash = ? AND expira >= ?",
                (token_hash, iso(ahora())),
            ).fetchone()
        return fila["estudiante_id"] if fila else None

    def cerrar_sesion(self, token_hash: str) -> None:
        with self.conexion() as c:
            c.execute("DELETE FROM sesiones WHERE token_hash = ?", (token_hash,))

    # ---------- mensajes ----------

    def guardar_turno(self, est_id: str, texto_estudiante: str, es_pista: bool, tutor: dict) -> None:
        """Guarda juntos el mensaje del estudiante y la respuesta del tutor.

        Se escriben en la misma transacción para que el historial siempre alterne
        estudiante / tutor: si la llamada a Claude falla, no queda nada guardado.
        """
        t = iso(ahora())
        meta = tutor.get("meta") or {}
        with self.conexion() as c:
            c.execute(
                "INSERT INTO mensajes(estudiante_id, rol, texto, es_pista, creado) VALUES (?, 'user', ?, ?, ?)",
                (est_id, texto_estudiante, int(es_pista), t),
            )
            c.execute(
                """INSERT INTO mensajes(estudiante_id, rol, texto, texto_crudo, meta_json, meta_valido,
                       ejercicio, tipo_pedido, escalon, error_detectado, estado, modelo, creado)
                   VALUES (?, 'assistant', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    est_id,
                    tutor["texto"],
                    tutor.get("texto_crudo"),
                    tutor.get("meta_json"),
                    int(bool(tutor.get("meta_valido"))),
                    meta.get("ejercicio"),
                    meta.get("tipo_pedido"),
                    meta.get("escalon"),
                    meta.get("error_detectado"),
                    meta.get("estado"),
                    tutor.get("modelo"),
                    t,
                ),
            )

    def mensajes(self, est_id: str, limite: int | None = None) -> list[sqlite3.Row]:
        with self.conexion() as c:
            if limite:
                filas = c.execute(
                    "SELECT * FROM (SELECT * FROM mensajes WHERE estudiante_id = ? ORDER BY id DESC LIMIT ?) "
                    "ORDER BY id",
                    (est_id, limite),
                ).fetchall()
            else:
                filas = c.execute(
                    "SELECT * FROM mensajes WHERE estudiante_id = ? ORDER BY id", (est_id,)
                ).fetchall()
        return filas

    def ultimo_del_tutor(self, est_id: str) -> sqlite3.Row | None:
        with self.conexion() as c:
            return c.execute(
                "SELECT * FROM mensajes WHERE estudiante_id = ? AND rol = 'assistant' ORDER BY id DESC LIMIT 1",
                (est_id,),
            ).fetchone()
