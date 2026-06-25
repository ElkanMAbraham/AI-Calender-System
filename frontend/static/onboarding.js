(function () {
    'use strict';

    /* ─────────────────────────────────────────
       State
    ───────────────────────────────────────── */
    const STEP_LABELS = ['Welcome', 'Your name', 'Primary use', 'AI provider', 'Autonomy', 'Review'];
    const TOTAL_STEPS = STEP_LABELS.length;

    const state = {
        step: 0,
        name: '',
        primary_use: '',
        ai_provider: '',
        autonomy_level: '',
    };

    /* ─────────────────────────────────────────
       DOM refs
    ───────────────────────────────────────── */
    const stepNav = document.getElementById('step-nav');
    const pipRow = document.getElementById('pip-row');
    const stepCounter = document.getElementById('step-counter');
    const btnNext = document.getElementById('btn-next');
    const btnBack = document.getElementById('btn-back');
    const reviewTable = document.getElementById('review-table');
    const errorBanner = document.getElementById('submit-error');
    const launchOverlay = document.getElementById('launch-overlay');
    const launchHeading = document.getElementById('launch-heading');
    const progressBar = document.getElementById('progress-bar');
    const inputName = document.getElementById('input-name');

    /* ─────────────────────────────────────────
       Build nav + pips once
    ───────────────────────────────────────── */
    function buildNav() {
        stepNav.innerHTML = '';
        STEP_LABELS.forEach((label, i) => {
            const item = document.createElement('div');
            item.className = 'step-nav-item';
            item.id = `nav-item-${i}`;

            const dot = document.createElement('div');
            dot.className = 'step-nav-dot';
            dot.id = `nav-dot-${i}`;
            dot.innerHTML = '';

            const lbl = document.createElement('span');
            lbl.className = 'step-nav-label';
            lbl.id = `nav-label-${i}`;
            lbl.textContent = label;

            item.appendChild(dot);
            item.appendChild(lbl);
            stepNav.appendChild(item);
        });

        pipRow.innerHTML = '';
        for (let i = 0; i < TOTAL_STEPS; i++) {
            const pip = document.createElement('div');
            pip.className = 'pip';
            pip.id = `pip-${i}`;
            pipRow.appendChild(pip);
        }
    }

    /* ─────────────────────────────────────────
       Update nav + pips for current step
    ───────────────────────────────────────── */
    function updateNav() {
        for (let i = 0; i < TOTAL_STEPS; i++) {
            const item = document.getElementById(`nav-item-${i}`);
            const dot = document.getElementById(`nav-dot-${i}`);
            const pip = document.getElementById(`pip-${i}`);

            item.classList.toggle('is-active', i === state.step);
            item.classList.toggle('is-done', i < state.step);

            dot.classList.toggle('is-active', i === state.step);
            dot.classList.toggle('is-done', i < state.step);

            if (i < state.step) {
                dot.innerHTML = `<svg width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path d="M2 5l2.5 2.5 3.5-4" stroke="var(--color-text-success)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>`;
            } else if (i === state.step) {
                dot.innerHTML = `<div class="step-nav-dot-inner"></div>`;
            } else {
                dot.innerHTML = '';
            }

            pip.classList.toggle('is-active', i === state.step);
            pip.classList.toggle('is-done', i < state.step);
        }

        stepCounter.textContent = `Step ${state.step + 1} / ${TOTAL_STEPS}`;
    }

    /* ─────────────────────────────────────────
       Show / transition steps
    ───────────────────────────────────────── */
    function goToStep(next) {
        const current = document.getElementById(`step-${state.step}`);
        const incoming = document.getElementById(`step-${next}`);

        current.classList.add('is-exiting');

        setTimeout(() => {
            current.classList.remove('is-visible', 'is-entering', 'is-exiting');
            state.step = next;

            incoming.classList.add('is-visible');
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    incoming.classList.add('is-entering');
                });
            });

            updateNav();
            updateButtons();

            if (next === TOTAL_STEPS - 1) buildReview();

            // Auto-focus inputs
            if (next === 1) inputName.focus();
        }, 220);
    }

    /* ─────────────────────────────────────────
       Validation
    ───────────────────────────────────────── */
    function canContinue() {
        switch (state.step) {
            case 1: return state.name.trim().length > 1;
            case 2: return state.primary_use !== '';
            case 3: return state.ai_provider !== '';
            case 4: return state.autonomy_level !== '';
            default: return true;
        }
    }

    function updateButtons() {
        btnNext.disabled = !canContinue();
        btnBack.classList.toggle('is-hidden', state.step === 0);

        if (state.step === TOTAL_STEPS - 1) {
            btnNext.innerHTML = `Save &amp; launch <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M5 2l4 4.5L5 11" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
        } else {
            btnNext.innerHTML = `Continue <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M5 2l4 4.5L5 11" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
        }
    }

    /* ─────────────────────────────────────────
       Option tile selection
    ───────────────────────────────────────── */
    function bindTiles() {
        document.querySelectorAll('.option-tile').forEach(tile => {
            tile.addEventListener('click', () => {
                const group = tile.dataset.group;
                const value = tile.dataset.value;
                if (!group || !value) return;

                document.querySelectorAll(`.option-tile[data-group="${group}"]`).forEach(t => {
                    t.classList.remove('is-selected');
                });
                tile.classList.add('is-selected');

                state[group] = value;
                updateButtons();
            });
        });
    }


    /* ─────────────────────────────────────────
       Review table
    ───────────────────────────────────────── */
    function buildReview() {
        const rows = [
            { col: 'name', val: state.name },
            { col: 'primary_use', val: state.primary_use },
            { col: 'ai_provider', val: state.ai_provider },
            { col: 'ai_api_key', val: '(not collected — set in Settings)' },
            { col: 'autonomy_level', val: state.autonomy_level },
        ];

        reviewTable.innerHTML = '';
        rows.forEach(({ col, val }) => {
            const row = document.createElement('div');
            row.className = 'review-row';

            const colEl = document.createElement('code');
            colEl.className = 'review-col';
            colEl.textContent = col;

            const valEl = document.createElement('span');
            valEl.className = 'review-val' + (val ? '' : ' is-empty');
            valEl.textContent = val || '(empty)';

            row.appendChild(colEl);
            row.appendChild(valEl);
            reviewTable.appendChild(row);
        });
    }

    /* ─────────────────────────────────────────
       js_api submit + launch screen
    ───────────────────────────────────────── */
    async function submitAndLaunch() {
        errorBanner.style.display = 'none';
        btnNext.disabled = true;
        btnNext.textContent = 'Saving…';

        const payload = {
            name: state.name,
            primary_use: state.primary_use,
            ai_provider: state.ai_provider,
            autonomy_level: state.autonomy_level,
        };

        try {
            // Calls Api.save_onboarding(payload) in backend/api.py via
            const result = await window.pywebview.api.saveOnboarding(payload);

            if (!result.ok) {
                throw new Error(result.error ?? 'Unknown error from Python.');
            }

            showLaunch();

            window.location.href = "index.html";

        } catch (err) {
            errorBanner.textContent = `Failed to save: ${err.message}`;
            errorBanner.style.display = 'block';
            btnNext.disabled = false;
            updateButtons();
        }
    }

    function showLaunch() {
        launchHeading.textContent = state.name
            ? `You're all set, ${state.name.split(' ')[0]}.`
            : "You're all set.";

        launchOverlay.classList.add('is-visible');

        // Animate progress bar after overlay fades in
        setTimeout(() => {
            progressBar.style.width = '100%';
        }, 350);
    }

    /* ─────────────────────────────────────────
    Event listeners
    ───────────────────────────────────────── */
    btnBack.addEventListener('click', () => {
        if (state.step > 0) goToStep(state.step - 1);
    });

    inputName.addEventListener('input', (e) => {
        state.name = e.target.value;
        updateButtons();
    });

    inputName.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && canContinue()) goToStep(state.step + 1);
    });

    // Wait for pywebview bridge before allowing submission
    window.addEventListener('pywebviewready', function () {
        btnNext.addEventListener('click', () => {
            if (!canContinue()) return;
            if (state.step === TOTAL_STEPS - 1) {
                submitAndLaunch();
            } else {
                goToStep(state.step + 1);
            }
        });
    });

    /* ─────────────────────────────────────────
       Init
    ───────────────────────────────────────── */
    buildNav();
    bindTiles();

    // Show first step
    const firstStep = document.getElementById('step-0');
    firstStep.classList.add('is-visible');
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            firstStep.classList.add('is-entering');
        });
    });

    updateNav();
    updateButtons();

})();