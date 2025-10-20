# app.py

import mysql.connector
from flask import Flask, render_template, request
from collections import defaultdict

app = Flask(__name__)

# --- Configurazione del Database ---
# *** MODIFICA QUESTI VALORI CON I TUOI DATI REALI ***
DB_CONFIG = {
    'user': 'TUO_UTENTE',
    'password': 'TUA_PASSWORD',
    'host': '127.0.0.1',
    'database': 'TUO_DATABASE_LOTTO'
}

# --- Costanti per Analisi ---
SHORT_PERIOD_N = 50 # Numero di estrazioni per l'analisi del breve periodo

# --- Funzione di Connessione al DB ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Errore di connessione al DB: {err}")
        return None

# --- Logica di Analisi Statistica Avanzata ---
def analyze_lotto_data(ruota='Bari'):
    conn = get_db_connection()
    if not conn:
        return {"error": "Impossibile connettersi al database."}
    
    cursor = conn.cursor(dictionary=True)
    results = {}
    
    try:
        # 1. Estrai TUTTI i dati per la ruota selezionata, ordinati per data
        # Assumiamo che la tabella si chiami 'lotto_estrazioni'
        cursor.execute(f"""
            SELECT drawdate, value
            FROM lotto_estrazioni
            WHERE wheelname = %s
            ORDER BY drawdate DESC, seq ASC
        """, (ruota,))
        all_draws = cursor.fetchall()
        
        if not all_draws:
            return {"error": f"Nessun dato trovato per la ruota: {ruota}"}

        # 2. Preparazione dei Dati
        
        # Ottiene l'elenco degli ID estrazione unici e ordinati
        draw_ids = sorted(list(set(d['drawdate'] for d in all_draws)), reverse=True)
        
        last_date = draw_ids[0].strftime("%d/%m/%Y")
        
        frequency = defaultdict(int)
        ritardo_attuale = {}
        
        # Inizializzazione di tutti i numeri (1-90)
        for i in range(1, 91):
            ritardo_attuale[i] = len(draw_ids) 
            
        
        # 3. CALCOLO Frequenza Assoluta e Ritardo Attuale
        for i, draw_date in enumerate(draw_ids):
            # Ottieni i numeri estratti in questa data
            drawn_values = [d['value'] for d in all_draws if d['drawdate'] == draw_date]
            
            for num in drawn_values:
                frequency[num] += 1
                
                # Aggiorna il ritardo attuale SOLO la prima volta che lo incontri (l'estrazione più recente)
                if ritardo_attuale[num] == len(draw_ids): # Se è ancora al valore iniziale
                    ritardo_attuale[num] = i
        
        
        # 4. ANALISI DEL BREVE PERIODO (Ultime N Estrazioni)
        last_n_draw_ids = draw_ids[:SHORT_PERIOD_N]
        short_term_freq = defaultdict(int)
        
        for draw_date in last_n_draw_ids:
            drawn_values = [d['value'] for d in all_draws if d['drawdate'] == draw_date]
            for num in drawn_values:
                short_term_freq[num] += 1

        # Calcola la media di frequenza attesa per il breve periodo
        # Ci sono 5 numeri estratti per estrazione.
        expected_short_freq = (5 * SHORT_PERIOD_N) / 90 

        # I. HOT NUMBERS (Molto più frequenti della media)
        hot_numbers = {num: count for num, count in short_term_freq.items() if count > expected_short_freq * 1.5}
        top_hot = sorted(hot_numbers.items(), key=lambda item: item[1], reverse=True)[:5]

        # II. COLD NUMBERS (Molto meno frequenti della media)
        # Considera i numeri che sono usciti 0 o 1 volta nel breve periodo (e che non sono già ultra-ritardatari)
        cold_numbers = {num: count for num in range(1, 91) if short_term_freq[num] <= 1 and ritardo_attuale[num] < SHORT_PERIOD_N}
        top_cold = sorted(cold_numbers.items(), key=lambda item: item[1])[:5] # Ordina per frequenza crescente

        
        # 5. ANALISI DEI PATTERN (Sull'Ultima Estrazione)
        last_drawn_values = sorted([d['value'] for d in all_draws if d['drawdate'] == draw_ids[0]])
        
        gemelli = []
        consecutivi = []
        
        for num in last_drawn_values:
            # Numeri Gemelli (es. 11, 22, ...)
            if num % 11 == 0 and num > 10:
                gemelli.append(num)
                
            # Numeri Simmetrici (es. 1-90, 45-46) - Analisi complessa per il Lotto a 5. Ci concentriamo su Gemelli/Consecutivi.

        # Numeri Consecutivi (es. 12-13)
        for i in range(len(last_drawn_values) - 1):
            if last_drawn_values[i+1] == last_drawn_values[i] + 1:
                consecutivi.append(f"{last_drawn_values[i]}-{last_drawn_values[i+1]}")


        # 6. Preparazione Risultati
        
        results = {
            "ruota": ruota,
            "ultima_estrazione": last_date,
            "frequenti_assoluti": sorted(frequency.items(), key=lambda item: item[1], reverse=True)[:5],
            "ritardatari_attuali": sorted(ritardo_attuale.items(), key=lambda item: item[1], reverse=True)[:5],
            "hot_numbers": top_hot,
            "cold_numbers": top_cold,
            "pattern_ultima": {
                "gemelli": gemelli,
                "consecutivi": list(set(consecutivi))
            }
        }
        
    except Exception as e:
        results = {"error": f"Errore durante l'analisi: {e}"}
        
    finally:
        cursor.close()
        conn.close()
        
    return results

# --- Rotte Flask ---
@app.route('/', methods=['GET', 'POST'])
def index():
    ruote = ['Bari', 'Cagliari', 'Firenze', 'Genova', 'Milano', 'Napoli', 'Palermo', 'Roma', 'Torino', 'Venezia', 'Nazionale']
    analisi = None
    selected_ruota = 'Bari'
    
    if request.method == 'POST':
        selected_ruota = request.form.get('ruota')
        analisi = analyze_lotto_data(selected_ruota)
    
    return render_template('index.html', ruote=ruote, analisi=analisi, selected_ruota=selected_ruota)

if __name__ == '__main__':
    app.run(debug=True)
