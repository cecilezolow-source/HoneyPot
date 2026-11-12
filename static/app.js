/* HoneyPot – kleine Interaktionen fürs Frontend (ohne Abhängigkeiten) */
(function () {
    "use strict";

    var $ = function (sel, root) { return (root || document).querySelector(sel); };
    var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

    function store(key, value) {
        try {
            if (value === undefined) return localStorage.getItem(key);
            if (value === null) localStorage.removeItem(key);
            else localStorage.setItem(key, value);
        } catch (e) { return null; }
    }

    /* ---------------- Mobile-Navigation ---------------- */
    var navToggle = $(".nav-toggle");
    var navLinks = $(".nav-links");
    if (navToggle && navLinks) {
        navToggle.addEventListener("click", function () {
            var open = navLinks.classList.toggle("open");
            navToggle.setAttribute("aria-expanded", open ? "true" : "false");
        });
    }

    /* ---------------- Toasts ---------------- */
    function dismiss(toast) {
        if (!toast || toast.classList.contains("leaving")) return;
        toast.classList.add("leaving");
        toast.addEventListener("animationend", function () { toast.remove(); }, { once: true });
    }

    function wireToast(toast) {
        var close = $(".toast-close", toast);
        var timer = $(".toast-timer", toast);
        if (close) close.addEventListener("click", function () { dismiss(toast); });
        if (timer) timer.addEventListener("animationend", function () { dismiss(toast); });
    }

    function showToast(text) {
        var stack = $(".toast-stack");
        if (!stack) return;
        var t = document.createElement("div");
        t.className = "toast";
        t.setAttribute("role", "status");
        var s = document.createElement("span"); s.className = "toast-text"; s.textContent = text;
        var c = document.createElement("button"); c.className = "toast-close"; c.type = "button";
        c.setAttribute("aria-label", "Schließen"); c.innerHTML = "&times;";
        var tm = document.createElement("span"); tm.className = "toast-timer"; tm.style.animationDuration = "3.5s";
        t.append(s, c, tm);
        stack.appendChild(t);
        wireToast(t);
    }

    $$(".toast").forEach(wireToast);

    /* ---------------- Passwort anzeigen ---------------- */
    $$(".pw-toggle").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var input = btn.parentElement.querySelector("input");
            var show = input.type === "password";
            input.type = show ? "text" : "password";
            btn.classList.toggle("on", show);
            btn.setAttribute("aria-label", show ? "Passwort verbergen" : "Passwort anzeigen");
            input.focus();
        });
    });

    /* ---------------- Lade-Spinner beim Absenden ---------------- */
    $$(".js-loading-form").forEach(function (form) {
        form.addEventListener("submit", function () { form.classList.add("loading"); });
    });
    window.addEventListener("pageshow", function () {
        $$(".js-loading-form.loading").forEach(function (f) { f.classList.remove("loading"); });
    });

    /* ---------------- Registrierung: Passwortstärke + Abgleich ---------------- */
    var regForm = $(".js-register-form");
    if (regForm) {
        var pw = $("#password", regForm);
        var pw2 = $("#password2", regForm);
        var meter = $(".strength", regForm);
        var label = $(".strength-label", regForm);
        var hint = $(".match-hint", regForm);
        var names = ["Passwortstärke", "Schwach", "Mittel", "Gut", "Stark"];

        var rate = function (v) {
            if (!v) return 0;
            var score = 0;
            if (v.length >= 8) score++;
            if (v.length >= 12) score++;
            if (/[a-z]/.test(v) && /[A-Z]/.test(v)) score++;
            if (/\d/.test(v)) score++;
            if (/[^A-Za-z0-9]/.test(v)) score++;
            return Math.max(1, Math.min(4, score));
        };

        var checkMatch = function () {
            hint.hidden = !pw2.value || pw.value === pw2.value;
        };

        pw.addEventListener("input", function () {
            var lvl = rate(pw.value);
            meter.setAttribute("data-level", lvl);
            label.textContent = names[lvl];
            checkMatch();
        });
        pw2.addEventListener("input", checkMatch);
    }

    /* ---------------- Relative Datumsangaben ---------------- */
    var rtf = window.Intl && Intl.RelativeTimeFormat ? new Intl.RelativeTimeFormat("de", { numeric: "auto" }) : null;

    function parseDate(raw) {
        var m = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})$/.exec((raw || "").trim());
        if (!m) return null;
        return new Date(+m[1], m[2] - 1, +m[3], +m[4], +m[5], +m[6]);
    }

    function relative(date) {
        var diff = (date.getTime() - Date.now()) / 1000;
        var units = [["year", 31536000], ["month", 2592000], ["week", 604800], ["day", 86400], ["hour", 3600], ["minute", 60]];
        for (var i = 0; i < units.length; i++) {
            if (Math.abs(diff) >= units[i][1]) return rtf.format(Math.round(diff / units[i][1]), units[i][0]);
        }
        return "gerade eben";
    }

    $$(".js-reldate").forEach(function (el) {
        var d = parseDate(el.getAttribute("data-date"));
        // Nur echte Zeitstempel umformatieren – alles andere bleibt unverändert sichtbar
        if (!d || !rtf) return;
        el.textContent = relative(d);
        el.title = d.toLocaleString("de-DE", { dateStyle: "long", timeStyle: "short" });
    });

    /* ---------------- Dashboard ---------------- */
    var greeting = $(".js-greeting");
    if (greeting) {
        var h = new Date().getHours();
        greeting.textContent = h < 5 ? "Gute Nacht" : h < 11 ? "Guten Morgen" : h < 17 ? "Guten Tag" : h < 22 ? "Guten Abend" : "Gute Nacht";
    }

    var grid = $(".topf-grid");

    // Ansicht: Kacheln oder Liste
    var viewBtns = $$(".view-btn");
    function setView(view) {
        grid.classList.toggle("list", view === "list");
        viewBtns.forEach(function (b) { b.classList.toggle("active", b.getAttribute("data-view") === view); });
        store("hp-view", view);
    }
    if (grid && viewBtns.length) {
        viewBtns.forEach(function (b) {
            b.addEventListener("click", function () { setView(b.getAttribute("data-view")); });
        });
        setView(store("hp-view") || "grid");
    }

    // Sortierung
    var sortSel = $(".sort-select");
    if (sortSel && grid) {
        var collator = new Intl.Collator("de", { sensitivity: "base", numeric: true });
        var applySort = function () {
            var mode = sortSel.value;
            var cards = $$(".topf-card", grid);
            cards.sort(function (a, b) {
                if (mode === "az") return collator.compare(a.dataset.title, b.dataset.title);
                if (mode === "za") return collator.compare(b.dataset.title, a.dataset.title);
                if (mode === "old") return b.dataset.index - a.dataset.index;
                return a.dataset.index - b.dataset.index;
            });
            cards.forEach(function (c) { grid.appendChild(c); });
            store("hp-sort", mode);
        };
        var saved = store("hp-sort");
        if (saved) { sortSel.value = saved; if (saved !== "new") applySort(); }
        sortSel.addEventListener("change", applySort);
    }

    // Kategorie-Filter
    var chips = $$(".filter-chip");
    var filterEmpty = $(".filter-empty");
    chips.forEach(function (chip) {
        chip.addEventListener("click", function () {
            var f = chip.getAttribute("data-filter");
            chips.forEach(function (c) { c.classList.toggle("active", c === chip); });
            var visible = 0;
            $$(".topf-card", grid).forEach(function (card) {
                var show = f === "alle" || card.getAttribute("data-kategorie") === f;
                card.classList.toggle("is-hidden", !show);
                if (show) visible++;
            });
            if (filterEmpty) filterEmpty.hidden = visible > 0;
        });
    });

    // Taste "/" fokussiert die Suche
    var searchInput = $(".search-bar input");
    if (searchInput) {
        document.addEventListener("keydown", function (e) {
            var tag = (document.activeElement && document.activeElement.tagName) || "";
            if (e.key === "/" && !/INPUT|TEXTAREA|SELECT/.test(tag)) {
                e.preventDefault();
                searchInput.focus();
                searchInput.select();
            }
        });
    }

    /* ---------------- Detailseite ---------------- */
    var content = $(".js-content");
    var readtime = $(".js-readtime");
    if (content && readtime) {
        var words = content.textContent.trim().split(/\s+/).filter(Boolean).length;
        readtime.textContent = Math.max(1, Math.round(words / 200)) + " Min. Lesezeit";
    }

    var bookmark = $(".js-bookmark");
    if (bookmark) {
        var key = "hp-bookmark:" + location.pathname;
        var render = function (on) {
            bookmark.setAttribute("aria-pressed", on ? "true" : "false");
            $(".bookmark-label", bookmark).textContent = on ? "Gemerkt" : "Merken";
        };
        render(store(key) === "1");
        bookmark.addEventListener("click", function () {
            var on = bookmark.getAttribute("aria-pressed") !== "true";
            store(key, on ? "1" : null);
            render(on);
        });
    }

    var copyBtn = $(".js-copy");
    if (copyBtn) {
        copyBtn.addEventListener("click", function () {
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(location.href).then(
                    function () { showToast("Link in die Zwischenablage kopiert."); },
                    function () { showToast("Kopieren nicht möglich."); }
                );
            } else {
                showToast("Kopieren wird hier nicht unterstützt.");
            }
        });
    }

    /* ---------------- Neuer Honigtopf: Zähler, Vorlagen, Vorschau ---------------- */
    var editor = $(".js-editor-form");
    if (editor) {
        var title = $("#title", editor);
        var body = $("#content", editor);
        var cTitle = $('.counter[data-for="title"]', editor);
        var cBody = $('.counter[data-for="content"]', editor);
        var pCard = $(".js-preview-card");
        var pTitle = $(".js-preview-title");
        var pBody = $(".js-preview-body");
        var pKat = $(".js-preview-kat");
        var pSorte = $(".js-preview-sorte");

        var update = function () {
            cTitle.textContent = title.value.length + " / " + title.maxLength;
            var n = body.value.trim() ? body.value.trim().split(/\s+/).length : 0;
            cBody.textContent = n + (n === 1 ? " Wort" : " Wörter");
            pTitle.textContent = title.value.trim() || "Dein Titel erscheint hier";
            pBody.textContent = body.value.trim() || "Und hier ein Ausschnitt deines Inhalts…";

            var sorte = $('input[name="sorte"]:checked', editor);
            if (sorte) {
                pCard.style.setProperty("--honey", sorte.getAttribute("data-farbe"));
                pSorte.textContent = sorte.getAttribute("data-name");
            }
            var kat = $('input[name="kategorie"]:checked', editor);
            if (kat) pKat.textContent = kat.getAttribute("data-name");
        };

        title.addEventListener("input", update);
        body.addEventListener("input", update);
        $$('input[name="sorte"], input[name="kategorie"]', editor).forEach(function (r) {
            r.addEventListener("change", update);
        });

        $$(".chip", editor).forEach(function (chip) {
            chip.addEventListener("click", function () {
                if (!title.value.trim()) title.value = chip.getAttribute("data-title");
                var tpl = chip.getAttribute("data-content");
                body.value = body.value.trim() ? body.value.replace(/\s*$/, "") + "\n\n" + tpl : tpl;
                var kat = $('input[name="kategorie"][value="' + chip.getAttribute("data-kategorie") + '"]', editor);
                if (kat) kat.checked = true;
                update();
                body.focus();
                body.setSelectionRange(body.value.length, body.value.length);
            });
        });

        update();
    }

    /* ---------------- Challenges-Popup (abhakbare Checkliste) ---------------- */
    var chOverlay = $(".js-challenge-overlay");
    if (chOverlay) {
        var boxes = $$(".js-challenge-box");
        var fill = $(".js-challenge-fill");
        var count = $(".js-challenge-count");
        var badge = $(".js-challenge-badge");
        var PREFIX = "challenge:";

        function fortschritt() {
            var done = boxes.filter(function (b) { return b.checked; }).length;
            var total = boxes.length;
            if (fill) fill.style.width = total ? (done / total * 100) + "%" : "0";
            if (count) count.textContent = done + " / " + total + " gelöst";
            if (badge) {
                badge.textContent = done + "/" + total;
                badge.hidden = done === 0;
            }
        }

        boxes.forEach(function (box) {
            var key = PREFIX + box.getAttribute("data-id");
            box.checked = store(key) === "1";
            box.closest(".challenge-item").classList.toggle("done", box.checked);
            box.addEventListener("change", function () {
                store(key, box.checked ? "1" : null);
                box.closest(".challenge-item").classList.toggle("done", box.checked);
                fortschritt();
            });
        });
        fortschritt();

        function openModal() { chOverlay.hidden = false; document.body.classList.add("modal-open"); }
        function closeModal() { chOverlay.hidden = true; document.body.classList.remove("modal-open"); }

        $$(".js-open-challenges").forEach(function (b) { b.addEventListener("click", openModal); });
        $$(".js-close-challenges").forEach(function (b) { b.addEventListener("click", closeModal); });
        chOverlay.addEventListener("click", function (e) { if (e.target === chOverlay) closeModal(); });
        document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !chOverlay.hidden) closeModal(); });

        var reset = $(".js-challenge-reset");
        if (reset) {
            reset.addEventListener("click", function () {
                boxes.forEach(function (box) {
                    box.checked = false;
                    store(PREFIX + box.getAttribute("data-id"), null);
                    box.closest(".challenge-item").classList.remove("done");
                });
                fortschritt();
            });
        }
    }
})();
