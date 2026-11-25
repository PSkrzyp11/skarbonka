"""Tabele bazy danych i zmiany wprowadzane w starszych bazach."""

TABELE = (
    "osoby",
    "konta",
    "kategorie",
    "importy",
    "cykliczne",
    "transakcje",
    "budzety",
    "cele",
    "wplaty_celu",
    "reguly",
    "kursy",
)

SCHEMAT = """
CREATE TABLE IF NOT EXISTS osoby (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nazwa TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS konta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nazwa TEXT NOT NULL UNIQUE,
    typ TEXT NOT NULL,
    grosze_poczatkowe INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS kategorie (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nazwa TEXT NOT NULL UNIQUE,
    czy_wydatek INTEGER NOT NULL DEFAULT 1 CHECK (czy_wydatek IN (0, 1))
);
CREATE TABLE IF NOT EXISTS importy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plik TEXT NOT NULL,
    utworzono TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cykliczne (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nazwa TEXT NOT NULL,
    rodzaj TEXT NOT NULL CHECK (rodzaj IN ('wydatek', 'przychód')),
    grosze INTEGER NOT NULL CHECK (grosze > 0),
    konto_id INTEGER NOT NULL REFERENCES konta(id),
    kategoria_id INTEGER NOT NULL REFERENCES kategorie(id),
    start TEXT NOT NULL,
    czestotliwosc TEXT NOT NULL,
    ostatnia TEXT,
    aktywna INTEGER NOT NULL DEFAULT 1 CHECK (aktywna IN (0, 1))
);
CREATE TABLE IF NOT EXISTS transakcje (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rodzaj TEXT NOT NULL CHECK (rodzaj IN ('wydatek', 'przychód', 'przelew')),
    data TEXT NOT NULL,
    grosze INTEGER NOT NULL CHECK (grosze > 0),
    opis TEXT NOT NULL,
    konto_id INTEGER NOT NULL REFERENCES konta(id),
    konto_docelowe_id INTEGER REFERENCES konta(id),
    kategoria_id INTEGER REFERENCES kategorie(id),
    import_id INTEGER REFERENCES importy(id)
);
CREATE TABLE IF NOT EXISTS budzety (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kategoria_id INTEGER NOT NULL REFERENCES kategorie(id),
    miesiac TEXT NOT NULL,
    grosze INTEGER NOT NULL CHECK (grosze > 0),
    UNIQUE (kategoria_id, miesiac)
);
CREATE TABLE IF NOT EXISTS cele (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nazwa TEXT NOT NULL UNIQUE,
    grosze INTEGER NOT NULL CHECK (grosze > 0),
    termin TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS wplaty_celu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cel_id INTEGER NOT NULL REFERENCES cele(id) ON DELETE CASCADE,
    data TEXT NOT NULL,
    grosze INTEGER NOT NULL CHECK (grosze > 0)
);
CREATE TABLE IF NOT EXISTS reguly (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fraza TEXT NOT NULL,
    kategoria_id INTEGER NOT NULL REFERENCES kategorie(id),
    priorytet INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS kursy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    waluta TEXT NOT NULL,
    data TEXT NOT NULL,
    wartosc TEXT NOT NULL,
    UNIQUE (waluta, data)
);
CREATE INDEX IF NOT EXISTS transakcje_data ON transakcje(data);
"""

NOWE_KOLUMNY = (
    ("cykliczne", "osoba_id", "INTEGER REFERENCES osoby(id) ON DELETE CASCADE"),
    ("transakcje", "cykliczna_id", "INTEGER REFERENCES cykliczne(id) ON DELETE SET NULL"),
    ("transakcje", "waluta", "TEXT NOT NULL DEFAULT 'PLN'"),
    ("transakcje", "grosze_oryg", "INTEGER"),
)

BEZ_UNIKALNYCH_NAZW = """
PRAGMA foreign_keys = OFF;
BEGIN;
CREATE TABLE cykliczne_nowe (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nazwa TEXT NOT NULL,
    rodzaj TEXT NOT NULL CHECK (rodzaj IN ('wydatek', 'przychód')),
    grosze INTEGER NOT NULL CHECK (grosze > 0),
    konto_id INTEGER NOT NULL REFERENCES konta(id),
    kategoria_id INTEGER NOT NULL REFERENCES kategorie(id),
    start TEXT NOT NULL,
    czestotliwosc TEXT NOT NULL,
    ostatnia TEXT,
    aktywna INTEGER NOT NULL DEFAULT 1 CHECK (aktywna IN (0, 1))
);
INSERT INTO cykliczne_nowe SELECT * FROM cykliczne;
DROP TABLE cykliczne;
ALTER TABLE cykliczne_nowe RENAME TO cykliczne;
COMMIT;
"""
