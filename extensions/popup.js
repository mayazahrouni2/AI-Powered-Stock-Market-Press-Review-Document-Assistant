const startBtn = document.getElementById('startBtn');
const resultDiv = document.getElementById('result');
const progressBar = document.getElementById('progressBar');

startBtn.addEventListener('click', () => {
  resultDiv.textContent = "🚀 Lancement de l'agent...";
  progressBar.style.width = '20%';
  startBtn.disabled = true;

  fetch('http://localhost:5000/start')
    .then(res => res.json())
    .then(data => {
      resultDiv.textContent = data.message;
      progressBar.style.width = '50%';

      // Vérifier périodiquement si l'agent a fini
      const interval = setInterval(() => {
        fetch('http://localhost:5000/status')
          .then(res => res.json())
          .then(statusData => {
            resultDiv.textContent = statusData.message;
            if (!statusData.running) {
              progressBar.style.width = '100%';
              clearInterval(interval);
              startBtn.disabled = false;
            } else {
              // Animation progressive (optionnel)
              let currentWidth = parseInt(progressBar.style.width);
              if (currentWidth < 90) {
                progressBar.style.width = (currentWidth + 5) + '%';
              }
            }
          })
          .catch(() => {
            resultDiv.textContent = "❌ Erreur de connexion au serveur.";
            clearInterval(interval);
            startBtn.disabled = false;
            progressBar.style.width = '0%';
          });
      }, 2000);
    })
    .catch(() => {
      resultDiv.textContent = "❌ Impossible de lancer l'agent.";
      progressBar.style.width = '0%';
      startBtn.disabled = false;
    });
});
