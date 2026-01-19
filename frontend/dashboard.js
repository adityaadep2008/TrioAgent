document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const tasksGrid = document.getElementById('tasks-grid');
    const modal = document.getElementById('task-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalId = document.getElementById('modal-id');
    const modalStatus = document.getElementById('modal-status');
    const consoleOutput = document.getElementById('console-output');
    const resultArea = document.getElementById('result-area');
    const resultJson = document.getElementById('result-json');
    const closeModalBtn = document.getElementById('close-modal');
    const connectionStatus = document.getElementById('connection-status');
    const statusDot = document.querySelector('.status-dot');

    // Cursor Elements


    // State
    let activeTaskId = null;
    let tasks = {}; // { taskId: taskData }

    // --- Init ---
    init();

    function init() {

        initAnimations(); // Intro Animations
        fetchTasks();
        connectWebSocket();
        mermaid.initialize({ startOnLoad: false });
    }

    // --- Animations ---
    function initAnimations() {
        // 1. Header Text Split & Reveal
        const h1 = document.querySelector('.dashboard-header h1');
        if (h1) {
            h1.innerHTML = splitTextToSpans(h1.textContent);
            gsap.from(h1.querySelectorAll('span'), {
                y: 100,
                opacity: 0,
                duration: 1.2,
                stagger: 0.05,
                ease: "power4.out",
                delay: 0.2
            });
        }

        // 2. Line Expansion
        gsap.to('.header-line', {
            width: '60px',
            duration: 1.5,
            ease: "expo.out",
            delay: 1
        });

        // 3. Status Fade In
        gsap.from('.status-indicator', {
            x: 20,
            opacity: 0,
            duration: 1,
            ease: "power2.out",
            delay: 0.8
        });

        // 4. Back Link Fade In
        gsap.from('.back-link', {
            x: -20,
            opacity: 0,
            duration: 1,
            ease: "power2.out",
            delay: 0.8
        });
    }

    function splitTextToSpans(text) {
        return text.split('').map(char =>
            `<span style="display:inline-block; min-width: 8px;">${char === ' ' ? '&nbsp;' : char}</span>`
        ).join('');
    }

    // --- Custom Cursor ---


    // --- Data Fetching ---
    async function fetchTasks() {
        try {
            const response = await fetch('http://localhost:8000/tasks');
            const data = await response.json();

            tasksGrid.innerHTML = '';
            tasks = {};

            if (data.length === 0) {
                renderEmptyState();
            } else {
                data.forEach((task, index) => {
                    tasks[task.id] = task;
                    createTaskCard(task, index); // Pass index for stagger
                });
            }
            feather.replace();
        } catch (error) {
            console.error("Failed to fetch tasks:", error);
        }
    }

    function renderEmptyState() {
        tasksGrid.innerHTML = `
            <div class="empty-state">
                <div class="empty-visual"></div>
                <p>No active missions. Deploy an agent to see data here.</p>
            </div>
        `;
        // Animate Empty State
        gsap.from('.empty-state', {
            y: 30,
            opacity: 0,
            duration: 1,
            ease: "power3.out",
            delay: 0.5
        });
    }

    // --- UI Rendering ---
    function createTaskCard(task, index = 0) {
        if (tasksGrid.querySelector('.empty-state')) {
            tasksGrid.innerHTML = '';
        }

        const card = document.createElement('div');
        card.id = `card-${task.id}`;
        card.className = `task-card ${task.status}`;
        card.onclick = () => openTaskModal(task.id);



        const icon = getPersonaIcon(task.persona);

        card.innerHTML = `
            <div class="card-header">
                <div class="persona-badge">
                    ${icon}
                    <span>${capitalize(task.persona)}</span>
                </div>
                <span class="status-badge ${task.status}">${task.status.toUpperCase()}</span>
            </div>
            <div class="card-body">
                <p class="task-info">${getTaskSummary(task)}</p>
                <div class="task-footer">
                    <span class="timestamp">${formatTime(task.created_at)}</span>
                    <span class="arrow-icon"><i data-feather="arrow-up-right"></i></span>
                </div>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar"></div>
            </div>
        `;

        tasksGrid.prepend(card); // Newest first

        // GSAP Entrance (Staggered based on index or just simple entry)
        gsap.fromTo(card,
            { y: 100, opacity: 0, rotationX: 10, scale: 0.9 },
            {
                y: 0,
                opacity: 1,
                rotationX: 0,
                scale: 1,
                duration: 1,
                ease: "power4.out",
                clearProps: "all" // Clear transform to allow hover
            }
        );

        // Advanced Hover Effect 
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const centerX = rect.width / 2;
            const centerY = rect.height / 2;

            const rotateX = ((y - centerY) / centerY) * -5;
            const rotateY = ((x - centerX) / centerX) * 5;

            gsap.to(card, {
                rotationX: rotateX,
                rotationY: rotateY,
                duration: 0.4,
                ease: "power2.out",
                transformPerspective: 1000
            });
        });

        card.addEventListener('mouseleave', () => {
            gsap.to(card, {
                rotationX: 0,
                rotationY: 0,
                duration: 0.6,
                ease: "elastic.out(1, 0.5)",
                clearProps: "transform"
            });
        });
    }

    function updateTaskCard(taskId, status, result = null) {
        const card = document.getElementById(`card-${taskId}`);
        if (!card) return;

        card.className = `task-card ${status}`;
        const badge = card.querySelector('.status-badge');
        badge.className = `status-badge ${status}`;
        badge.textContent = status.toUpperCase();

        if (tasks[taskId]) {
            tasks[taskId].status = status;
            tasks[taskId].result = result;
        }

        if (activeTaskId === taskId) {
            modalStatus.textContent = status.toUpperCase();
            modalStatus.className = `badge ${status}`;
            if (status === 'success' || status === 'failed') {
                showResult(result);
            }
        }
    }

    // --- Modal Logic ---
    function openTaskModal(taskId) {
        const task = tasks[taskId];
        if (!task) return;

        activeTaskId = taskId;
        modalTitle.textContent = `${capitalize(task.persona)} Operation`;
        modalId.textContent = `ID: ${taskId.split('-')[0]}...`;

        modalStatus.textContent = task.status.toUpperCase();
        modalStatus.className = `badge ${task.status}`;

        consoleOutput.innerHTML = '';
        if (task.logs && task.logs.length > 0) {
            task.logs.forEach(log => appendLog(log, false));
        } else {
            consoleOutput.innerHTML = '<div class="log-line system">> Waiting for Uplink...</div>';
        }

        if (task.status === 'success' || task.status === 'failed') {
            showResult(task.result);
        } else {
            resultArea.classList.add('hidden');
        }

        // Modal Entrance Animation
        modal.classList.remove('hidden');
        gsap.fromTo('.modal-content',
            { y: 50, opacity: 0, scale: 0.95 },
            { y: 0, opacity: 1, scale: 1, duration: 0.5, ease: "power3.out" }
        );

        consoleOutput.scrollTop = consoleOutput.scrollHeight;
    }

    function closeModal() {
        gsap.to('.modal-content', {
            y: 50, opacity: 0, scale: 0.95, duration: 0.3, ease: "power3.in",
            onComplete: () => {
                modal.classList.add('hidden');
                activeTaskId = null;
            }
        });
    }

    // Event Listeners for Modal
    closeModalBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    function appendLog(message, autoScroll = true) {
        const line = document.createElement('div');
        line.className = 'log-line';

        if (message.includes('Error') || message.includes('failed') || message.includes('❌')) {
            line.classList.add('error');
        } else if (message.includes('Success') || message.includes('✅')) {
            line.classList.add('success');
        }

        line.textContent = message;
        consoleOutput.appendChild(line);

        if (autoScroll) {
            consoleOutput.scrollTop = consoleOutput.scrollHeight;
        }
    }

    function showResult(result) {
        resultArea.classList.remove('hidden');
        // Simple JSON dump but planned for better UI
        resultJson.textContent = JSON.stringify(result, null, 2);

        // Custom views (same as before)
        if (result && result.flowchart_code) {
            // Re-render mermaid if it's there
            // (Logic same as original file, abbreviated here for clarity but keeping functionality)
            resultJson.innerHTML = '';
            const mermaidContainer = document.createElement('div');
            mermaidContainer.className = 'mermaid';
            mermaidContainer.innerHTML = result.flowchart_code;
            resultArea.appendChild(mermaidContainer);
            mermaid.init(undefined, mermaidContainer);
        }
    }

    // --- WebSocket ---
    function connectWebSocket() {
        const ws = new WebSocket('ws://localhost:8000/ws');

        ws.onopen = () => {
            connectionStatus.textContent = 'ONLINE';
            statusDot.classList.add('pulse');
            statusDot.style.backgroundColor = '#000'; // Black for connected in light mode
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleWsMessage(data);
            } catch (e) {
                console.log("Ignored non-JSON WS message:", event.data);
            }
        };

        ws.onclose = () => {
            connectionStatus.textContent = 'OFFLINE';
            statusDot.classList.remove('pulse');
            statusDot.style.backgroundColor = '#ff0000';
            setTimeout(connectWebSocket, 5000);
        };
    }

    function handleWsMessage(payload) {
        const { type, task_id, message, status, result, persona } = payload;

        if (type === 'start') {
            const newTask = {
                id: task_id,
                persona: persona,
                status: 'running',
                created_at: new Date().toISOString(),
                logs: [],
                result: null,
                payload: {}
            };
            tasks[task_id] = newTask;
            createTaskCard(newTask);
            feather.replace();
        }

        if (!tasks[task_id] && type !== 'start') {
            fetchTasks();
            return;
        }

        if (type === 'log') {
            tasks[task_id].logs.push(message);
            if (activeTaskId === task_id) {
                appendLog(message);
            }
        } else if (type === 'complete') {
            updateTaskCard(task_id, status, result);
        }
    }

    // --- Helpers ---
    function capitalize(str) {
        return str ? str.charAt(0).toUpperCase() + str.slice(1) : '';
    }

    function formatTime(isoStr) {
        if (!isoStr) return '';
        const d = new Date(isoStr);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function getPersonaIcon(persona) {
        const icons = {
            shopper: '<i data-feather="shopping-cart"></i>',
            rider: '<i data-feather="map"></i>',
            patient: '<i data-feather="plus-circle"></i>',
            coordinator: '<i data-feather="calendar"></i>',
            foodie: '<i data-feather="coffee"></i>'
        };
        return icons[persona] || '<i data-feather="cpu"></i>';
    }

    function getTaskSummary(task) {
        const p = task.payload || {};
        if (task.persona === 'shopper') return `Finding ${p.product || 'items'}`;
        if (task.persona === 'rider') return `Ride to ${p.drop || 'destination'}`;
        return 'Active Operation';
    }
});
