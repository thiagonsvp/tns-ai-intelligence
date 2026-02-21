import os
import re
import csv
import io
import time
from flask import Flask, request, jsonify, render_template, Response, redirect, url_for
from flask_cors import CORS
from playwright.sync_api import sync_playwright
import sqlite3

# Database setup
def init_db():
    conn = sqlite3.connect('history.db')
    c = conn.cursor()
    # Table for search headers
    c.execute('''CREATE TABLE IF NOT EXISTS searches
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  query TEXT, location TEXT, results_count INTEGER, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    # Table for lead details
    c.execute('''CREATE TABLE IF NOT EXISTS results
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  search_id INTEGER, name TEXT, phone TEXT, address TEXT, rating REAL, 
                  FOREIGN KEY(search_id) REFERENCES searches(id) ON DELETE CASCADE)''')
    
    # MIGRATION: Check for missing columns in results table
    c.execute("PRAGMA table_info(results)")
    columns = [row[1] for row in c.fetchall()]
    
    if 'website' not in columns:
        c.execute("ALTER TABLE results ADD COLUMN website TEXT")
    if 'maps_link' not in columns:
        c.execute("ALTER TABLE results ADD COLUMN maps_link TEXT")
    if 'instagram' not in columns:
        c.execute("ALTER TABLE results ADD COLUMN instagram TEXT")
        
    conn.commit()
    conn.close()

init_db()

app = Flask(__name__)
CORS(app)

# In-memory storage for the latest search results to support CSV export
last_search_results = []

def validate_brazilian_phone(phone):
    if not phone: return False
    clean_phone = re.sub(r'\D', '', phone)
    return 10 <= len(clean_phone) <= 13

def format_whatsapp_url(phone):
    clean_phone = re.sub(r'\D', '', phone)
    if not clean_phone.startswith('55') and len(clean_phone) <= 11:
        clean_phone = '55' + clean_phone
    return f"https://wa.me/{clean_phone}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/history')
def history_page():
    conn = sqlite3.connect('history.db')
    c = conn.cursor()
    c.execute("SELECT * FROM searches ORDER BY timestamp DESC")
    searches = c.fetchall()
    conn.close()
    return render_template('history.html', searches=searches)

@app.route('/history/view/<int:id>')
def view_leads(id):
    conn = sqlite3.connect('history.db')
    c = conn.cursor()
    c.execute("SELECT query, location FROM searches WHERE id = ?", (id,))
    search_info = c.fetchone()
    c.execute("SELECT name, phone, address, rating, website, maps_link, instagram FROM results WHERE search_id = ?", (id,))
    leads = []
    for row in c.fetchall():
        leads.append({
            "name": row[0],
            "phone": row[1],
            "address": row[2],
            "rating": row[3],
            "website": row[4],
            "maps_link": row[5],
            "instagram": row[6],
            "wa_url": format_whatsapp_url(row[1])
        })
    conn.close()
    return render_template('view_leads.html', leads=leads, info=search_info, search_id=id)

@app.route('/history/delete/<int:id>', methods=['POST'])
def delete_history(id):
    conn = sqlite3.connect('history.db')
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = ON")
    c.execute("DELETE FROM searches WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('history_page'))

def clean_txt(text):
    if not text: return ""
    # Remove non-printable characters but keep standard Portuguese/Latin characters
    # This strips things like Gmps icons (\u202d, \u202c, etc)
    return "".join(char for char in text if char.isprintable()).strip()

@app.route('/api/search', methods=['POST'])
def search():
    global last_search_results
    data = request.json
    location = data.get('location', '')
    query = data.get('query', '')

    print(f"DEBUG: TNS AI iniciando MINERAÇÃO EM MASSA (Meta: 200) para '{query}' em '{location}'...")
    
    search_term = f"{query} {location}"
    results_list = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            url = f"https://www.google.com/maps/search/{search_term.replace(' ', '+')}"
            page.goto(url, wait_until="load", timeout=90000)
            
            # Identify the results feed
            feed_selector = 'div[role="feed"]'
            try:
                page.wait_for_selector(feed_selector, timeout=15000)
            except:
                feed_selector = 'div[aria-label^="Resultados"]'

            seen_names = set()
            
            print("DEBUG: Carregando lista completa...")
            for s in range(35):
                page.hover(feed_selector)
                page.mouse.wheel(0, 5000)
                page.wait_for_timeout(1500)
                if "Você chegou ao fim da lista" in page.content(): break

            cards = page.locator('div[role="article"]').all()
            if not cards: cards = page.locator('a.hfpxzc').all()

            print(f"DEBUG: Processando {len(cards)} itens...")

            for i, card in enumerate(cards):
                if len(results_list) >= 210: break
                
                try:
                    card.scroll_into_view_if_needed()
                    
                    # Core card info
                    card_title_el = card.locator('div.fontHeadlineSmall').first
                    raw_card_name = card_title_el.inner_text().strip() if card_title_el.count() > 0 else "N/A"
                    card_name = clean_txt(raw_card_name)
                    
                    if card_name in seen_names or card_name == "N/A": continue

                    # Click and wait for TRUE update
                    card.click()
                    page.wait_for_timeout(3000) # Robust wait for side-panel
                    
                    details = page.locator('div[role="main"]').first
                    if details.count() == 0: continue
                    
                    # Name Check
                    panel_name_el = page.locator('h1.DUwDvf').first
                    panel_name = clean_txt(panel_name_el.inner_text()) if panel_name_el.count() > 0 else ""
                    
                    if card_name not in panel_name and panel_name not in card_name:
                        page.wait_for_timeout(2000)
                        panel_name = clean_txt(panel_name_el.inner_text())
                        if card_name not in panel_name and panel_name not in card_name:
                            continue

                    panel_text = details.inner_text()
                    
                    # Phone
                    phone = "N/A"
                    p_btn = page.locator('button[data-item-id*="phone"]').first
                    if p_btn.count() > 0:
                        phone = clean_txt(p_btn.inner_text())
                    else:
                        phone_match = re.search(r'(\+55\s?)?(\(?\d{2}\)?\s?)?(\d{4,5}[-\s]?\d{4})', panel_text)
                        if phone_match: phone = clean_txt(phone_match.group(0))

                    # Address
                    address = "Consultar no Maps"
                    a_btn = page.locator('button[data-item-id="address"]').first
                    if a_btn.count() > 0: address = clean_txt(a_btn.inner_text())

                    # Rating
                    rating = 0.0
                    rating_el = page.locator('div.F7nice span span').first
                    if rating_el.count() > 0:
                        try:
                            rating = float(rating_el.inner_text().replace(',', '.'))
                        except: pass

                    # Website & Instagram detector
                    website = "N/A"
                    instagram = "N/A"
                    w_btn = page.locator('a[data-item-id="authority"]').first
                    if w_btn.count() > 0:
                        website = w_btn.get_attribute('href')
                        if website and "instagram.com" in website: 
                            instagram = website
                        
                    maps_link = page.url

                    if phone != "N/A" and validate_brazilian_phone(phone):
                        seen_names.add(card_name)
                        results_list.append({
                            "name": card_name,
                            "phone": phone,
                            "address": address,
                            "rating": rating,
                            "website": website,
                            "instagram": instagram,
                            "maps_link": maps_link,
                            "wa_url": format_whatsapp_url(phone)
                        })
                        if len(results_list) % 5 == 0:
                            print(f"DEBUG: [SAVE] {len(results_list)} leads extraídos.")
                except Exception as e:
                    print(f"DEBUG: Erro no lead {i}: {e}")
                    continue

            browser.close()

        # DB persistence
        conn = sqlite3.connect('history.db')
        c = conn.cursor()
        c.execute("INSERT INTO searches (query, location, results_count) VALUES (?, ?, ?)", 
                  (query, location, len(results_list)))
        sid = c.lastrowid
        for r in results_list:
            c.execute("INSERT INTO results (search_id, name, phone, address, rating, website, maps_link, instagram) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (sid, r['name'], r['phone'], r['address'], r['rating'], r['website'], r['maps_link'], r['instagram']))
        conn.commit()
        conn.close()

        last_search_results = results_list
        return jsonify(results_list)

    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/export/<int:sid>')
def export_specific(sid):
    conn = sqlite3.connect('history.db')
    c = conn.cursor()
    c.execute("SELECT name, phone, address, rating, website, maps_link, instagram FROM results WHERE search_id = ?", (sid,))
    data = c.fetchall()
    conn.close()
    
    output = io.StringIO()
    # Using 'utf-8-sig' and semicolon as delimiter for perfect Excel compatibility
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_ALL)
    writer.writerow(["nome", "telefone", "endereco", "nota", "site", "maps", "instagram"])
    writer.writerows(data)
    
    # Prepend BOM for Excel UTF-8 recognition
    content = '\ufeff' + output.getvalue()
    return Response(
        content,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=leads_id_{sid}.csv"}
    )

@app.route('/api/export/merged')
def export_merged():
    conn = sqlite3.connect('history.db')
    c = conn.cursor()
    # Unique across names+phones
    c.execute("SELECT DISTINCT name, phone, address, rating, website, maps_link, instagram FROM results")
    data = c.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_ALL)
    writer.writerow(["nome", "telefone", "endereco", "nota", "site", "maps", "instagram"])
    writer.writerows(data)
    
    content = '\ufeff' + output.getvalue()
    return Response(
        content,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=leads_mesclados_premium.csv"}
    )

@app.route('/api/export', methods=['GET'])
def export_last():
    if not last_search_results: return jsonify({"error": "Nada encontrado"}), 400
    output = io.StringIO()
    fieldnames = ["name", "phone", "address", "rating", "website", "maps_link", "instagram"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=';', quoting=csv.QUOTE_ALL)
    writer.writeheader()
    
    # Filter only relevant fields for dict writer
    rows = []
    for r in last_search_results:
        rows.append({k: r[k] for k in fieldnames})
    writer.writerows(rows)
    
    content = '\ufeff' + output.getvalue()
    return Response(
        content,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=extracao_atual.csv"}
    )

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
