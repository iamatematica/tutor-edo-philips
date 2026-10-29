"""Base SQLite del tutor (archivo datos/tutor.db, fuera del repo).

Tablas, tal como las fija CLAUDE.md:
- estudiantes(id 'EST-NN', codigo_hash)
- sesiones(id, estudiante, inicio, ultima_actividad, dispositivo): una sesión se
  abre en el login y se da por cerrada tras 20 minutos sin mensajes.
- mensajes(id, sesion, estudiante, rol, texto, meta_json, creado): en los del
  tutor, meta_json es el bloque <meta> ya validado (o NULL si no vino o no valida).

Nada más se guarda: ni nombres, ni direcciones IP, ni qué hace el alumno fuera del chat.
Las fechas van en UTC con formato ISO 8601.
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
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante       TEXT NOT NULL REFERENCES estudiantes(id),
    inicio           TEXT NOT NULL,
    ultima_actividad TEXT NOT NULL,
    dispositivo      TEXT NOT NULL CHECK (dispositivo IN ('celular', 'computadora'))
);

CREATE TABLE IF NOT EXISTS mensajes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion     INTEGER NOT NULL REFERENCES sesiones(id),
    estudiante TEXT NOT NULL REFERENCES estudiantes(id),
    rol        TEXT NOT NULL CHECK (rol IN ('user', 'assistant')),
    texto      TEXT NOT NULL,
    meta_json  TEXT,
    creado     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS sesiones_estudiante ON sesiones(estudiante, id);
CREATE INDEX IF NOT EXISTS mensajes_estudiante ON mensajes(estudiante, id);
CREATE INDEX IF NOT EXISTS mensajes_sesion ON mensajes(sesion, id);
"""


def ahora() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


class BaseDatos:
    def __init__(self, ruta: Path):
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with self.conexion() as c:
            columnas = {f["name"] for f in c.execute("PRAGMA table_info(sesiones)")}
            if columnas and "estudiante" not in columnas:
                raise RuntimeError(
                    f"{self.ruta} tiene el esquema anterior al contrato del 29/10 (sesiones sin 'estudiante'). "
                    "Si es una base de prueba, borrala; si tiene datos reales, hay que migrarla."
                )
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

    def abrir_sesion(self, est_id: str, dispositivo: str, cuando: datetime | None = None) -> int:
        t = iso(cuando or ahora())
        with self.conexion() as c:
            cur = c.execute(
                "INSERT INTO sesiones(estudiante, inicio, ultima_actividad, dispositivo) VALUES (?, ?, ?, ?)",
                (est_id, t, t, dispositivo),
            )
            return cur.lastrowid

    def sesion_activa(self, est_id: str, minutos: int, cuando: datetime | None = None) -> sqlite3.Row | None:
        """La última sesión del estudiante, si tuvo actividad en los últimos `minutos`."""
        limite = iso((cuando or ahora()) - timedelta(minutes=minutos))
        with self.conexion() as c:
            return c.execute(
                "SELECT * FROM sesiones WHERE estudiante = ? AND ultima_actividad >= ? ORDER BY id DESC LIMIT 1",
                (est_id, limite),
            ).fetchone()

    def sesiones(self, est_id: str) -> list[sqlite3.Row]:
        with self.conexion() as c:
            return c.execute("SELECT * FROM sesiones WHERE estudiante = ? ORDER BY id", (est_id,)).fetchall()

    # ---------- mensajes ----------

    def guardar_turno(self, sesion: int, est_id: str, texto_estudiante: str, texto_tutor: str,
                      meta_json: str | None, cuando: datetime | None = None) -> None:
        """Guarda juntos el mensaje del estudiante y la respuesta del tutor, y actualiza la sesión.

        Van en la misma transacción para que el historial siempre alterne
        estudiante / tutor: si la llamada a Claude falla, no queda nada guardado.
        """
        t = iso(cuando or ahora())
        with self.conexion() as c:
            c.execute(
                "INSERT INTO mensajes(sesion, estudiante, rol, texto, creado) VALUES (?, ?, 'user', ?, ?)",
                (sesion, est_id, texto_estudiante, t),
            )
            c.execute(
                "INSERT INTO mensajes(sesion, estudiante, rol, texto, meta_json, creado) "
                "VALUES (?, ?, 'assistant', ?, ?, ?)",
                (sesion, est_id, texto_tutor, meta_json, t),
            )
            c.execute("UPDATE sesiones SET ultima_actividad = ? WHERE id = ?", (t, sesion))

    def mensajes(self, est_id: str) -> list[sqlite3.Row]:
        with self.conexion() as c:
            return c.execute("SELECT * FROM mensajes WHERE estudiante = ? ORDER BY id", (est_id,)).fetchall()

    def ultimos_de_sesion(self, sesion: int, limite: int) -> list[sqlite3.Row]:
        """Los últimos `limite` mensajes de la sesión, en orden cronológico."""
        with self.conexion() as c:
            return c.execute(
                "SELECT * FROM (SELECT * FROM mensajes WHERE sesion = ? ORDER BY id DESC LIMIT ?) ORDER BY id",
                (sesion, limite),
            ).fetchall()

    def ultimo_del_tutor(self, est_id: str) -> sqlite3.Row | None:
        with self.conexion() as c:
            return c.execute(
                "SELECT * FROM mensajes WHERE estudiante = ? AND rol = 'assistant' ORDER BY id DESC LIMIT 1",
                (est_id,),
            ).fetchone()

    def turnos_desde(self, est_id: str, desde: datetime) -> int:
        """Cantidad de turnos (mensajes del estudiante respondidos) desde un instante."""
        with self.conexion() as c:
            fila = c.execute(
                "SELECT COUNT(*) AS n FROM mensajes WHERE estudiante = ? AND rol = 'user' AND creado >= ?",
                (est_id, iso(desde)),
            ).fetchone()
        return fila["n"]
