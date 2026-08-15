(function() {
    'use strict';

    var startTime = Date.now();
    var el = null;
    var rafId = null;
    var hidden = false;

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
            el.textContent = fmt(Date.now() - startTime);
        }
        rafId = requestAnimationFrame(tick);
    }

    function onVisibility() {
        if (document.hidden) {
            hidden = true;
            if (el) el.style.opacity = '0.15';
        } else {
            hidden = false;
            if (el) el.style.opacity = '0.4';
        }
    }

    create();
    document.addEventListener('visibilitychange', onVisibility);
    tick();
})();
