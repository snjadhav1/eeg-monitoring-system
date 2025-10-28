// ===== GLOBAL VARIABLES =====
let timelineChart, brainWaveChart;
let animationFrameId;
let brainCircleAnimation;
let studentsData = [];
let selectedStudent = null;

// ===== INITIALIZE ON LOAD =====
document.addEventListener('DOMContentLoaded', () => {
    initializeDateTimeClock();
    initializeTimelineChart();
    initializeBrainWaveChart();
    initializeMetricCircles();
    initializeParticles();
    animateNumbers();
    initializeNavigation();
    loadTeacherInfo();
    initializeStudentsDashboard();
    
    // Check if a student was selected from students.html
    checkForSelectedStudent();
});

// ===== DATE AND TIME =====
function initializeDateTimeClock() {
    updateDateTime();
    setInterval(updateDateTime, 1000);
}

function updateDateTime() {
    const now = new Date();
    
    const dateOptions = { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    };
    const dateStr = now.toLocaleDateString('en-US', dateOptions);
    
    const timeStr = now.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
    });
    
    const dateElement = document.querySelector('.current-date');
    const timeElement = document.querySelector('.current-time');
    
    if (dateElement) dateElement.textContent = dateStr;
    if (timeElement) timeElement.textContent = timeStr;
}

// ===== TIMELINE CHART =====
function initializeTimelineChart() {
    const canvas = document.getElementById('timelineChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth * 2;
    canvas.height = canvas.offsetHeight * 2;
    ctx.scale(2, 2);
    
    const width = canvas.offsetWidth;
    const height = canvas.offsetHeight;
    
    // Data points representing attention states
    // 1 = Focused, 0.5 = Distracted, 0.3 = Relaxed, 0 = Drowsy
    const dataPoints = [
        { time: 0, value: 0.9, state: 'focused' },
        { time: 2, value: 0.95, state: 'focused' },
        { time: 5, value: 0.85, state: 'focused' },
        { time: 8, value: 0.88, state: 'focused' },
        { time: 10, value: 0.6, state: 'distracted' },
        { time: 12, value: 0.55, state: 'distracted' },
        { time: 15, value: 0.85, state: 'focused' },
        { time: 18, value: 0.9, state: 'focused' },
        { time: 20, value: 0.3, state: 'relaxed' },
        { time: 22, value: 0.35, state: 'relaxed' },
        { time: 25, value: 0.92, state: 'focused' },
        { time: 28, value: 0.88, state: 'focused' },
        { time: 30, value: 0.9, state: 'focused' }
    ];
    
    let animationProgress = 0;
    
    function drawChart() {
        ctx.clearRect(0, 0, width, height);
        
        // Draw grid
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = (height / 4) * i;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }
        
        // Draw gradient fill
        const gradient = ctx.createLinearGradient(0, 0, 0, height);
        gradient.addColorStop(0, 'rgba(102, 126, 234, 0.3)');
        gradient.addColorStop(0.5, 'rgba(118, 75, 162, 0.2)');
        gradient.addColorStop(1, 'rgba(240, 147, 251, 0.1)');
        
        ctx.beginPath();
        ctx.moveTo(0, height);
        
        dataPoints.forEach((point, index) => {
            if (index / dataPoints.length <= animationProgress) {
                const x = (point.time / 30) * width;
                const y = height - (point.value * height);
                
                if (index === 0) {
                    ctx.lineTo(x, y);
                } else {
                    const prevPoint = dataPoints[index - 1];
                    const prevX = (prevPoint.time / 30) * width;
                    const prevY = height - (prevPoint.value * height);
                    
                    const cpX = (prevX + x) / 2;
                    ctx.quadraticCurveTo(cpX, prevY, x, y);
                }
            }
        });
        
        ctx.lineTo(width, height);
        ctx.closePath();
        ctx.fillStyle = gradient;
        ctx.fill();
        
        // Draw line
        ctx.beginPath();
        dataPoints.forEach((point, index) => {
            if (index / dataPoints.length <= animationProgress) {
                const x = (point.time / 30) * width;
                const y = height - (point.value * height);
                
                if (index === 0) {
                    ctx.moveTo(x, y);
                } else {
                    const prevPoint = dataPoints[index - 1];
                    const prevX = (prevPoint.time / 30) * width;
                    const prevY = height - (prevPoint.value * height);
                    
                    const cpX = (prevX + x) / 2;
                    ctx.quadraticCurveTo(cpX, prevY, x, y);
                }
            }
        });
        
        const lineGradient = ctx.createLinearGradient(0, 0, width, 0);
        lineGradient.addColorStop(0, '#10b981');
        lineGradient.addColorStop(0.3, '#3b82f6');
        lineGradient.addColorStop(0.6, '#8b5cf6');
        lineGradient.addColorStop(1, '#f59e0b');
        
        ctx.strokeStyle = lineGradient;
        ctx.lineWidth = 3;
        ctx.stroke();
        
        // Draw points
        dataPoints.forEach((point, index) => {
            if (index / dataPoints.length <= animationProgress) {
                const x = (point.time / 30) * width;
                const y = height - (point.value * height);
                
                // Outer glow
                const glowGradient = ctx.createRadialGradient(x, y, 0, x, y, 10);
                glowGradient.addColorStop(0, getStateColor(point.state, 0.5));
                glowGradient.addColorStop(1, 'transparent');
                
                ctx.beginPath();
                ctx.arc(x, y, 10, 0, Math.PI * 2);
                ctx.fillStyle = glowGradient;
                ctx.fill();
                
                // Point
                ctx.beginPath();
                ctx.arc(x, y, 5, 0, Math.PI * 2);
                ctx.fillStyle = getStateColor(point.state, 1);
                ctx.fill();
                
                // Inner point
                ctx.beginPath();
                ctx.arc(x, y, 2, 0, Math.PI * 2);
                ctx.fillStyle = '#ffffff';
                ctx.fill();
            }
        });
        
        if (animationProgress < 1) {
            animationProgress += 0.01;
            requestAnimationFrame(drawChart);
        }
    }
    
    drawChart();
}

