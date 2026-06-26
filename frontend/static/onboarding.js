(function () {
    'use strict';

    /* ─────────────────────────────────────────
       State
    ───────────────────────────────────────── */
    const STEP_LABELS = ['Welcome', 'Your name', 'Primary use', 'AI provider', 'API key', 'Autonomy', 'Review'];
    const TOTAL_STEPS = STEP_LABELS.length;

    const state = {
        step: 0,
        name: '',
        primary_use: '',
        ai_provider: '',
        ai_api_key: '',
        autonomy_level: '',
        ai_context: '',
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
    const inputApiKey = document.getElementById('input-api-key');
    const apiKeyCloud = document.getElementById('api-key-cloud');
    const apiKeyHint = document.getElementById('api-key-hint');
    const apiKeyLabel = document.getElementById('api-key-label');
    const btnToggleKey = document.getElementById('btn-toggle-key');
    const iconEye = document.getElementById('icon-eye');
    const iconEyeOff = document.getElementById('icon-eye-off');
    const contextContainer = document.getElementById('context-container');
    const btnAddContext = document.getElementById('btn-add-context');
    const contextInputWrap = document.getElementById('context-input-wrap');
    const inputContext = document.getElementById('input-context');
    const btnIcon = document.getElementById('btn-add-context-icon');
    const btnLabel = document.getElementById('btn-add-context-label');

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
            if (next === 2) {
                document.querySelector('#step-2 h2').textContent =
                    `Hey ${state.name.split(' ')[0]}, how will you primarily use this?`;
            }
            if (next === 4) setupApiKeyStep();
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
            case 4: return state.ai_api_key.trim().length > 10;
            case 5: return state.autonomy_level !== '';
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
    function handleTileChange(group, value) {
        state[group] = value;
        if (group === 'primary_use') {
            contextContainer.style.display = 'block';
        }
        updateButtons();
    }

    function mountTiles() {
        DocketTiles.mount(
            document.getElementById('primary-use-tiles'),
            'primary_use',
            state.primary_use,
            (value) => handleTileChange('primary_use', value)
        );
        DocketTiles.mount(
            document.getElementById('ai-provider-tiles-host'),
            'ai_provider',
            state.ai_provider,
            (value) => handleTileChange('ai_provider', value),
            { variant: 'row' }
        );
        DocketTiles.mount(
            document.getElementById('autonomy-tiles-host'),
            'autonomy_level',
            state.autonomy_level,
            (value) => handleTileChange('autonomy_level', value),
            { variant: 'row' }
        );
    }


    /* ─────────────────────────────────────────
       Review table
    ───────────────────────────────────────── */
    function buildReview() {
        // Show only the chosen tile per group; pointer-events disabled
        // to keep the review read-only.
        const labels = {
            primary_use: 'Primary use',
            ai_provider: 'AI provider',
            autonomy_level: 'Autonomy',
        };
        const groups = [
            { key: 'primary_use',    variant: undefined },
            { key: 'ai_provider',    variant: 'row' },
            { key: 'autonomy_level', variant: 'row' },
        ];

        const reviewTiles = groups.map(g => {
            const chosen = state[g.key];
            const def = DocketTiles.groups[g.key][chosen];
            return `
                <div class="review-row" style="align-items:flex-start;flex-direction:column;gap:var(--space-sm);">
                    <span class="review-col">${labels[g.key]}</span>
                    <div style="width:100%;max-width:none;pointer-events:none;">
                        ${def ? renderReviewTile(def, g.variant) : `<div class="text-sm" style="color:var(--color-text-tertiary);">Not selected</div>`}
                    </div>
                </div>
            `;
        }).join('');

        reviewTable.innerHTML = `
            <div class="review-row">
                <span class="review-col">Name</span>
                <span class="review-val" style="margin-left:auto;">${state.name}</span>
            </div>
            ${reviewTiles}
        `;
    }

    // Render a single read-only tile. Mirrors the inner markup of
    // DocketTiles.renderButtons so review matches a live selected tile.
    function renderReviewTile(def, variant) {
        const variantCls = variant === "row" ? " option-tile--row" : "";
        const badge = def.badge ? " " + def.badge : "";
        const iconBox = '<span class="tile-icon">' + def.icon + '</span>';
        const inner = variant === "row"
            ? iconBox
                + '<div style="flex:1;">'
                +   '<div class="tile-label">' + def.label + badge + '</div>'
                +   '<div class="tile-desc">' + def.desc + '</div>'
                + '</div>'
            : '<div class="tile-header">'
                +   iconBox
                +   '<div class="tile-label">' + def.label + badge + '</div>'
                + '</div>'
                + '<div class="tile-desc">' + def.desc + '</div>';
        return '<button class="option-tile' + variantCls + ' is-selected" type="button">'
            + inner
            + '</button>';
    }

    function setupApiKeyStep() {
        apiKeyCloud.style.display = 'block';

        const cfg = DocketTiles.apiKeyHints[state.ai_provider] || DocketTiles.apiKeyHints.anthropic;
        apiKeyLabel.textContent = cfg.label;
        apiKeyHint.textContent = cfg.hint;
        inputApiKey.placeholder = cfg.placeholder;
        inputApiKey.value = state.ai_api_key;
        inputApiKey.focus();
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
            ai_api_key: state.ai_api_key,
            autonomy_level: state.autonomy_level,
            ai_context: state.ai_context,
        };

        try {
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

    inputApiKey.addEventListener('input', (e) => {
        state.ai_api_key = e.target.value;
        updateButtons();
    });

    inputContext.addEventListener('input', (e) => {
        state.ai_context = e.target.value;
    });


    btnToggleKey.addEventListener('click', () => {
        const isPassword = inputApiKey.type === 'password';
        inputApiKey.type = isPassword ? 'text' : 'password';
        iconEye.style.display = isPassword ? 'none' : 'block';
        iconEyeOff.style.display = isPassword ? 'block' : 'none';
    });


    btnAddContext.addEventListener('click', () => {
        const isOpen = contextInputWrap.style.display !== 'none';
        contextInputWrap.style.display = isOpen ? 'none' : 'block';
        btnIcon.innerHTML = isOpen
            ? `<path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M12 5l0 14M5 12l14 0"/>`
            : `<path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M5 12l14 0"/>`;
        btnLabel.textContent = isOpen ? 'Add context' : 'Remove context';
        if (!isOpen) inputContext.focus();
    });

    /* ─────────────────────────────────────────
       Init
    ───────────────────────────────────────── */
    buildNav();
    mountTiles();

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