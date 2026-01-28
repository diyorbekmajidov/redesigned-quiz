/**
 * Quiz Timer - Test vaqtini kuzatish
 */

class QuizTimer {
    constructor(remainingSeconds, onTimeUp) {
        this.remainingSeconds = remainingSeconds;
        this.onTimeUp = onTimeUp;
        this.timerInterval = null;
        this.warningShown = false;
    }
    
    start() {
        this.updateDisplay();
        this.timerInterval = setInterval(() => {
            this.remainingSeconds--;
            
            if (this.remainingSeconds <= 0) {
                this.stop();
                this.onTimeUp();
                return;
            }
            
            this.updateDisplay();
            this.checkWarnings();
        }, 1000);
    }
    
    stop() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }
    
    updateDisplay() {
        const minutes = Math.floor(this.remainingSeconds / 60);
        const seconds = this.remainingSeconds % 60;
        
        const display = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        
        // Timer element'ni yangilash
        const timerElement = document.getElementById('quiz-timer');
        if (timerElement) {
            timerElement.textContent = display;
            
            // Rang o'zgartirish
            if (this.remainingSeconds <= 60) {
                timerElement.classList.add('text-danger');
                timerElement.classList.remove('text-warning', 'text-primary');
            } else if (this.remainingSeconds <= 300) {
                timerElement.classList.add('text-warning');
                timerElement.classList.remove('text-danger', 'text-primary');
            }
        }
        
        // Progress bar
        const progressBar = document.getElementById('timer-progress');
        if (progressBar) {
            const totalSeconds = parseInt(progressBar.dataset.totalSeconds);
            const percentage = (this.remainingSeconds / totalSeconds) * 100;
            progressBar.style.width = `${percentage}%`;
            
            if (percentage <= 10) {
                progressBar.classList.add('bg-danger');
                progressBar.classList.remove('bg-warning', 'bg-success');
            } else if (percentage <= 30) {
                progressBar.classList.add('bg-warning');
                progressBar.classList.remove('bg-danger', 'bg-success');
            }
        }
    }
    
    checkWarnings() {
        // 5 daqiqa qolganida ogohlantirish
        if (this.remainingSeconds === 300 && !this.warningShown) {
            this.showWarning('5 daqiqa qoldi!');
            this.warningShown = true;
        }
        
        // 1 daqiqa qolganida ogohlantirish
        if (this.remainingSeconds === 60) {
            this.showWarning('1 daqiqa qoldi!', 'danger');
        }
    }
    
    showWarning(message, type = 'warning') {
        // Toast notification
        const toastHtml = `
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fas fa-clock me-2"></i>${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                            data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        const toastContainer = document.getElementById('toast-container') || 
            this.createToastContainer();
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        const toastElement = toastContainer.lastElementChild;
        const toast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: 5000
        });
        toast.show();
        
        // Toast yopilgandan keyin o'chirish
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }
    
    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '11';
        document.body.appendChild(container);
        return container;
    }
}

// Auto-save javoblar
class QuizAutoSave {
    constructor(saveUrl, interval = 30000) {
        this.saveUrl = saveUrl;
        this.interval = interval;
        this.saveTimer = null;
        this.unsavedChanges = false;
    }
    
    start() {
        // Form o'zgarishlarini kuzatish
        document.querySelectorAll('input[type="radio"]').forEach(input => {
            input.addEventListener('change', () => {
                this.unsavedChanges = true;
            });
        });
        
        // Avtomatik saqlash
        this.saveTimer = setInterval(() => {
            if (this.unsavedChanges) {
                this.save();
            }
        }, this.interval);
        
        // Sahifa yopilishda ogohlantirish
        window.addEventListener('beforeunload', (e) => {
            if (this.unsavedChanges) {
                e.preventDefault();
                e.returnValue = '';
            }
        });
    }
    
    stop() {
        if (this.saveTimer) {
            clearInterval(this.saveTimer);
        }
    }
    
    async save() {
        const form = document.getElementById('quiz-form');
        if (!form) return;
        
        const formData = new FormData(form);
        formData.append('action', 'save');
        
        try {
            const response = await fetch(this.saveUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                }
            });
            
            if (response.ok) {
                this.unsavedChanges = false;
                this.showSaveStatus('success');
            } else {
                this.showSaveStatus('error');
            }
        } catch (error) {
            console.error('Auto-save xatolik:', error);
            this.showSaveStatus('error');
        }
    }
    
    showSaveStatus(status) {
        const statusElement = document.getElementById('save-status');
        if (!statusElement) return;
        
        if (status === 'success') {
            statusElement.innerHTML = '<i class="fas fa-check-circle text-success"></i> Saqlandi';
        } else {
            statusElement.innerHTML = '<i class="fas fa-exclamation-circle text-danger"></i> Xatolik';
        }
        
        setTimeout(() => {
            statusElement.innerHTML = '';
        }, 3000);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Timer
    const timerElement = document.getElementById('quiz-timer');
    if (timerElement) {
        const remainingSeconds = parseInt(timerElement.dataset.remainingSeconds);
        
        const timer = new QuizTimer(remainingSeconds, () => {
            // Vaqt tugaganda
            alert('Vaqt tugadi! Test avtomatik yakunlanmoqda...');
            document.getElementById('quiz-form').submit();
        });
        
        timer.start();
        
        // Form submit qilinganda timer to'xtatish
        document.getElementById('quiz-form')?.addEventListener('submit', () => {
            timer.stop();
        });
    }
    
    // Auto-save
    const quizForm = document.getElementById('quiz-form');
    if (quizForm) {
        const saveUrl = quizForm.action;
        const autoSave = new QuizAutoSave(saveUrl);
        autoSave.start();
    }
});