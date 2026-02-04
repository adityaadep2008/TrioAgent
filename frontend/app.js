
// -- app.js --

document.addEventListener("DOMContentLoaded", () => {

    // --- MODE TOGGLE LOGIC ---
    const btnManual = document.getElementById('mode-manual_btn');
    const btnVoice = document.getElementById('mode-voice_btn');
    const viewManual = document.getElementById('mode-manual');
    const viewVoice = document.getElementById('mode-voice');

    function switchMode(mode) {
        if (mode === 'manual') {
            btnManual.classList.add('active');
            btnVoice.classList.remove('active');
            viewManual.style.display = 'block';
            viewVoice.style.display = 'none';
        } else {
            btnManual.classList.remove('active');
            btnVoice.classList.add('active');
            viewManual.style.display = 'none';
            viewVoice.style.display = 'block';
        }
    }

    btnManual.addEventListener('click', () => switchMode('manual'));
    btnVoice.addEventListener('click', () => switchMode('voice'));

    // --- WEBSOCKET CONNECTION ---
    const resultWrapper = document.getElementById('result-wrapper');
    const resultMessage = document.getElementById('result-message');

    function logStatus(msg) {
        console.log("LOG:", msg);
        // If in voice mode, maybe append to chat? 
        // For now, update global status logic if visible
        if (viewManual.style.display !== 'none') {
            resultWrapper.classList.remove('hidden');
            resultMessage.innerHTML = msg.replace(/\n/g, '<br>');
        }
    }

    function showResultUI(result) {
        resultWrapper.classList.remove('hidden');
        if (result.status === 'success') {
            resultMessage.innerHTML = `<span style="color:var(--voice-green)">SUCCESS</span><br>${JSON.stringify(result.data || result, null, 2)}`;
        } else {
            resultMessage.innerHTML = `<span style="color:var(--voice-red)">FAILED</span><br>${result.error || "Unknown Error"}`;
        }

        // If Voice Mode active, speak result
        if (viewVoice.style.display !== 'none' && window.lastVoiceCommand) {
            const spoken = result.message || "Task completed.";
            speak(spoken);
            addChatMessage(spoken, 'agent');
            window.lastVoiceCommand = false;
        }
    }

    // Connect WS
    function connectWebSocket() {
        const ws = new WebSocket('ws://localhost:8002/ws');
        ws.onopen = () => logStatus('Connected to Neural Core.');
        ws.onmessage = (event) => {
            try {
                const parsed = JSON.parse(event.data);
                if (parsed.type === 'log') {
                    // logStatus(parsed.message); // Too verbose for main UI?
                } else if (parsed.type === 'complete') {
                    showResultUI(parsed.result);
                }
            } catch (e) { console.log(event.data); }
        };
        ws.onclose = () => setTimeout(connectWebSocket, 3000);
    }
    connectWebSocket();


    // --- MANUAL MODE: PERSONA SELECTOR LOGIC ---

    // Logic from original script.js adapted here
    const dropdownTrigger = document.getElementById('dropdown-trigger');
    const dropdownOptions = document.querySelector('.dropdown-options');
    const options = document.querySelectorAll('.dropdown-option');
    const inputVal = document.getElementById('persona-select-value');
    const triggerText = document.querySelector('.selected-text');
    const forms = document.querySelectorAll('.form-content');

    // Default Selection
    selectPersona('shopper');

    dropdownTrigger.addEventListener('click', () => {
        dropdownOptions.classList.toggle('active');
    });

    options.forEach(opt => {
        opt.addEventListener('click', () => {
            const val = opt.getAttribute('data-value');
            selectPersona(val);
            triggerText.textContent = opt.textContent;
            dropdownOptions.classList.remove('active');
        });
    });

    // Close dropdown if clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.custom-dropdown-container')) {
            dropdownOptions.classList.remove('active');
        }
    });

    function selectPersona(persona) {
        inputVal.value = persona;
        forms.forEach(f => {
            f.classList.add('hidden');
            gsap.set(f, { opacity: 0, y: 20 });
        });

        const activeForm = document.getElementById(`form-${persona}`);
        if (activeForm) {
            activeForm.classList.remove('hidden');
            gsap.to(activeForm, { opacity: 1, y: 0, duration: 0.5 });
        }
    }

    // Pill Logic (Rider)
    document.querySelectorAll('.pill-option').forEach(pill => {
        pill.addEventListener('click', function () {
            const parent = this.parentElement;
            parent.querySelectorAll('.pill-option').forEach(p => p.classList.remove('active'));
            this.classList.add('active');

            // Update hidden input if exists
            const hidden = parent.parentElement.querySelector('input[type="hidden"]');
            if (hidden) hidden.value = this.getAttribute('data-value');
        });
    });

    // Dynamic Lists (Guests/Meds)
    const addGuestBtn = document.getElementById('add-guest-btn');
    if (addGuestBtn) {
        addGuestBtn.addEventListener('click', () => {
            const div = document.createElement('div');
            div.className = 'guest-item';
            div.innerHTML = `<input type="text" class="styled-input guest-name" placeholder="Guest Name">`;
            document.getElementById('guest-list-container').appendChild(div);
        });
    }

    const addMedBtn = document.getElementById('add-medicine-btn');
    if (addMedBtn) {
        addMedBtn.addEventListener('click', () => {
            const temp = document.querySelector('.medicine-item').cloneNode(true);
            temp.querySelector('input').value = '';
            document.getElementById('medicine-list-container').appendChild(temp);
        });
    }

    // EXECUTE BUTTON
    const execBtn = document.getElementById('find-deal-btn');
    execBtn.addEventListener('click', async () => {
        const persona = inputVal.value;
        let payload = { persona: persona };

        // Build Payload based on persona
        if (persona === 'shopper') {
            payload.product = document.getElementById('product-name').value;
        } else if (persona === 'rider') {
            payload.pickup = document.getElementById('pickup-location').value;
            payload.drop = document.getElementById('drop-location').value;
            payload.preference = document.getElementById('rider-preference-value').value;
            payload.action = document.getElementById('rider-action-toggle').checked ? 'book' : 'compare';
        } else if (persona === 'patient') {
            const meds = [];
            document.querySelectorAll('.medicine-item').forEach(item => {
                const name = item.querySelector('.med-name').value;
                const qty = item.querySelector('.med-qty').value;
                if (name) meds.push({ name, qty: parseInt(qty) });
            });
            payload.medicine = meds;
            payload.role = 'patient';
        } else if (persona === 'foodie') {
            payload.food_item = document.getElementById('food-item').value;
            payload.action = document.getElementById('foodie-action-toggle').checked ? 'order' : 'search';
        } else if (persona === 'coordinator') {
            payload.event_name = document.getElementById('event-name').value;
            const guests = [];
            document.querySelectorAll('.guest-name').forEach(i => { if (i.value) guests.push(i.value) });
            payload.guest_list = guests;
        } else if (persona === 'traveller') {
            payload.source = document.getElementById('trip-source').value;
            payload.destination = document.getElementById('trip-dest').value;
            payload.date = document.getElementById('trip-date').value;
            payload.user_interests = document.getElementById('trip-interests').value;
        }

        logStatus("Sending mission to core...");

        try {
            const res = await fetch('/task', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            logStatus("Mission Queued. ID: " + data.task_id);
        } catch (e) {
            logStatus("Error: " + e.message);
        }
    });


    // --- VOICE MODE LOGIC ---

    const bigMicBtn = document.getElementById('big-mic-btn');
    const voiceStatus = document.getElementById('voice-status-text');
    const chatDisplay = document.getElementById('chat-display');

    // TTS
    const synth = window.speechSynthesis;
    function speak(text) {
        if (synth.speaking) synth.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.pitch = 1;
        utterance.rate = 1;

        // Visual Feedback
        bigMicBtn.classList.add('speaking');
        utterance.onend = () => bigMicBtn.classList.remove('speaking');

        synth.speak(utterance);
    }

    function addChatMessage(text, sender) {
        const div = document.createElement('div');
        div.className = `msg-bubble msg-${sender}`;
        div.textContent = text;
        chatDisplay.appendChild(div);
        chatDisplay.scrollTop = chatDisplay.scrollHeight;
    }

    // --- ROBUST SPEECH RECOGNITION (VAD & STATE MACHINE) ---
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition;

    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = true; // KEEP LISTENING
        recognition.interimResults = true; // Show text as you speak
        recognition.lang = 'en-US'; // Critical for ensuring correct server connection

        // --- CONFIGURATION ---
        const SILENCE_DELAY = 2500; // 2.5 seconds of silence to finalize

        // --- STATE MANAGEMENT ---
        let logicalListeningState = false; // The source of truth for "Are we in a session?"
        let silenceTimeoutId = null;
        let finalTranscript = '';

        // --- CONTROL FUNCTIONS ---
        window.startSession = function () {
            if (logicalListeningState) return;

            logicalListeningState = true;
            finalTranscript = '';

            // Update UI
            bigMicBtn.classList.add('listening');
            voiceStatus.textContent = "Listening...";

            // Start API
            try {
                recognition.start();
            } catch (e) {
                console.warn("API Start Error (clean):", e);
            }
        };

        window.endSession = function () {
            console.log("Ending Session. Logical State -> False");
            logicalListeningState = false;
            clearTimeout(silenceTimeoutId);

            // Stop API
            recognition.stop();

            // Update UI
            bigMicBtn.classList.remove('listening');
            voiceStatus.textContent = "Processing...";

            // Process Result
            const textToSend = finalTranscript.trim();
            if (textToSend.length > 0) {
                sendVoiceToBackend(textToSend);
            } else {
                voiceStatus.textContent = "Tap to Speak";
            }
        };

        // Button Handler
        bigMicBtn.addEventListener('click', () => {
            if (logicalListeningState) {
                window.endSession(); // Manual Stop
            } else {
                window.startSession(); // Manual Start
            }
        });

        // --- EVENTS ---
        recognition.onstart = () => {
            console.log("API: Started");
        };

        recognition.onerror = (event) => {
            console.error("Speech Error", event.error);
            // Ignore 'no-speech' and 'aborted' (tab conflict)
            if (event.error !== 'no-speech' && event.error !== 'aborted') {
                // Revert to generic message as requested ("try to make sothing that works like that")
                voiceStatus.textContent = "Error listening. Try again.";
            }
        };

        recognition.onend = () => {
            console.log("API: Ended. Logical State:", logicalListeningState);
            if (logicalListeningState) {
                // Browser stopped, but we want to keep listening (Seamless Restart)
                console.log("Creating seamless restart...");
                try {
                    recognition.start();
                } catch (e) {
                    console.error("Restart failed:", e);
                    // If we can't restart, we must abort
                    logicalListeningState = false;
                    voiceStatus.textContent = "Error: Mic stopped unexpectedly.";
                    bigMicBtn.classList.remove('listening');
                }
            }
        };

        recognition.onresult = (event) => {
            let interimTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript + ' ';
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }

            // Visual Update: Show exactly what is being heard
            // Just like accessibility.html: "Listening..." is replaced by actual text
            const currentText = finalTranscript + interimTranscript;
            const display = currentText.trim().length > 0 ? currentText : "Listening...";
            // Show result in the status text, trimmed to fit
            voiceStatus.textContent = display.slice(-100);

            // RESET SILENCE TIMER
            clearTimeout(silenceTimeoutId);
            silenceTimeoutId = setTimeout(() => {
                console.log("Silence limit reached. Auto-submitting.");
                window.endSession();
            }, SILENCE_DELAY);
        };

        // Backend Communication
        async function sendVoiceToBackend(text) {
            voiceStatus.textContent = "Thinking...";
            addChatMessage(text, 'user');
            window.lastVoiceCommand = true;

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: "voice-web-" + Date.now(),
                        message: text
                    })
                });

                const data = await response.json();
                if (data.response) {
                    addChatMessage(data.response, 'agent');
                    speak(data.response);
                    voiceStatus.textContent = "Tap to Speak";
                }
            } catch (e) {
                voiceStatus.textContent = "Error connecting.";
                speak("I'm having trouble connecting to the core.");
            }
        }

    } else {
        voiceStatus.textContent = "Voice not supported in this browser.";
    }

}); // DOMContentLoaded
