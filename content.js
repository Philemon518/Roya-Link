// Test log to confirm content.js is loaded
console.log("Content script is loaded and running on this page.");

chrome.runtime.onMessage.addListener((message) => {
    if (message.action === "playAudio" && message.audio_url) {
        console.log("Message received in content.js:", message);

        const audio = new Audio(message.audio_url);
        const video = document.querySelector("video");

        if (!video) {
            console.error("No video element found on the page.");
            return;
        }

        // Add debugging logs
        console.log("Video element detected:", video);
        console.log("Audio URL:", message.audio_url);

        // Ensure the video speed matches the audio speed
        if (message.video_speed) {
            console.log("Setting video playback rate to:", message.video_speed);
            video.playbackRate = message.video_speed;
        }

        // Synchronize audio with video playback
        video.addEventListener("play", () => {
            console.log("Primary logic: Video is playing. Attempting to start audio playback.");
            try {
                audio.currentTime = video.currentTime; // Sync audio with video
                audio.play().then(() => {
                    console.log("Primary logic: Audio playback started successfully.");
                }).catch((error) => {
                    console.error("Primary logic: Error playing audio:", error);
                    showPlaybackPrompt(audio);
                });
            } catch (e) {
                console.error("Primary logic: Audio playback failed:", e);
                showPlaybackPrompt(audio);
            }
        });

        video.addEventListener("pause", () => {
            console.log("Video paused. Pausing audio.");
            audio.pause();
        });

        video.addEventListener("seeked", () => {
            console.log("Video seeked. Adjusting audio time.");
            audio.currentTime = video.currentTime;
        });

        video.addEventListener("ended", () => {
            console.log("Video ended. Stopping audio.");
            audio.pause();
        });

        console.log("Audio playback synchronized with video.");

        // Handle audio errors
        audio.onerror = () => {
            console.error("Audio playback error occurred.");
            showPlaybackPrompt(audio);
        };
    } else {
        console.error("Invalid message or missing audio URL.");
    }
});

/**
 * Injects an <audio> element with controls into the page as a fallback.
 * This is useful if browser autoplay policies prevent automatic playback.
 */
function showPlaybackPrompt(audio) {
    console.log("Fallback logic: Injecting audio element for manual playback.");

    const audioElement = document.createElement("audio");
    audioElement.src = audio.src;
    audioElement.controls = true; // Add playback controls for user interaction
    audioElement.style.position = "fixed";
    audioElement.style.bottom = "20px";
    audioElement.style.right = "20px";
    audioElement.style.zIndex = "1000";

    document.body.appendChild(audioElement);

    const prompt = document.createElement("div");
    prompt.innerText = "Fallback logic: Audio playback blocked by browser. Use controls to play.";
    prompt.style.position = "fixed";
    prompt.style.bottom = "50px";
    prompt.style.right = "20px";
    prompt.style.backgroundColor = "#ffcc00";
    prompt.style.color = "#000";
    prompt.style.padding = "10px";
    prompt.style.borderRadius = "5px";
    prompt.style.zIndex = "1000";
    prompt.style.fontSize = "14px";

    document.body.appendChild(prompt);

    setTimeout(() => {
        prompt.remove(); // Remove the prompt after 10 seconds
    }, 10000);

    // Log the fallback details
    console.log("Fallback logic: Audio element and prompt added to the page.");
}