function getStateColor(state, alpha = 1) {
    const colors = {
        'focused': `rgba(16, 185, 129, ${alpha})`,
        'distracted': `rgba(245, 158, 11, ${alpha})`,
        'relaxed': `rgba(139, 92, 246, ${alpha})`,
        'drowsy': `rgba(99, 102, 241, ${alpha})`
    };
    return colors[state] || `rgba(102, 126, 234, ${alpha})`;
}

// ===== BRAIN WAVE CHART =====
function initializeBrainWaveChart() {
    const canvas = document.getElementById('brainWaveChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const container = canvas.parentElement;
    
    // Use container width to prevent overflow
    const containerWidth = container.offsetWidth;
    const containerHeight = container.offsetHeight;
    
    canvas.width = containerWidth * 2;  // 2x for retina display
    canvas.height = containerHeight * 2;
    ctx.scale(2, 2);
    
    const width = containerWidth;
    const height = containerHeight;
    
    let offset = 0;
    
    function drawWaves() {
        ctx.clearRect(0, 0, width, height);
        
        // Grid lines for reference
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
        ctx.lineWidth = 1;
        for (let i = 1; i < 4; i++) {
            const y = (height / 4) * i;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }
        
        const waves = [
            { color: '#f59e0b', frequency: 0.01, amplitude: Math.min(30, height/10), offset: height * 0.10, name: 'Delta' },
            { color: '#8b5cf6', frequency: 0.015, amplitude: Math.min(25, height/12), offset: height * 0.28, name: 'Theta' },
            { color: '#10b981', frequency: 0.02, amplitude: Math.min(20, height/15), offset: height * 0.46, name: 'Alpha' },
            { color: '#3b82f6', frequency: 0.04, amplitude: Math.min(15, height/20), offset: height * 0.64, name: 'Beta' },
            { color: '#ec4899', frequency: 0.06, amplitude: Math.min(12, height/25), offset: height * 0.82, name: 'Gamma' }
        ];
        
        waves.forEach(wave => {
            ctx.beginPath();
            ctx.strokeStyle = wave.color;
            ctx.lineWidth = 2;
            
            for (let x = 0; x < width; x++) {
                const y = wave.offset + 
                         Math.sin((x + offset) * wave.frequency) * wave.amplitude +
                         Math.sin((x + offset) * wave.frequency * 2) * (wave.amplitude / 2);
                
                // Clamp Y to stay within canvas bounds
                const clampedY = Math.max(0, Math.min(height, y));
                
                if (x === 0) {
                    ctx.moveTo(x, clampedY);
                } else {
                    ctx.lineTo(x, clampedY);
                }
            }
            
            ctx.stroke();
            
            // Glow effect
            ctx.shadowBlur = 10;
            ctx.shadowColor = wave.color;
            ctx.stroke();
            ctx.shadowBlur = 0;
        });
        
        offset += 2;
        animationFrameId = requestAnimationFrame(drawWaves);
    }
    
    drawWaves();
}

// ===== METRIC CIRCLES =====
function initializeMetricCircles() {
    const metricCircles = document.querySelectorAll('.metric-circle');
    
    metricCircles.forEach(circle => {
        const percent = circle.getAttribute('data-percent');
        const progressCircle = circle.querySelector('.metric-progress');
        const textElement = circle.querySelector('.metric-text');
        
        if (progressCircle) {
            const radius = 50;
            const circumference = 2 * Math.PI * radius;
            const offset = circumference - (percent / 100) * circumference;
            
            // Add gradient definition
            const svg = circle.querySelector('.metric-svg');
            const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
            const gradient = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
            gradient.setAttribute('id', `gradient-${Math.random()}`);
            gradient.setAttribute('x1', '0%');
            gradient.setAttribute('y1', '0%');
            gradient.setAttribute('x2', '100%');
            gradient.setAttribute('y2', '100%');
            
            const stop1 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
            stop1.setAttribute('offset', '0%');
            stop1.setAttribute('style', 'stop-color:#667eea;stop-opacity:1');
            
            const stop2 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
            stop2.setAttribute('offset', '100%');
            stop2.setAttribute('style', 'stop-color:#f093fb;stop-opacity:1');
            
            gradient.appendChild(stop1);
            gradient.appendChild(stop2);
            defs.appendChild(gradient);
            svg.insertBefore(defs, svg.firstChild);
            
            progressCircle.setAttribute('stroke', `url(#${gradient.id})`);
            
            // Animate
            setTimeout(() => {
                progressCircle.style.strokeDashoffset = offset;
            }, 100);
            
            // Animate number
            animateNumber(textElement, 0, percent, 2000);
        }
    });
}

// ===== ANIMATED PARTICLES =====
function initializeParticles() {
    const particlesContainer = document.querySelector('.particles');
    if (!particlesContainer) return;
    
    for (let i = 0; i < 20; i++) {
        const particle = document.createElement('div');
        particle.style.position = 'absolute';
        particle.style.width = Math.random() * 4 + 2 + 'px';
        particle.style.height = particle.style.width;
        particle.style.borderRadius = '50%';
        particle.style.background = 'rgba(102, 126, 234, 0.5)';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.top = Math.random() * 100 + '%';
        particle.style.animation = `particleFloat ${Math.random() * 10 + 10}s ease-in-out infinite`;
        particle.style.animationDelay = Math.random() * 5 + 's';
        particle.style.filter = 'blur(1px)';
        
        particlesContainer.appendChild(particle);
    }
    
    // Add particle animation keyframes
    const style = document.createElement('style');
    style.textContent = `
        @keyframes particleFloat {
            0%, 100% {
                transform: translate(0, 0);
                opacity: 0;
            }
            10% {
                opacity: 1;
            }
            90% {
                opacity: 1;
            }
            50% {
                transform: translate(${Math.random() * 100 - 50}px, ${Math.random() * 100 - 50}px);
            }
        }
    `;
    document.head.appendChild(style);
}

// ===== NUMBER ANIMATION =====
function animateNumber(element, start, end, duration, suffix = '') {
    if (!element) return;
    
    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
            current = end;
            clearInterval(timer);
        }
        element.textContent = Math.round(current) + suffix;
    }, 16);
}

