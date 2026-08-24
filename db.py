import os
import sys
import importlib.util

import psycopg2

# Dossier de l'application
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Charger config.py depuis le même dossier que l'exécutable
config_path = os.path.join(APP_DIR, "config.py")

if not os.path.exists(config_path):
    raise FileNotFoundError(
        f"config.py introuvable : {config_path}"
    )

spec = importlib.util.spec_from_file_location("config", config_path)
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

DB_NAME = config.DB_NAME
DB_USER = config.DB_USER
DB_PASS = config.DB_PASS
DB_HOST = config.DB_HOST


def get_conn():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=5432,
        sslmode="require",
    )


def get_absences_by_date(date):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id,date,debut,fin,classe,code,nom,duree,motif,justifiee
                FROM absences WHERE date=%s ORDER BY classe, nom
            """, (date,))
            rows = cur.fetchall()
            result = []
            for r in rows:
                result.append({
                    "id": r[0], "date": str(r[1]), "debut": r[2].strftime("%H:%M"),
                    "fin": r[3].strftime("%H:%M"), "classe": r[4], "code": r[5],
                    "nom": r[6], "duree": r[7], "motif": r[8], "justifiee": r[9]
                })
            return result


def update_absences(rows):
    with get_conn() as conn:
        with conn.cursor() as cur:
            for r in rows:
                justifiee = r["justifiee"] == "true"
                cur.execute("UPDATE absences SET motif=%s, justifiee=%s WHERE id=%s",
                            (r["motif"], justifiee, r["id"]))
        conn.commit()

def delete_absences_bulk(ids):
    if not ids:
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM absences WHERE id = ANY(%s)", (ids,))
        conn.commit()


def get_eleves(search_query=""):
    with get_conn() as conn:
        with conn.cursor() as cur:
            if search_query:
                cur.execute("""
                    SELECT nom, classe, code FROM eleves 
                    WHERE nom ILIKE %s OR code ILIKE %s OR classe ILIKE %s 
                    ORDER BY classe, nom
                """, (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"))
            else:
                cur.execute("SELECT nom, classe, code FROM eleves ORDER BY classe, nom")
            return [{"nom": r[0], "classe": r[1], "code": r[2]} for r in cur.fetchall()]


def add_eleve(data):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM eleves WHERE code = %s", (data['code'],))
            student_exists = cur.fetchone()

            if student_exists:
                cur.execute("""
                    UPDATE eleves 
                    SET nom = %s, classe = %s 
                    WHERE code = %s
                """, (data['nom'], data['classe'], data['code']))
            else:
                cur.execute("""
                    INSERT INTO eleves (nom, classe, code) 
                    VALUES (%s, %s, %s)
                """, (data['nom'], data['classe'], data['code']))
        conn.commit()


def delete_eleves_bulk(codes):
    if not codes:
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM eleves WHERE code = ANY(%s)", (codes,))
        conn.commit()


def get_encadrants():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT mdp, classes, nom FROM encadrants ORDER BY nom")
            return [{"mdp": r[0], "classes": r[1], "nom": r[2]} for r in cur.fetchall()]


def add_encadrant(data):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO encadrants (mdp, classes, nom) VALUES (%s, %s, %s)",
                        (data['mdp'], data['classes'], data['nom']))
        conn.commit()


def delete_encadrant(nom):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM encadrants WHERE nom = %s", (nom,))
        conn.commit()