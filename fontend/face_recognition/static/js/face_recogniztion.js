const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const videoFeed = document.getElementById('videoFeed');
const statusDisplay = document.getElementById('statusDisplay');

let recognitionActive = false;
let eventSource = null;

startBtn.addEventListener('click', () => {
    startRecognition();
});

stopBtn.addEventListener('click', () => {
    stopRecognition();
});

function startRecognition() {
    recognitionActive = true;
    startBtn.disabled = true;
    stopBtn.disabled = false;
    statusDisplay.textContent = "System is starting...";
    statusDisplay.className = "status";

    // For this demo, we'll simulate the video feed
    // In a real implementation, you would connect to your Python backend
    videoFeed.src = "data:image/svg+xml;charset=UTF-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='640' height='480' viewBox='0 0 640 480'%3E%3Crect width='100%25' height='100%25' fill='%23ddd'/%3E%3Ctext x='50%25' y='50%25' font-family='Arial' font-size='24' fill='%23666' text-anchor='middle' dominant-baseline='middle'%3ECamera feed would appear here%3C/text%3E%3C/svg%3E";

    // Simulate recognition status updates
    setTimeout(() => {
        statusDisplay.textContent = "System is running. Waiting for face detection...";
        statusDisplay.className = "status unknown";
        }, 1000);

    // In a real implementation, you would use something like:
    // eventSource = new EventSource('/video_feed');
    // eventSource.onmessage = function(e) {
    //     videoFeed.src = 'data:image/jpeg;base64,' + e.data;
    // };
}

function stopRecognition() {
    recognitionActive = false;
    startBtn.disabled = false;
    stopBtn.disabled = true;
    statusDisplay.textContent = "System is stopped.";
    statusDisplay.className = "status";

    // Clear the video feed
    videoFeed.src = "";

    // In a real implementation:
    // if (eventSource) {
    //     eventSource.close();
    // }
}

// For demonstration purposes - simulate face recognition
function simulateRecognition() {
    if (!recognitionActive) return;

    const outcomes = [
        {name: "Recognized: John Doe (Real)", class: "recognized"},
        {name: "Recognized: Jane Smith (Fake)", class: "unknown"},
        {name: "Undefined face detected", class: "unknown"},
        {name: "No face detected", class: "unknown"}
    ];

    const randomOutcome = outcomes[Math.floor(Math.random() * outcomes.length)];
    statusDisplay.textContent = randomOutcome.name;
    statusDisplay.className = "status " + randomOutcome.class;

    setTimeout(simulateRecognition, 3000);
}

// Start simulation when "Start" is clicked
startBtn.addEventListener('click', () => {
    setTimeout(simulateRecognition, 2000);
});
