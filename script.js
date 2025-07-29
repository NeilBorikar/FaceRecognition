document.addEventListener('DOMContentLoaded', function () {
    // ========= LIVE CAMERA + ATTENDANCE LOGGING =========
    const videoFeed = document.getElementById('camera-feed');
    const markBtn = document.getElementById('mark-btn');
    const attendanceLog = document.getElementById('attendance-log');

    // Mark attendance button handler
    if (markBtn) {
        markBtn.addEventListener('click', async () => {
            markBtn.disabled = true;
            markBtn.textContent = 'Processing...';

            try {
                const response = await fetch('/mark_attendance');
                const result = await response.json();

                if (result.status === 'success') {
                    attendanceLog.innerHTML += `
                        <div class="log-entry">
                            <span class="name">${result.name}</span>
                            <span class="time">${result.time}</span>
                            <span class="status success">✓</span>
                        </div>`;
                } else {
                    attendanceLog.innerHTML += `
                        <div class="log-entry">
                            <span class="error">${result.message}</span>
                        </div>`;
                }
            } catch (error) {
                attendanceLog.innerHTML += `
                    <div class="log-entry">
                        <span class="error">Network error</span>
                    </div>`;
            } finally {
                markBtn.disabled = false;
                markBtn.textContent = 'Mark Attendance';
            }
        });

        // Auto-scroll log every 500ms
        setInterval(() => {
            attendanceLog.scrollTop = attendanceLog.scrollHeight;
        }, 500);
    }

    // ========= ATTENDANCE FILTER UI =========
    const setupAttendanceFilters = () => {
        const filterTypeRadios = document.querySelectorAll('input[name="filter_type"]');

        const updateInputs = () => {
            const isSingle = document.querySelector('#single_date:checked') !== null;
            const dateInput = document.querySelector('[name="date"]');
            const startInput = document.querySelector('[name="start_date"]');
            const endInput = document.querySelector('[name="end_date"]');

            if (dateInput && startInput && endInput) {
                dateInput.disabled = !isSingle;
                startInput.disabled = isSingle;
                endInput.disabled = isSingle;
            }
        };

        if (filterTypeRadios.length > 0) {
            filterTypeRadios.forEach(radio => {
                radio.addEventListener('change', updateInputs);
            });
            updateInputs(); // initial setup
        }
    };

    setupAttendanceFilters();
});