document.addEventListener("DOMContentLoaded", () => {
    const LANGUAGE_MAP = {
        "cat": "Catalan",
        "cmn": "Mandarin",
        "por": "Portuguese",
        "spa": "Spanish",
        "pes": "Western Persian"
    };

    const languageSelect = document.getElementById("language");
    const progressContainer = document.getElementById("progress-container");
    const progressBar = document.getElementById("progress-bar");
    const progressStatus = document.getElementById("progress-status");

    // Populate the language dropdown
    for (const [code, name] of Object.entries(LANGUAGE_MAP)) {
        const option = document.createElement("option");
        option.value = code;
        option.textContent = name;
        languageSelect.appendChild(option);
    }

    document.getElementById("translate").addEventListener("click", async () => {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        const url = tab.url;
        const language = languageSelect.value;

        if (!language) {
            alert("Please select a language!");
            return;
        }

        // Show the progress container and reset progress
        progressContainer.style.display = "block";
        progressBar.value = 0;
        progressStatus.textContent = "Connecting to server...";

        const ws = new WebSocket("ws://127.0.0.1:8000/progress");

        // Handle WebSocket connection
        ws.onopen = () => {
            console.log("WebSocket connection established.");
            ws.send(JSON.stringify({ youtube_url: url, language_code: language }));
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log("Progress update:", data);

            if (data.progress >= 0) {
                progressBar.value = data.progress;
                progressStatus.textContent = data.status;
            }

            if (data.progress === 100) {
                progressStatus.textContent = "Audio file ready! Playing now...";
                ws.close();
            }

            if (data.progress === -1) {
                progressStatus.textContent = "An error occurred: " + data.status;
                ws.close();
            }
        };

        ws.onerror = (error) => {
            console.error("WebSocket error:", error);
            progressStatus.textContent = "Connection error. Please try again.";
            ws.close();
        };

        ws.onclose = () => {
            console.log("WebSocket connection closed.");
        };
    });
});
