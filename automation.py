import os
import sys

# 1. Point Playwright to the bundled browsers if running as an EXE
if getattr(sys, "frozen", False):
    # sys._MEIPASS is the temporary folder where PyInstaller extracts the EXE contents
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(sys._MEIPASS, "ms-playwright")

# 2. Dynamic config loading (as discussed previously)
import importlib.util
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

config_path = os.path.join(APP_DIR, "config.py")

if not os.path.exists(config_path):
    raise FileNotFoundError(f"config.py introuvable : {config_path}")

spec = importlib.util.spec_from_file_location("config", config_path)
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

DB_NAME = config.DB_NAME
DB_USER = config.DB_USER
DB_PASS = config.DB_PASS
DB_HOST = config.DB_HOST

# 3. Now import Playwright
from playwright.sync_api import sync_playwright
import psycopg2
from config import *
from playwright.sync_api import sync_playwright
import psycopg2

def type_input(page, selector, value):
    field = page.locator(selector)
    field.click()
    field.press("Control+A")
    field.press("Backspace")
    field.type(str(value), delay=1)

def run_playwright(date):

    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=5432,
        sslmode="require",
    )

    cur = conn.cursor()

    cur.execute("""
        SELECT date,debut,fin,classe,code,nom,motif,justifiee
        FROM absences
        WHERE date = %s
        ORDER BY classe, nom
    """, (date,))

    rows = cur.fetchall()

    print("ABSENCES:", rows)

    cur.close()
    conn.close()

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)

        page = browser.new_page()

        page.goto(
            "https://www.cpge.ac.ma/Intranet/Login.aspx?ReturnUrl=%2fIntranet%2fCPGEPages%2fAbsenceEleve.aspx"
        )

        page.fill("#txtUserNom", CODE)
        page.fill("#txtPassword", MDP)

        page.click("#btnLogin")
        page.wait_for_load_state("networkidle")

        page.goto("https://www.cpge.ac.ma/Intranet/CPGEPages/AbsenceEleve.aspx")
        
        page.click("#ctl00_btnNew")
        page.wait_for_load_state("networkidle")

        page.locator("#ctl00_PlaceHolderMain_rblTypeAbsence_1").check()
        page.wait_for_load_state("networkidle")

        
        
        initi = True
        
        for i in rows:
            page.click("#ctl00_PlaceHolderMain_btnContinuer")
            page.wait_for_load_state("networkidle")
            page.fill("#ctl00_PlaceHolderMain_txtAbsenceEleveDateDebutDate", i[0].strftime("%d%m%Y"))
            type_input(page, "#ctl00_PlaceHolderMain_txtAbsenceEleveDateDebutHeure", i[1].strftime("%H%M"))
            type_input(page, "#ctl00_PlaceHolderMain_txtAbsenceEleveDateFinHeure", i[2].strftime("%H%M"))
            page.locator("#ctl00_PlaceHolderMain_ImgBtnPUAbsenceEleve_Id_EleveCNEEleve").click()
            page.locator("#ctl00_PopUpModal_PanelPopup").wait_for()
            page.locator("input[title='CodeElève']").fill(i[4])
            page.locator("#ctl00_PopUpModal_BtnPopUpFind").click()
            page.locator("#ctl00_PopUpModal_grdPUListe").wait_for()
            row = page.locator("#ctl00_PopUpModal_grdPUListe tr", has_text=i[4]).first
            row.locator("input[type='image']").click()
            page.locator("#ctl00_PopUpModal_PanelPopup").wait_for(state="hidden")
            duree = i[2].hour - i[1].hour
            page.locator("#ctl00_PlaceHolderMain_txtAbsenceEleveDureeAbsence").fill(str(duree))
            page.locator(
                "#ctl00_PlaceHolderMain_ddlAbsenceEleve_Id_MotifAbsenceMotifMotifAbsence"
            ).select_option(value=str(i[6]))
            page.locator(
                "#ctl00_PlaceHolderMain_ddlAbsenceEleveJustifiee"
            ).select_option(value="true" if i[7] else "false")
            page.locator("#ctl00_btnSave").click()
            page.locator("#ctl00_btnNew").wait_for(state="visible")
            page.locator("#ctl00_btnNew").click()


        page.wait_for_timeout(60000)
        browser.close()