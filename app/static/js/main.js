function openModal(modalId) {
    var modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function closeModal(modalId) {
    var modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

function openDayModal(date, notes) {
    document.getElementById('modal-date').value = date;
    document.getElementById('modal-date-not-studied').value = date;
    document.getElementById('modal-notes').value = notes || '';
    openModal('day-modal');
}

document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('active');
    }
});

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal.active').forEach(function(modal) {
            modal.classList.remove('active');
        });
    }
});

setTimeout(function() {
    var celebration = document.getElementById('celebration');
    if (celebration) {
        celebration.style.opacity = '0';
        setTimeout(function() {
            celebration.remove();
        }, 300);
    }
}, 3000);
