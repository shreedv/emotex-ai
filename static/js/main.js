document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('text-form');
    const analyzeBtn = document.getElementById('analyze-btn');
    const btnText = analyzeBtn.querySelector('.btn-text');
    const loader = document.getElementById('btn-loader');
    
    // Bento sections
    const placeholderAccent = document.getElementById('result-placeholder');
    const resultBody = document.getElementById('result-body');
    const reasoningCard = document.getElementById('reasoning-card');
    const chartCard = document.getElementById('chart-card');
    const historyCard = document.getElementById('history-card');
    const resultAccentUI = document.getElementById('result-accent');
    
    // Values
    const detectedEmotion = document.getElementById('detected-emotion');
    const confidenceScore = document.getElementById('confidence-score');
    const confidenceFill = document.getElementById('confidence-fill');
    const aiReasoning = document.getElementById('ai-reasoning');
    
    const historyBody = document.getElementById('history-body');
    const chartCanvas = document.getElementById('emotionChart');
    
    let emotionChartInstance = null;
    
    const emotionColors = {
        'happy': '#f59e0b',
        'sad': '#3b82f6',
        'anger': '#ef4444',
        'fear': '#8b5cf6',
        'surprise': '#ec4899',
        'neutral': '#64748b'
    };

    fetchDashboardData();

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const textArea = document.getElementById('user-text');
        const text = textArea.value.trim();
        if (!text) return;

        btnText.classList.add('hidden');
        loader.classList.remove('hidden');
        analyzeBtn.disabled = true;
        
        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                displayResult(data.emotion, data.score, data.reasoning);
                updateChart(data.stats);
                fetchHistory(); // Refresh history table
            } else {
                alert('Analysis failed: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error analyzing text:', error);
            alert('Could not connect to the server.');
        } finally {
            btnText.classList.remove('hidden');
            loader.classList.add('hidden');
            analyzeBtn.disabled = false;
        }
    });

    function displayResult(emotion, score, reasoning) {
        // Hide placeholder, show distinct bento sections
        placeholderAccent.classList.add('hidden');
        resultBody.classList.remove('hidden');
        reasoningCard.classList.remove('hidden');
        chartCard.classList.remove('hidden');
        historyCard.classList.remove('hidden');
        
        detectedEmotion.textContent = emotion;
        confidenceScore.textContent = `${score}`;
        aiReasoning.textContent = `> ${reasoning}`;
        
        // Dynamically change accent color based on emotion!
        const color = emotionColors[emotion] || emotionColors['neutral'];
        resultAccentUI.style.backgroundColor = color;
        
        confidenceFill.style.width = `0%`;
        setTimeout(() => { confidenceFill.style.width = `${score}%`; }, 50);
    }
    
    async function fetchDashboardData() {
        try {
            const [statsRes, historyRes] = await Promise.all([ fetch('/stats'), fetch('/history') ]);
            if (statsRes.ok) {
                const stats = await statsRes.json();
                if (Object.keys(stats).length > 0) {
                    updateChart(stats);
                    chartCard.classList.remove('hidden');
                }
            }
            if (historyRes.ok) {
                const h = await historyRes.json();
                if (h.length > 0) historyCard.classList.remove('hidden');
                renderHistory(h);
            }
        } catch (err) {}
    }
    
    async function fetchHistory() {
        try {
            const res = await fetch('/history');
            if (res.ok) renderHistory(await res.json());
        } catch (err) {}
    }
    
    function renderHistory(items) {
        historyBody.innerHTML = '';
        if (items.length === 0) return;
        
        items.forEach(item => {
            const date = new Date(item.timestamp);
            const timeStr = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
            const color = emotionColors[item.emotion] || emotionColors['neutral'];
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="color:var(--text-secondary); width: 60px;">${timeStr}</td>
                <td>
                    <div style="font-weight:600; margin-bottom:4px; font-size:1.05em;">"${item.text}"</div>
                    <div style="font-size:0.85rem; color:var(--text-secondary); font-family: 'JetBrains Mono', monospace;">> ${item.reasoning}</div>
                </td>
                <td style="width: 100px; text-align: right;">
                    <span class="label-cell" style="background-color: ${color}">${item.emotion}</span>
                    <div style="font-size:0.75rem; color:#666; margin-top: 4px; font-family: 'JetBrains Mono', monospace;">Score: ${item.score}%</div>
                </td>
            `;
            historyBody.appendChild(tr);
        });
    }

    function updateChart(stats) {
        const labels = Object.keys(stats);
        const data = Object.values(stats);
        const bgColors = labels.map(emotion => emotionColors[emotion] || emotionColors['neutral']);

        if (emotionChartInstance) {
            emotionChartInstance.data.labels = labels;
            emotionChartInstance.data.datasets[0].data = data;
            emotionChartInstance.data.datasets[0].backgroundColor = bgColors;
            emotionChartInstance.data.datasets[0].borderColor = '#141414';
            emotionChartInstance.update();
        } else {
            emotionChartInstance = new Chart(chartCanvas, {
                type: 'pie',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: bgColors,
                        borderWidth: 2,
                        borderColor: '#141414',
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { 
                            position: 'bottom', 
                            labels: { color: '#888', font: { family: "'JetBrains Mono', monospace", size: 10 } } 
                        }
                    }
                }
            });
        }
    }
});