function animateNumbers() {
    const observerOptions = {
        threshold: 0.5,
        rootMargin: '0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const element = entry.target;
                const targetText = element.textContent;
                const targetNumber = parseInt(targetText);
                
                if (!isNaN(targetNumber)) {
                    animateNumber(element, 0, targetNumber, 1500);
                    observer.unobserve(element);
                }
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.stat-value, .breakdown-value').forEach(el => {
        observer.observe(el);
    });
}

// ===== NAVIGATION =====
function initializeNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            // Don't prevent default - let the link work
            // Just add visual effects
            
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            // Add ripple effect
            const ripple = document.createElement('div');
            ripple.style.position = 'absolute';
            ripple.style.borderRadius = '50%';
            ripple.style.background = 'rgba(102, 126, 234, 0.5)';
            ripple.style.width = ripple.style.height = '0';
            ripple.style.top = '50%';
            ripple.style.left = '50%';
            ripple.style.transform = 'translate(-50%, -50%)';
            ripple.style.pointerEvents = 'none';
            ripple.style.animation = 'ripple 0.6s ease-out';
            
            link.style.position = 'relative';
            link.appendChild(ripple);
            
            setTimeout(() => ripple.remove(), 600);
        });
    });
    
    // Add ripple animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes ripple {
            to {
                width: 200px;
                height: 200px;
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}

// ===== FLOATING ACTION BUTTON =====
// Removed - No longer used

// ===== ADD STUDENT MODAL =====
function openAddStudentModal() {
    const modal = document.getElementById('addStudentModal');
    if (modal) {
        modal.style.display = 'flex';
        // Reset form
        document.getElementById('addStudentForm').reset();
        // Focus on first input
        setTimeout(() => {
            document.getElementById('studentFirstName').focus();
        }, 100);
    }
}

