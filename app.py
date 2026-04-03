import os
import sqlite3
import json
import urllib.request
import urllib.error
import time

import pkgutil
import importlib.util
import sys

# Maintain Python 3.14+ compatibility
if not hasattr(pkgutil, 'get_loader'):
    def _get_loader(name):
        try:
            if name == '__main__':
                return getattr(sys.modules.get(name, None), '__loader__', None)
            spec = importlib.util.find_spec(name)
            if spec is None:
                return None
            return spec.loader
        except Exception:
            return None
    pkgutil.get_loader = _get_loader

from flask import Flask, g, render_template, request, jsonify

app = Flask(__name__)
DATABASE = os.path.join(os.path.dirname(__file__), 'emotions.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.execute('DROP TABLE IF EXISTS emotions')
    db.execute(
        '''
        CREATE TABLE emotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            text TEXT,
            emotion TEXT,
            score REAL,
            reasoning TEXT
        )
        '''
    )
    db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# ---------- Hybrid AI Analyzer System ----------
class HybridEmotionAnalyzer:
    """
    Primary Goal: ALWAYS use real AI (no rule-based fallback).
    
    Mode 1 (Local): Attempts to connect to Ollama running locally. 
    Mode 2 (Cloud): If Ollama is offline or times out, it switches instantly 
                    to a FREE public Hugging Face AI API endpoint.
    """
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.ollama_model = "gemma:2b"
        
        # Free public API for an emotion classification model
        self.hf_url = "https://api-inference.huggingface.co/models/j-hartmann/emotion-english-distilroberta-base"

    def analyze_emotion(self, text):
        """Clean function that tries local Ollama first, then falls back to HF Cloud"""
        try:
            print("[info] Attempting Mode 1: Local Ollama Model...")
            return self._call_ollama(text)
        except Exception as e:
            print(f"[warning] Ollama failed ({e}). Switching to Mode 2: Hugging Face API...")
            try:
                return self._call_huggingface(text)
            except Exception as hf_e:
                print(f"[error] Both AI models failed. Last error: {hf_e}")
                raise Exception("Outage: Both offline and online AI algorithms are currently unreachable.")

    def _call_ollama(self, text):
        prompt = (
            "Analyze the sentiment of the following text. "
            "Respond ONLY with a valid JSON object in this exact format: "
            '{"emotion": "<choose exactly one: happy, sad, anger, fear, surprise, neutral>", '
            '"score": <a number from 0 to 100 representing confidence>, '
            '"reasoning": "<1 short sentence explaining why>"}\n\n'
            f"Text: \"{text}\""
        )
        
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        req = urllib.request.Request(self.ollama_url, data=json.dumps(payload).encode('utf-8'), 
                                     headers={'Content-Type': 'application/json'})
                                     
        # Time out relatively quickly (3 seconds) to ensure user isn't kept waiting if it's down!
        with urllib.request.urlopen(req, timeout=4) as response:
            result = json.loads(response.read().decode('utf-8'))
            
        llm_text = result.get('response', '{}').strip()
        if llm_text.startswith('```json'): llm_text = llm_text[7:]
        if llm_text.endswith('```'): llm_text = llm_text[:-3]
        
        parsed = json.loads(llm_text)
        emotion = self._normalize_emotion(parsed.get("emotion", "neutral"))
        
        score_raw = parsed.get("score", 0.0)
        score = float(str(score_raw).replace('%', ''))
        if score <= 1.0 and score > 0.0: score = score * 100
            
        return emotion, round(score, 1), parsed.get("reasoning", "Processed via Local LLM.")

    def _call_huggingface(self, text):
        hf_token = os.environ.get("HF_TOKEN")
        
        if not hf_token or hf_token.strip() == "":
            return "neutral", 0.0, "(Offline) Hugging Face token not configured. Please set HF_TOKEN environment variable."
            
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {hf_token}"
        }
            
        payload = {"inputs": text}
        hf_url = "https://router.huggingface.co/hf-inference/models/j-hartmann/emotion-english-distilroberta-base"
        req = urllib.request.Request(hf_url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                results = json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 401 or e.code == 403:
                # App will not crash! It returns a safe fallback message to the frontend UI!
                return "neutral", 0.0, "(Offline) HuggingFace Fallback blocked: You must add your free HF API Token inside app.py to use Cloud AI!"
            elif e.code == 503:
                return "neutral", 0.0, "(Offline) HuggingFace model is currently loading on their servers. Try again in 20 seconds!"
            else:
                return "neutral", 0.0, f"(Offline) Cloud API Error {e.code}"
        except Exception:
             return "neutral", 0.0, "(Offline) Failed to connect to any Cloud AI services."
            
        # Parse the HF response if successful
        if isinstance(results, list) and len(results) > 0 and isinstance(results[0], list):
            predictions = results[0]
        elif isinstance(results, list) and len(results) > 0 and isinstance(results[0], dict):
            predictions = results
        else:
            predictions = [{"label": "neutral", "score": 0.5}]
            
        best_prediction = max(predictions, key=lambda x: x.get('score', 0))
        emotion = self._normalize_emotion(best_prediction.get('label', 'neutral'))
        score = round(best_prediction.get('score', 0) * 100, 1)
        reasoning = f"(Hugging Face API Fallback) Classified as {emotion} via Deep Learning."
        
        return emotion, score, reasoning

    def _normalize_emotion(self, raw_emotion):
        """Helper to ensure API responses match our UI classes."""
        e = raw_emotion.lower()
        if "joy" in e or "happy" in e: return "happy"
        if "sad" in e: return "sad"
        if "ang" in e: return "anger"
        if "fear" in e: return "fear"
        if "surpris" in e: return "surprise"
        return "neutral"

hybrid_ai = HybridEmotionAnalyzer()

@app.before_request
def ensure_db():
    try:
        db = get_db()
        cur = db.execute("PRAGMA table_info(emotions)")
        columns = [row[1] for row in cur.fetchall()]
        if 'reasoning' not in columns:
            init_db()
    except Exception:
        init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_route():
    data = request.get_json(force=True)
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'no text provided'}), 400

    try:
        emotion, score, reasoning = hybrid_ai.analyze_emotion(text)
    except Exception as e:
        return jsonify({'error': str(e)}), 503
    
    db = get_db()
    db.execute('INSERT INTO emotions (text, emotion, score, reasoning) VALUES (?, ?, ?, ?)', (text, emotion, score, reasoning))
    db.commit()
    
    stats = get_stats()
    return jsonify({
        'emotion': emotion, 
        'score': score,
        'reasoning': reasoning,
        'stats': stats
    })

@app.route('/history')
def history():
    db = get_db()
    cur = db.execute('SELECT text, emotion, score, reasoning, timestamp FROM emotions ORDER BY timestamp DESC LIMIT 10')
    rows = cur.fetchall()
    return jsonify([dict(row) for row in rows])

@app.route('/stats')
def stats():
    return jsonify(get_stats())

def get_stats() -> dict:
    db = get_db()
    cur = db.execute('SELECT emotion, COUNT(*) AS count FROM emotions GROUP BY emotion')
    rows = cur.fetchall()
    return {row['emotion']: row['count'] for row in rows}

if __name__ == '__main__':
    with app.app_context():
        pass
    # Bind to 0.0.0.0 so external devices (like mobile phones on LAN) can reach it!
    app.run(host='0.0.0.0', debug=True, port=5000)
