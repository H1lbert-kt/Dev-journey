(function() {
    'use strict';

    var pageStartTime = Date.now();
    var el = null;
    var hidden = false;
    var studyMode = false;
    var studySeconds = 0;
    var studyRunning = false;

    function create() {
        el = document.createElement('div');
        el.id = 'session-timer';
        el.style.cssText = [
            'position:fixed',
            'bottom:12px',
            'right:12px',
            'font-family:"Courier New",monospace',
            'font-size:12px',
            'letter-spacing:0.5px',
            'color:rgba(255,255,255,0.4)',
            'background:rgba(255,255,255,0.04)',
            'backdrop-filter:blur(4px)',
            '-webkit-backdrop-filter:blur(4px)',
            'padding:4px 8px',
            'border-radius:4px',
            'z-index:9999',
            'pointer-events:none',
            'transition:opacity 0.4s ease',
            'user-select:none',
            'opacity:0.4'
        ].join(';');
        el.textContent = '00:00';
        document.body.appendChild(el);
    }

    function fmt(ms) {
        var total = Math.floor(ms / 1000);
        var h = Math.floor(total / 3600);
        var m = Math.floor((total % 3600) / 60);
        var s = total % 60;
        var pad = function(n) { return n < 10 ? '0' + n : '' + n; };
        if (h > 0) return pad(h) + ':' + pad(m) + ':' + pad(s);
        return pad(m) + ':' + pad(s);
    }

    function tick() {
        if (!hidden && el) {
            if (studyMode) {
                el.textContent = fmt(studySeconds * 1000);
            } else {
                el.textContent = fmt(Date.now() - pageStartTime);
            }
        }
    }

    function onVisibility() {
        if (document.hidden) {
            hidden = true;
            if (el) el.style.opacity = '0.15';
        } else {
            hidden = false;
            if (el) el.style.opacity = '0.4';
            tick();
        }
    }

    function onStorage(e) {
        if (e.key === 'ftState') {
            try {
                var state = JSON.parse(e.newValue || 'null');
                if (state && state.seconds > 0) {
                    studyMode = true;
                    studyRunning = !!state.running;
                    if (state.running && state.startTime > 0) {
                        studySeconds = Math.floor((Date.now() - state.startTime) / 1000);
                    } else {
                        studySeconds = state.seconds;
                    }
                } else {
                    studyMode = false;
                    studySeconds = 0;
                }
            } catch(err) {
                studyMode = false;
                studySeconds = 0;
            }
        }
    }

    function onBroadcast(e) {
        if (e.data && e.data.type === 'state') {
            studyMode = true;
            studyRunning = e.data.running || false;
            if (e.data.running && e.data.startTime > 0) {
                studySeconds = Math.floor((Date.now() - e.data.startTime) / 1000);
            } else {
                studySeconds = e.data.seconds || 0;
            }
        } else if (e.data && e.data.type === 'stop') {
            studyMode = false;
            studySeconds = 0;
        }
    }

    function init() {
        try {
            var state = JSON.parse(localStorage.getItem('ftState') || 'null');
            if (state && state.seconds > 0) {
                studyMode = true;
                studyRunning = !!state.running;
                if (state.running && state.startTime > 0) {
                    studySeconds = Math.floor((Date.now() - state.startTime) / 1000);
                } else {
                    studySeconds = state.seconds;
                }
            }
        } catch(e) {}

        create();
        document.addEventListener('visibilitychange', onVisibility);
        window.addEventListener('storage', onStorage);

        if (typeof BroadcastChannel !== 'undefined') {
            var channel = new BroadcastChannel('devjourney-timer');
            channel.onmessage = onBroadcast;
        }

        tick();
        setInterval(tick, 1000);
    }

    init();
})();