function closeAddStudentModal() {
    const modal = document.getElementById('addStudentModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

window.openAddStudentModal = openAddStudentModal;
window.closeAddStudentModal = closeAddStudentModal;

function addNewStudent(event) {
    event.preventDefault();
    
    const firstName = document.getElementById('studentFirstName').value.trim();
    const lastName = document.getElementById('studentLastName').value.trim();
    
    if (!firstName || !lastName) {
        alert('Please enter both first and last name');
        return;
    }
    
    // Generate new student ID
    const newId = `STU${String(studentsData.length + 1).padStart(3, '0')}`;
    
    // Create new student object
    const mentalStates = ['distracted', 'drowsy', 'relaxed', 'focused'];
    const newStudent = {
        id: newId,
        name: `${firstName} ${lastName}`,
        state: mentalStates[Math.floor(Math.random() * mentalStates.length)],
        alpha: Math.floor(Math.random() * 40) + 30,
        beta: Math.floor(Math.random() * 40) + 30,
        gamma: Math.floor(Math.random() * 30) + 20,
        theta: Math.floor(Math.random() * 30) + 20
    };
    
    // Add to students array
    studentsData.push(newStudent);
    
    // Re-sort by state priority
    const statePriority = { distracted: 0, drowsy: 1, relaxed: 2, focused: 3 };
    studentsData.sort((a, b) => statePriority[a.state] - statePriority[b.state]);
    
    // Re-render the student lists
    renderStudentLists();
    
    // Close modal
    closeAddStudentModal();
    
    // Show success notification
    showNotification(`Student ${firstName} ${lastName} added successfully!`);
}

window.addNewStudent = addNewStudent;

// Close modal when clicking outside
document.addEventListener('click', (e) => {
    const modal = document.getElementById('addStudentModal');
    if (modal && e.target === modal) {
        closeAddStudentModal();
    }
});

// ===== NOTIFICATION SYSTEM =====
function showNotification(message) {
    const notification = document.createElement('div');
    notification.style.position = 'fixed';
    notification.style.top = '100px';
    notification.style.right = '2rem';
    notification.style.background = 'rgba(17, 24, 39, 0.95)';
    notification.style.backdropFilter = 'blur(20px)';
    notification.style.border = '1px solid rgba(102, 126, 234, 0.3)';
    notification.style.borderRadius = '16px';
    notification.style.padding = '1.5rem 2rem';
    notification.style.color = 'white';
    notification.style.boxShadow = '0 10px 40px rgba(0, 0, 0, 0.5)';
    notification.style.zIndex = '10000';
    notification.style.minWidth = '300px';
    notification.style.animation = 'slideInRight 0.4s ease-out';
    notification.innerHTML = `
        <div style="display: flex; align-items: center; gap: 1rem;">
            <div style="font-size: 2rem;">✓</div>
            <div>
                <div style="font-weight: 700; margin-bottom: 0.25rem;">Success!</div>
                <div style="color: #d1d5db; font-size: 0.9rem;">${message}</div>
            </div>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.4s ease-out';
        setTimeout(() => notification.remove(), 400);
    }, 3000);
}

// ===== SCROLL ANIMATIONS =====
const scrollObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
});

document.querySelectorAll('.glass-card').forEach(card => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(30px)';
    card.style.transition = 'all 0.6s ease-out';
    scrollObserver.observe(card);
});

// ===== PERFORMANCE MONITORING =====
console.log('%c🧠 Bracon EEG Monitoring System', 
    'font-size: 20px; font-weight: bold; color: #667eea; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);');
console.log('%cSystem Status: Online ✓', 
    'font-size: 14px; color: #10b981;');
console.log('%cDeveloped with ❤️ for classroom attention monitoring', 
    'font-size: 12px; color: #9ca3af;');

// ===== KEYBOARD SHORTCUTS =====
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K for search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        console.log('Search shortcut activated');
    }
    
    // Esc to close modals
    if (e.key === 'Escape') {
        console.log('Escape key pressed');
    }
});

// ===== CLEANUP ON UNLOAD =====
window.addEventListener('beforeunload', () => {
    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
    }
});

// ===== REAL-TIME DATA SIMULATION =====
function simulateRealTimeData() {
    setInterval(() => {
        // Simulate confidence changes
        const confidenceElement = document.querySelector('.status-value:not(.focused)');
        if (confidenceElement && confidenceElement.textContent.includes('%')) {
            const currentValue = parseInt(confidenceElement.textContent);
            const newValue = Math.max(80, Math.min(95, currentValue + Math.floor(Math.random() * 5 - 2)));
            confidenceElement.textContent = newValue + '%';
        }
        
        // Update connection status
        const connectionDot = document.querySelector('.connection-dot');
        if (connectionDot) {
            connectionDot.style.opacity = Math.random() > 0.1 ? '1' : '0.5';
        }
    }, 3000);
}

// Start real-time simulation
simulateRealTimeData();

// ===== TEACHER INFO LOADER =====
function loadTeacherInfo() {
    const teacherName = localStorage.getItem('teacherName') || 'Teacher';
    const subjectName = localStorage.getItem('subjectName') || 'Subject';
    
    const teacherNameElement = document.getElementById('teacherName');
    const subjectNameElement = document.getElementById('subjectName');
    
    if (teacherNameElement) teacherNameElement.textContent = teacherName;
    if (subjectNameElement) subjectNameElement.textContent = subjectName;
}

// ===== STUDENTS DASHBOARD =====
function initializeStudentsDashboard() {
    // Load real students from database
    loadStudentsFromDatabase();
}

async function loadStudentsFromDatabase() {
    try {
        console.log('🔍 Fetching students from API...');
        const response = await fetch('/api/students-list');
        const data = await response.json();
        
        console.log('📊 API Response:', data);
        
        if (data.status === 'success') {
            console.log(`✅ Received ${data.students.length} students`);
            
            // Show ALL students initially (for debugging)
            studentsData = data.students;
            console.log('📋 All students:', studentsData);
            
            // Filter only connected ones for display
            const connectedStudents = studentsData.filter(s => s.state !== 'disconnected');
            console.log(`🟢 Connected students: ${connectedStudents.length}`, connectedStudents);
            
            // Use connected students for display
            studentsData = connectedStudents;
            
            // Sort students by state priority (distracted first)
            const statePriority = { distracted: 0, drowsy: 1, relaxed: 2, focused: 3 };
            studentsData.sort((a, b) => statePriority[a.state] - statePriority[b.state]);
            
            renderStudentLists();
            startRealTimeUpdates();
        } else {
            console.error('❌ Failed to load students:', data.msg);
        }
    } catch (error) {
        console.error('💥 Error loading students:', error);
    }
}

// Check if student was selected from another page
function checkForSelectedStudent() {
    // Check for student ID (old method)
    const selectedStudentId = localStorage.getItem('selectedStudentId');
    // Check for MAC address (new method from students page)
    const selectedStudentMac = localStorage.getItem('selectedStudentMac');
    
    if (selectedStudentMac) {
        // Priority to MAC address
        console.log('🔍 Looking for student with MAC:', selectedStudentMac);
        
        // Wait for students data to load
        const checkInterval = setInterval(() => {
            if (studentsData && studentsData.length > 0) {
                clearInterval(checkInterval);
                
                const student = studentsData.find(s => s.mac_address === selectedStudentMac);
                if (student) {
                    console.log('✅ Found student:', student.name);
                    setTimeout(() => {
                        showIndividualDashboard(student);
                    }, 500);
                } else {
                    console.warn('⚠️ Student not found with MAC:', selectedStudentMac);
                }
                
                // Clear localStorage
                localStorage.removeItem('selectedStudentMac');
                localStorage.removeItem('selectedStudentName');
                localStorage.removeItem('selectedStudentId');
            }
        }, 100); // Check every 100ms
        
        // Timeout after 5 seconds
        setTimeout(() => {
            clearInterval(checkInterval);
        }, 5000);
        
    } else if (selectedStudentId) {
        // Fallback to ID method
        const student = studentsData.find(s => s.id == selectedStudentId);
        if (student) {
            setTimeout(() => {
                showIndividualDashboard(student);
            }, 500);
        }
        localStorage.removeItem('selectedStudentId');
    }
}

function renderStudentLists() {
    const leftList = document.getElementById('leftStudentList');
    const rightList = document.getElementById('rightStudentList');
    
    if (!leftList || !rightList) return;
    
    // Safety check for studentsData
    if (!studentsData || !Array.isArray(studentsData)) {
        console.warn('studentsData is not valid:', studentsData);
        return;
    }
    
    leftList.innerHTML = '';
    rightList.innerHTML = '';
    
    studentsData.forEach((student, index) => {
        // Safety check for student object
        if (!student || !student.name || !student.state) {
            console.warn('Invalid student object:', student);
            return;
        }
        
        const studentElement = createStudentElement(student);
        
        if (index < 5) {
            leftList.appendChild(studentElement);
        } else {
            rightList.appendChild(studentElement);
        }
    });
}

function createStudentElement(student) {
    const div = document.createElement('div');
    div.className = `student-item state-${student.state}`;
    div.onclick = () => showIndividualDashboard(student);
    
    const stateIcons = {
        distracted: '😵',
        drowsy: '😴',
        relaxed: '😌',
        focused: '🎯',
        disconnected: '🔌'
    };
    
    const stateLabels = {
        distracted: 'Distracted',
        drowsy: 'Drowsy',
        relaxed: 'Relaxed',
        focused: 'Focused',
        disconnected: 'Disconnected'
    };
    
    // Get icon and label with fallback
    const icon = stateIcons[student.state] || '❓';
    const label = stateLabels[student.state] || 'Unknown';
    const studentName = student.name || 'Unknown Student';
    const studentId = student.id || 'N/A';
    
    div.innerHTML = `
        <div class="student-info-left">
            <div class="student-avatar-mini">${studentName.charAt(0)}</div>
            <div class="student-details-mini">
                <h5>${studentName}</h5>
                <span class="student-id-mini">${studentId}</span>
            </div>
        </div>
        <div class="student-state-badge ${student.state}">
            <span class="state-indicator ${student.state}"></span>
            ${icon} ${label}
        </div>
    `;
    
    return div;
}

function showIndividualDashboard(student) {
    selectedStudent = student;
    
    // Hide student list, show individual dashboard
    const studentSection = document.querySelector('.teacher-dashboard-card');
    const individualDashboard = document.getElementById('individualDashboard');
    
    if (studentSection) studentSection.style.display = 'none';
    if (individualDashboard) {
        individualDashboard.style.display = 'block';
        individualDashboard.style.animation = 'fadeInUp 0.6s ease-out';
    }
    
    // Update student name
    const nameElement = document.getElementById('selectedStudentName');
    if (nameElement) nameElement.textContent = `${student.name} - ${student.id}`;
    
    // Draw brain wave circle
    drawBrainWaveCircle(student);
    
    // Update wave percentages
    updateWavePercentages(student);
    
    // Update behavior description
    updateBehaviorDescription(student);
    
    // Update student-specific data
    updateStudentSpecificData(student);
    
    // Re-initialize brain wave chart for individual student with delay to ensure canvas is ready
    setTimeout(() => {
        // Stop any existing brain wave animation
        if (animationFrameId) {
            cancelAnimationFrame(animationFrameId);
        }
        initializeStudentBrainWaveChart();
        initializeMetricCircles();
    }, 200);
}

function updateStudentSpecificData(student) {
    // Update performance metrics
    const focusLevel = document.getElementById('studentFocusLevel');
    const engagement = document.getElementById('studentEngagement');
    if (focusLevel) focusLevel.textContent = student.alpha + '%';
    if (engagement) engagement.textContent = student.beta + '%';
    
    // Update attention span data
    const avgSpan = document.getElementById('avgAttentionSpan');
    const longestSpan = document.getElementById('longestSpan');
    const totalFocus = document.getElementById('totalFocusTime');
    
    const avgMinutes = Math.floor(Math.random() * 8) + 10;
    const longestMinutes = avgMinutes + Math.floor(Math.random() * 5) + 2;
    const totalMinutes = Math.floor(Math.random() * 30) + 30;
    const percentage = Math.floor((totalMinutes / 60) * 100);
    
    if (avgSpan) avgSpan.textContent = `${avgMinutes} minutes`;
    if (longestSpan) longestSpan.textContent = `${longestMinutes} minutes`;
    if (totalFocus) totalFocus.textContent = `${totalMinutes} minutes (${percentage}% of session)`;
    
    // Update recommendation based on state
    const recommendation = document.getElementById('attentionRecommendation');
    const recommendations = {
        distracted: 'Student needs re-engagement. Try interactive activities or visual aids.',
        drowsy: 'Consider a short break or energizing activity to boost alertness.',
        relaxed: 'Good state for creative work. Maintain calm environment.',
        focused: 'Excellent! Continue current methods and introduce challenging concepts.'
    };
    
    if (recommendation) recommendation.textContent = recommendations[student.state];
}

function closeIndividualDashboard() {
    const studentSection = document.querySelector('.teacher-dashboard-card');
    const individualDashboard = document.getElementById('individualDashboard');
    
    if (studentSection) studentSection.style.display = 'block';
    if (individualDashboard) individualDashboard.style.display = 'none';
    
    selectedStudent = null;
    
    // Stop all animations
    if (brainCircleAnimation) {
        cancelAnimationFrame(brainCircleAnimation);
    }
    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
        animationFrameId = null;
    }
}

window.closeIndividualDashboard = closeIndividualDashboard;

// ===== STUDENT-SPECIFIC BRAIN WAVE CHART =====
function initializeStudentBrainWaveChart() {
    const canvas = document.getElementById('brainWaveChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const container = canvas.parentElement;
    
    // Use container dimensions to prevent overflow
    const containerWidth = container.offsetWidth - 32; // Account for padding
    const containerHeight = container.offsetHeight - 32;
    
    canvas.width = containerWidth;
    canvas.height = containerHeight;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    
    const width = containerWidth;
    const height = containerHeight;
    
    let offset = 0;
    
    function drawWaves() {
        // Only draw if canvas is visible and student dashboard is open
        if (!selectedStudent || individualDashboard.style.display === 'none') {
            return;
        }
        
        ctx.clearRect(0, 0, width, height);
        
        // Define ALL 5 waves with different frequencies and amplitudes - properly spaced
        const waves = [
            { 
                color: '#f59e0b', 
                frequency: 0.015, 
                amplitude: Math.min(20, height * 0.15), 
                offset: height * 0.10, 
                name: 'Delta',
                speed: 1
            },
            { 
                color: '#8b5cf6', 
                frequency: 0.02, 
                amplitude: Math.min(18, height * 0.14), 
                offset: height * 0.27, 
                name: 'Theta',
                speed: 1.5
            },
            { 
                color: '#10b981', 
                frequency: 0.03, 
                amplitude: Math.min(15, height * 0.12), 
                offset: height * 0.44, 
                name: 'Alpha',
                speed: 2
            },
            { 
                color: '#3b82f6', 
                frequency: 0.05, 
                amplitude: Math.min(12, height * 0.10), 
                offset: height * 0.61, 
                name: 'Beta',
                speed: 3
            },
            { 
                color: '#ec4899', 
                frequency: 0.08, 
                amplitude: Math.min(10, height * 0.08), 
                offset: height * 0.78, 
                name: 'Gamma',
                speed: 4
            }
        ];
        
        waves.forEach(wave => {
            // Draw the main wave line
            ctx.beginPath();
            ctx.strokeStyle = wave.color;
            ctx.lineWidth = 2.5;
            for (let x = 0; x < width; x++) {
                // Create complex wave pattern with multiple harmonics, keep in frame
                const y = Math.max(0, Math.min(height - 1,
                    wave.offset + Math.sin((x + offset * wave.speed) * wave.frequency) * wave.amplitude +
                    Math.sin((x + offset * wave.speed) * wave.frequency * 2) * (wave.amplitude / 3) +
                    Math.sin((x + offset * wave.speed) * wave.frequency * 0.5) * (wave.amplitude / 4)
                ));
                if (x === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            }
            ctx.stroke();
            // Add glow effect
            ctx.shadowBlur = 15;
            ctx.shadowColor = wave.color;
            ctx.stroke();
            ctx.shadowBlur = 0;
            // Draw subtle fill gradient under the wave
            ctx.beginPath();
            ctx.moveTo(0, Math.max(0, Math.min(height - 1, wave.offset + wave.amplitude * 1.5)));
            for (let x = 0; x < width; x++) {
                const y = Math.max(0, Math.min(height - 1,
                    wave.offset + Math.sin((x + offset * wave.speed) * wave.frequency) * wave.amplitude +
                    Math.sin((x + offset * wave.speed) * wave.frequency * 2) * (wave.amplitude / 3) +
                    Math.sin((x + offset * wave.speed) * wave.frequency * 0.5) * (wave.amplitude / 4)
                ));
                ctx.lineTo(x, y);
            }
            ctx.lineTo(width, Math.max(0, Math.min(height - 1, wave.offset + wave.amplitude * 1.5)));
            ctx.closePath();
            const gradient = ctx.createLinearGradient(0, wave.offset - wave.amplitude, 0, wave.offset + wave.amplitude * 1.5);
            gradient.addColorStop(0, wave.color + '40');
            gradient.addColorStop(1, wave.color + '05');
            ctx.fillStyle = gradient;
            ctx.fill();
        });
        
        offset += 1;
        animationFrameId = requestAnimationFrame(drawWaves);
    }
    
    drawWaves();
}

function drawBrainWaveCircle(student) {
    const canvas = document.getElementById('brainCircleCanvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    canvas.width = 300;
    canvas.height = 300;
    
    const centerX = 150;
    const centerY = 150;
    const radius = 120;
    
    let rotation = 0;
    
    function animate() {
        ctx.clearRect(0, 0, 300, 300);
        
        // Draw outer glow rings
        for (let i = 0; i < 3; i++) {
            const glowRadius = radius + 10 + i * 10;
            const gradient = ctx.createRadialGradient(centerX, centerY, radius, centerX, centerY, glowRadius);
            gradient.addColorStop(0, 'rgba(102, 126, 234, 0.3)');
            gradient.addColorStop(1, 'transparent');
            
            ctx.beginPath();
            ctx.arc(centerX, centerY, glowRadius, 0, Math.PI * 2);
            ctx.strokeStyle = gradient;
            ctx.lineWidth = 2;
            ctx.stroke();
        }
        
        // Draw rotating wave circle
        const waveColors = [
            { color: '#10b981', value: student.alpha / 100 },  // Alpha - Green
            { color: '#3b82f6', value: student.beta / 100 },   // Beta - Blue
            { color: '#ec4899', value: student.gamma / 100 },  // Gamma - Pink
            { color: '#8b5cf6', value: student.theta / 100 }   // Theta - Purple
        ];
        
        waveColors.forEach((wave, index) => {
            const startAngle = (Math.PI * 2 / waveColors.length) * index + rotation;
            const endAngle = startAngle + (Math.PI * 2 / waveColors.length) * 0.9;
            
            const gradient = ctx.createLinearGradient(
                centerX - radius, centerY - radius,
                centerX + radius, centerY + radius
            );
            gradient.addColorStop(0, wave.color);
            gradient.addColorStop(1, wave.color + '80');
            
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius * wave.value, startAngle, endAngle);
            ctx.strokeStyle = gradient;
            ctx.lineWidth = 15;
            ctx.lineCap = 'round';
            ctx.stroke();
            
            // Add glow effect
            ctx.shadowBlur = 20;
            ctx.shadowColor = wave.color;
            ctx.stroke();
            ctx.shadowBlur = 0;
        });
        
        // Draw main circle
        const mainGradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, radius);
        mainGradient.addColorStop(0, 'rgba(102, 126, 234, 0.2)');
        mainGradient.addColorStop(1, 'rgba(118, 75, 162, 0.1)');
        
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
        ctx.fillStyle = mainGradient;
        ctx.fill();
        ctx.strokeStyle = 'rgba(102, 126, 234, 0.5)';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        rotation += 0.01;
        brainCircleAnimation = requestAnimationFrame(animate);
    }
    
    animate();
    
    // Update center icon and text
    const stateIcons = {
        distracted: '😵',
        drowsy: '😴',
        relaxed: '😌',
        focused: '🎯'
    };
    
    const stateLabels = {
        distracted: 'Distracted',
        drowsy: 'Drowsy',
        relaxed: 'Relaxed',
        focused: 'Focused'
    };
    
    const iconElement = document.getElementById('stateIcon');
    const textElement = document.getElementById('stateText');
    
    if (iconElement) iconElement.textContent = stateIcons[student.state];
    if (textElement) textElement.textContent = stateLabels[student.state];
}

function updateWavePercentages(student) {
    // Safety check
    if (!student) {
        console.warn('updateWavePercentages: student is null or undefined');
        return;
    }
    
    const waves = [
        { id: 'alpha', value: student.alpha || 0 },
        { id: 'beta', value: student.beta || 0 },
        { id: 'gamma', value: student.gamma || 0 },
        { id: 'theta', value: student.theta || 0 }
    ];
    
    waves.forEach(wave => {
        const valueElement = document.getElementById(`${wave.id}Value`);
        const barElement = document.getElementById(`${wave.id}Bar`);
        
        if (valueElement) {
            animateNumber(valueElement, 0, wave.value, 1500, '%');
        }
        
        if (barElement) {
            setTimeout(() => {
                barElement.style.width = wave.value + '%';
            }, 100);
        }
    });
}

function updateBehaviorDescription(student) {
    const stateDescriptions = {
        distracted: {
            state: 'The student is currently in a distracted state with low attention levels.',
            recommendation: 'Consider engaging the student with interactive activities, visual aids, or short breaks to improve focus.',
            pattern: 'Student shows better concentration during hands-on activities and interactive sessions.'
        },
        drowsy: {
            state: 'The student appears drowsy with reduced alertness and cognitive activity.',
            recommendation: 'Suggest physical movement, fresh air, or a brief energizing activity. Check if adequate rest is being obtained.',
            pattern: 'Drowsiness often occurs during passive learning. Increase engagement with active participation.'
        },
        relaxed: {
            state: 'The student is in a relaxed state with balanced brain activity.',
            recommendation: 'This is a good state for creative thinking. Encourage brainstorming and open-ended problem solving.',
            pattern: 'Student performs well in relaxed environments. Maintain a calm, supportive atmosphere.'
        },
        focused: {
            state: 'The student is highly focused with optimal attention and engagement levels.',
            recommendation: 'Excellent state for learning! Continue with current teaching methods and introduce challenging concepts.',
            pattern: 'Student maintains focus well during structured activities with clear objectives.'
        }
    };
    
    const description = stateDescriptions[student.state];
    
    const stateElement = document.getElementById('behaviorState');
    const recommendationElement = document.getElementById('behaviorRecommendation');
    const patternElement = document.getElementById('behaviorPattern');
    
    if (stateElement) stateElement.textContent = description.state;
    if (recommendationElement) recommendationElement.textContent = description.recommendation;
    if (patternElement) patternElement.textContent = description.pattern;
}

function startRealTimeUpdates() {
    // Update immediately on start
    updateStudentData();
    
    // Then update every 2 seconds for real-time monitoring
    setInterval(updateStudentData, 2000);
}

async function updateStudentData() {
    try {
        const response = await fetch('/api/students-list');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'success' && data.students && Array.isArray(data.students)) {
            // Update all students data (including disconnected ones)
            studentsData = data.students;
            
            // Sort: disconnected last, then by state priority
            const statePriority = { 
                distracted: 0, 
                drowsy: 1, 
                relaxed: 2, 
                focused: 3,
                disconnected: 4 
            };
            studentsData.sort((a, b) => {
                const priorityA = statePriority[a.state] || 4;
                const priorityB = statePriority[b.state] || 4;
                return priorityA - priorityB;
            });
            
            renderStudentLists();
            
            // Update individual dashboard if viewing a student
            if (selectedStudent && selectedStudent.id) {
                const updatedStudent = studentsData.find(s => s.id === selectedStudent.id);
                if (updatedStudent) {
                    selectedStudent = updatedStudent;
                    updateDashboardWithStudentData(updatedStudent);
                } else {
                    // Student no longer exists or is disconnected
                    console.warn('Selected student not found in updated data');
                }
            }
        } else {
            console.warn('Invalid response format:', data);
        }
    } catch (error) {
        console.error('Error updating student data:', error);
        // Don't spam errors - maybe device is temporarily offline
    }
}

function updateDashboardWithStudentData(student) {
    // Update wave percentages
    updateWavePercentages(student);
    
    // Update behavior description
    updateBehaviorDescription(student);
    
    // Update state icon and text
    const iconElement = document.getElementById('stateIcon');
    const textElement = document.getElementById('stateText');
    
    const stateIcons = {
        distracted: '😵',
        drowsy: '😴',
        relaxed: '😌',
        focused: '🎯',
        disconnected: '🔌'
    };
    
    const stateLabels = {
        distracted: 'Distracted',
        drowsy: 'Drowsy',
        relaxed: 'Relaxed',
        focused: 'Focused',
        disconnected: 'Disconnected'
    };
    
    if (iconElement) iconElement.textContent = stateIcons[student.state] || '❓';
    if (textElement) textElement.textContent = stateLabels[student.state] || 'Unknown';
    
    // Update connection status indicator if it exists
    const connectionIndicator = document.querySelector('.connection-status');
    if (connectionIndicator) {
        if (student.connected) {
            connectionIndicator.textContent = '🟢 Connected';
            connectionIndicator.style.color = '#10b981';
        } else {
            connectionIndicator.textContent = '🔴 Disconnected';
            connectionIndicator.style.color = '#ef4444';
        }
    }
    
    // Update focus percentage display
    const focusElement = document.querySelector('.focus-percentage');
    if (focusElement && student.focus !== undefined) {
        focusElement.textContent = `${Math.round(student.focus)}%`;
    }
}

// ===== EXPORT FUNCTIONS =====
window.braconApp = {
    // Session Management
    startNewSession: () => {
        console.log('Starting new session...');
        showNotification('New monitoring session started successfully!');
        setTimeout(() => {
            if (confirm('Would you like to navigate to the dashboard?')) {
                window.location.href = 'index.html';
            }
        }, 1500);
    },
    
    endSession: () => {
        console.log('Ending session...');
        if (confirm('Are you sure you want to end the current session?')) {
            showNotification('Session ended successfully');
            setTimeout(() => {
                window.location.href = 'session-history.html';
            }, 1500);
        }
    },

    startSession: (studentName) => {
        console.log(`Starting session for ${studentName}...`);
        showNotification(`Starting monitoring session for ${studentName}...`);
        setTimeout(() => {
            window.location.href = 'index.html';
        }, 1500);
    },

    // Data Export
    exportData: () => {
        console.log('Exporting data...');
        showNotification('Exporting current session data...');
        setTimeout(() => {
            const data = {
                student: 'Rahul',
                session_id: 'SESSION-' + Date.now(),
                focus_time: '38 minutes',
                quality_score: 85,
                confidence: '87%',
                timestamp: new Date().toISOString()
            };
            const dataStr = JSON.stringify(data, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'bracon-session-data.json';
            link.click();
            showNotification('Data exported successfully!');
        }, 1000);
    },

    exportSession: (sessionId) => {
        console.log(`Exporting session ${sessionId}...`);
        showNotification(`Exporting session ${sessionId}...`);
        setTimeout(() => {
            showNotification('Session data exported successfully!');
        }, 1000);
    },

    exportAllSessions: () => {
        console.log('Exporting all sessions...');
        showNotification('Preparing to export all session data...');
        setTimeout(() => {
            showNotification('All sessions exported successfully!');
        }, 1500);
    },

    exportAllData: () => {
        console.log('Exporting all student data...');
        showNotification('Exporting all student data...');
        setTimeout(() => {
            showNotification('All data exported successfully!');
        }, 1500);
    },

    // Report Functions
    sendReport: () => {
        console.log('Sending report...');
        const email = prompt('Enter email address to send report:');
        if (email) {
            showNotification(`Sending report to ${email}...`);
            setTimeout(() => {
                showNotification('Report sent successfully!');
            }, 1500);
        }
    },

    shareSession: (sessionId) => {
        console.log(`Sharing session ${sessionId}...`);
        const email = prompt('Enter email address to share session:');
        if (email) {
            showNotification(`Sharing session with ${email}...`);
            setTimeout(() => {
                showNotification('Session shared successfully!');
            }, 1500);
        }
    },

    // Session History Functions
    viewSessionDetails: (sessionId) => {
        console.log(`Viewing details for ${sessionId}...`);
        showNotification(`Loading session details...`);
        setTimeout(() => {
            window.location.href = 'index.html';
        }, 1000);
    },

    retrySession: (sessionId) => {
        console.log(`Retrying session ${sessionId}...`);
        if (confirm('Would you like to start a new session?')) {
            showNotification('Starting new session...');
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 1500);
        }
    },

    loadMoreSessions: () => {
        console.log('Loading more sessions...');
        showNotification('Loading previous sessions...');
        setTimeout(() => {
            showNotification('No more sessions to load');
        }, 1500);
    },

    // Filter Functions
    applyFilters: () => {
        const studentFilter = document.getElementById('studentFilter')?.value;
        const dateFilter = document.getElementById('dateFilter')?.value;
        const statusFilter = document.getElementById('statusFilter')?.value;
        
        console.log('Applying filters:', { studentFilter, dateFilter, statusFilter });
        showNotification('Filters applied successfully!');
    },

    // Student Management
    addNewStudent: () => {
        console.log('Adding new student...');
        const name = prompt('Enter student name:');
        if (name) {
            const studentId = prompt('Enter student ID:');
            if (studentId) {
                showNotification(`Adding student ${name}...`);
                setTimeout(() => {
                    showNotification(`${name} added successfully!`);
                }, 1500);
            }
        }
    },

    viewHistory: (studentName) => {
        console.log(`Viewing history for ${studentName}...`);
        showNotification(`Loading ${studentName}'s session history...`);
        setTimeout(() => {
            window.location.href = 'session-history.html';
        }, 1000);
    },

    // Student-specific actions
    viewStudentHistory: () => {
        if (selectedStudent) {
            console.log(`Viewing history for ${selectedStudent.name}...`);
            showNotification(`Loading ${selectedStudent.name}'s session history...`);
            setTimeout(() => {
                window.location.href = 'session-history.html';
            }, 1000);
        }
    },

    exportStudentData: () => {
        if (selectedStudent) {
            console.log(`Exporting data for ${selectedStudent.name}...`);
            showNotification(`Exporting ${selectedStudent.name}'s data...`);
            setTimeout(() => {
                const data = {
                    student: selectedStudent.name,
                    student_id: selectedStudent.id,
                    state: selectedStudent.state,
                    alpha: selectedStudent.alpha,
                    beta: selectedStudent.beta,
                    gamma: selectedStudent.gamma,
                    theta: selectedStudent.theta,
                    timestamp: new Date().toISOString()
                };
                const dataStr = JSON.stringify(data, null, 2);
                const dataBlob = new Blob([dataStr], { type: 'application/json' });
                const url = URL.createObjectURL(dataBlob);
                const link = document.createElement('a');
                link.href = url;
                link.download = `${selectedStudent.id}-data.json`;
                link.click();
                showNotification('Data exported successfully!');
            }, 1000);
        }
    },

    startStudentSession: () => {
        if (selectedStudent) {
            console.log(`Starting new session for ${selectedStudent.name}...`);
            showNotification(`Starting monitoring session for ${selectedStudent.name}...`);
        }
    },

    sendStudentReport: () => {
        if (selectedStudent) {
            const email = prompt('Enter email address to send report:');
            if (email) {
                showNotification(`Sending ${selectedStudent.name}'s report to ${email}...`);
                setTimeout(() => {
                    showNotification('Report sent successfully!');
                }, 1500);
            }
        }
    }
};

// ===== END SESSION FUNCTION =====
function endSession() {
    const confirmEnd = confirm('Are you sure you want to end this session? All current data will be saved.');
    if (confirmEnd) {
        showNotification('Session ended successfully!');
        setTimeout(() => {
            window.location.href = '/students-page';
        }, 1000);
    }
}

window.endSession = endSession;

