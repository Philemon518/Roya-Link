let websocket;

chrome.runtime.onMessage.addListener(async (message, sender, sendResponse) => {
    const { youtube_url, language_code, action } = message;

    if (action === "startTranslation") {
        try {
            // Start the translation via the API
            const response = await fetch("http://127.0.0.1:8000/translate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ youtube_url, language_code }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error("Error from API:", errorData.detail);
                sendResponse({ success: false, error: errorData.detail });
                return;
            }

            const result = await response.json();
            console.log("Translation response:", result);

            // Notify popup about the initial success
            chrome.runtime.sendMessage({ 
                action: "updateProgress", 
                progress: 10, 
                status: "Starting WebSocket connection..." 
            });

            // Open a WebSocket to track progress
            websocket = new WebSocket("ws://127.0.0.1:8000/progress");

            websocket.onopen = () => {
                console.log("WebSocket connection established.");
                websocket.send(JSON.stringify({ youtube_url, language_code }));
            };

            websocket.onmessage = (event) => {
                const progressUpdate = JSON.parse(event.data);
                console.log("WebSocket message received:", progressUpdate);

                if (progressUpdate.progress !== undefined) {
                    // Send progress updates to the popup
                    chrome.runtime.sendMessage({
                        action: "updateProgress",
                        progress: progressUpdate.progress,
                        status: progressUpdate.status,
                    });
                }

                if (progressUpdate.progress === 100) {
                    // Notify popup and send to content script when translation is complete
                    chrome.runtime.sendMessage({
                        action: "translationComplete",
                        audio_url: result.audio_url,
                        video_speed: result.video_speed,
                    });

                    // Notify content script
                    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
                        if (tabs.length > 0) {
                            chrome.tabs.sendMessage(tabs[0].id, {
                                action: "playAudio",
                                audio_url: result.audio_url,
                                video_speed: result.video_speed,
                            });
                        }
                    });

                    websocket.close();
                }

                if (progressUpdate.progress === -1) {
                    // Handle errors
                    chrome.runtime.sendMessage({
                        action: "translationError",
                        status: progressUpdate.status,
                    });
                    websocket.close();
                }
            };

            websocket.onerror = (error) => {
                console.error("WebSocket error:", error);
                chrome.runtime.sendMessage({ action: "translationError", status: "WebSocket connection error." });
            };

            sendResponse({ success: true });
        } catch (error) {
            console.error("Error communicating with the server:", error);
            sendResponse({ success: false, error: "Failed to start translation." });
        }
    }
});
