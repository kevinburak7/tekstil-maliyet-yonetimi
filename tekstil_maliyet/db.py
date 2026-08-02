"""SQLite veri erişimi."""
import sqlite3

from tekstil_maliyet import constants
from tekstil_maliyet.hesaplama import ValidationError


class Veritabani:
    def __init__(self):
        self.conn = sqlite3.connect(constants.DB_YOLU)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.conn.cursor()
        self.tablo_olustur()

    def tablo_olustur(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS receteler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tur TEXT,
                isim TEXT,
                parametre REAL,
                fire_orani REAL DEFAULT 1.2,
                tarih DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS icerikler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recete_id INTEGER,
                ad TEXT,
                miktar REAL,
                birim TEXT,
                fiyat REAL,
                para TEXT,
                FOREIGN KEY(recete_id) REFERENCES receteler(id) ON DELETE CASCADE
            )
        """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS katalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad TEXT NOT NULL UNIQUE,
                birim TEXT DEFAULT 'g/l',
                fiyat REAL NOT NULL,
                para TEXT DEFAULT 'TL',
                aktif INTEGER DEFAULT 1,
                tarih DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        self._migrate_fire_orani()
        self.conn.commit()

    def _migrate_fire_orani(self):
        cols = {
            row[1]
            for row in self.cursor.execute("PRAGMA table_info(receteler)").fetchall()
        }
        if "fire_orani" not in cols:
            self.cursor.execute(
                f"ALTER TABLE receteler ADD COLUMN fire_orani REAL DEFAULT {constants.FIRE_ORANI_VARSAYILAN}"
            )

    def _icerik_ekle(self, recete_id, icerik_listesi):
        for item in icerik_listesi:
            self.cursor.execute(
                """
                INSERT INTO icerikler (recete_id, ad, miktar, birim, fiyat, para)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    recete_id,
                    item["ad"],
                    item["miktar"],
                    item["birim"],
                    item["fiyat"],
                    item["para"],
                ),
            )

    def _icerik_getir(self, recete_id):
        self.cursor.execute(
            "SELECT ad, miktar, birim, fiyat, para FROM icerikler WHERE recete_id=?",
            (recete_id,),
        )
        return [
            {
                "ad": i[0],
                "miktar": i[1],
                "birim": i[2],
                "fiyat": i[3],
                "para": i[4],
            }
            for i in self.cursor.fetchall()
        ]

    def kaydet(self, tur, isim, parametre, icerik_listesi, fire_orani=constants.FIRE_ORANI_VARSAYILAN):
        self.cursor.execute(
            "INSERT INTO receteler (tur, isim, parametre, fire_orani) VALUES (?, ?, ?, ?)",
            (tur, isim, parametre, fire_orani),
        )
        recete_id = self.cursor.lastrowid
        self._icerik_ekle(recete_id, icerik_listesi)
        self.conn.commit()
        return recete_id

    def guncelle(
        self,
        recete_id,
        tur,
        isim,
        parametre,
        icerik_listesi,
        fire_orani=constants.FIRE_ORANI_VARSAYILAN,
    ):
        self.cursor.execute(
            """
            UPDATE receteler
            SET tur=?, isim=?, parametre=?, fire_orani=?, tarih=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (tur, isim, parametre, fire_orani, recete_id),
        )
        if self.cursor.rowcount == 0:
            return False
        self.cursor.execute("DELETE FROM icerikler WHERE recete_id=?", (recete_id,))
        self._icerik_ekle(recete_id, icerik_listesi)
        self.conn.commit()
        return True

    def getir_hepsi(self):
        veriler = []
        self.cursor.execute(
            "SELECT id, tur, isim, parametre, tarih, fire_orani FROM receteler ORDER BY id DESC"
        )
        for r_id, r_tur, r_isim, r_param, r_tarih, r_fire in self.cursor.fetchall():
            veriler.append(
                {
                    "id": r_id,
                    "tur": r_tur,
                    "isim": r_isim,
                    "parametre": r_param,
                    "tarih": r_tarih or "",
                    "fire_orani": (
                        float(r_fire)
                        if r_fire is not None
                        else constants.FIRE_ORANI_VARSAYILAN
                    ),
                    "icerik": self._icerik_getir(r_id),
                }
            )
        return veriler

    def getir_by_id(self, recete_id):
        self.cursor.execute(
            "SELECT id, tur, isim, parametre, tarih, fire_orani FROM receteler WHERE id=?",
            (recete_id,),
        )
        row = self.cursor.fetchone()
        if not row:
            return None
        r_id, r_tur, r_isim, r_param, r_tarih, r_fire = row
        return {
            "id": r_id,
            "tur": r_tur,
            "isim": r_isim,
            "parametre": r_param,
            "tarih": r_tarih or "",
            "fire_orani": (
                float(r_fire) if r_fire is not None else constants.FIRE_ORANI_VARSAYILAN
            ),
            "icerik": self._icerik_getir(r_id),
        }

    def son_id_by_isim(self, tur, isim):
        self.cursor.execute(
            "SELECT id FROM receteler WHERE tur=? AND isim=? ORDER BY id DESC LIMIT 1",
            (tur, isim),
        )
        row = self.cursor.fetchone()
        return row[0] if row else None

    def sil_by_id(self, recete_id):
        self.cursor.execute("DELETE FROM icerikler WHERE recete_id=?", (recete_id,))
        self.cursor.execute("DELETE FROM receteler WHERE id=?", (recete_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    # --- Kimyasal kataloğu ---

    def katalog_listele(self, sadece_aktif=True):
        if sadece_aktif:
            self.cursor.execute(
                """
                SELECT id, ad, birim, fiyat, para, aktif
                FROM katalog WHERE aktif=1 ORDER BY ad COLLATE NOCASE
                """
            )
        else:
            self.cursor.execute(
                """
                SELECT id, ad, birim, fiyat, para, aktif
                FROM katalog ORDER BY ad COLLATE NOCASE
                """
            )
        return [
            {
                "id": r[0],
                "ad": r[1],
                "birim": r[2],
                "fiyat": r[3],
                "para": r[4],
                "aktif": bool(r[5]),
            }
            for r in self.cursor.fetchall()
        ]

    def katalog_ekle(self, ad, birim, fiyat, para):
        ad = ad.strip()
        if not ad:
            raise ValidationError("Ürün adı zorunludur.")
        self.cursor.execute(
            """
            INSERT INTO katalog (ad, birim, fiyat, para, aktif)
            VALUES (?, ?, ?, ?, 1)
            """,
            (ad, birim, fiyat, para),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def katalog_guncelle(self, urun_id, ad, birim, fiyat, para, aktif=True):
        ad = ad.strip()
        if not ad:
            raise ValidationError("Ürün adı zorunludur.")
        self.cursor.execute(
            """
            UPDATE katalog
            SET ad=?, birim=?, fiyat=?, para=?, aktif=?, tarih=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (ad, birim, fiyat, para, 1 if aktif else 0, urun_id),
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    def katalog_sil(self, urun_id):
        self.cursor.execute("DELETE FROM katalog WHERE id=?", (urun_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def katalog_getir_by_ad(self, ad):
        self.cursor.execute(
            "SELECT id, ad, birim, fiyat, para, aktif FROM katalog WHERE ad=? COLLATE NOCASE",
            (ad.strip(),),
        )
        row = self.cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "ad": row[1],
            "birim": row[2],
            "fiyat": row[3],
            "para": row[4],
            "aktif": bool(row[5]),
        }


