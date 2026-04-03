# EmoTex – Offline Text Emotion Analyzer

This repository contains an offline emotion analysis web application built with Python, Flask, Ollama (local LLM), SQLite, and Chart.js. It's designed for privacy-conscious use with zero cloud dependency.

## Features

- Uses the Gemma3:1B local language model via Ollama to detect emotions (happiness, sadness, anger, fear, sarcasm).
- Flask backend handles user input, communicates with the local LLM, and manages application logic.
- SQLite database stores detected emotions for tracking and statistics.
- Front-end renders an interactive pie chart using Chart.js showing emotion distribution.

## Setup and Usage

1. **Install Ollama and the Gemma3:1B model**
   Follow the instructions at https://ollama.com/docs to install the CLI and pull `gemma3:1b`.

2. **Create a virtual environment and install Python dependencies**
   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```

3. **Start the application**
   ```bash
   python app.py
   ```
   Navigate to `http://127.0.0.1:5000` in your browser.

4. **Enter text** into the form on the page to analyze its emotion; results are stored locally and the pie chart updates.

## Project Structure

```
emotex/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   └── index.html
└── static/
    ├── js/
    │   └── main.js
    └── css/
        └── style.css
```

## Notes

- The emotion analysis works entirely offline as long as the local language model is installed.
- Customize the prompt or expand emotions by editing `app.py`.

---

Designed and developed by [Your Name] in 2025.