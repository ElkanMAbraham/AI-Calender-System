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
    const apiKeyOllama = document.getElementById('api-key-ollama');
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
            case 4: return state.ai_provider === 'ollama' || state.ai_api_key.trim().length > 10;
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
                if (group === 'primary_use') {
                    contextContainer.style.display = 'block';
                }
                updateButtons();
            });
        });
    }


    /* ─────────────────────────────────────────
       Review table
    ───────────────────────────────────────── */
    function buildReview() {
        const tiles = {
            primary_use: {
                work: { icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M3 9a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v9a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2l0 -9"/><path d="M8 7v-2a2 2 0 0 1 2 -2h4a2 2 0 0 1 2 2v2"/><path d="M12 12l0 .01"/><path d="M3 13a20 20 0 0 0 18 0"/></svg>`, label: 'Work', desc: 'Professional tasks, meetings, documents' },
                study: { icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M22 9l-10 -4l-10 4l10 4l10 -4v6"/><path d="M6 10.6v5.4a6 3 0 0 0 12 0v-5.4"/></svg>`, label: 'Study', desc: 'Essays, research, coursework, revision' },
                personal: { icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M19.5 12.572l-7.5 7.428l-7.5 -7.428a5 5 0 1 1 7.5 -6.566a5 5 0 1 1 7.5 6.572"/></svg>`, label: 'Personal', desc: 'Journaling, side projects, life admin' },
                mix: { icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M18 4l3 3l-3 3"/><path d="M18 20l3 -3l-3 -3"/><path d="M3 7h3a5 5 0 0 1 5 5a5 5 0 0 0 5 5h5"/><path d="M21 7h-5a4.978 4.978 0 0 0 -3 1m-4 8a4.984 4.984 0 0 1 -3 1h-3"/></svg>`, label: 'Mix', desc: 'Combination of work, study, and personal' },
            },
            ai_provider: {
                claude: { icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.4"/><path d="M5.5 10.5l2-5 2 5M6.3 8.8h2.4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>`, label: 'Claude', desc: 'Anthropic — cloud model' },
                openai: { icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.4"/><path d="M8 5v6M5.5 6.5l5 3M5.5 9.5l5-3" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>`, label: 'OpenAI', desc: 'GPT-4o / GPT-4 — cloud model' },
                ollama: { icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="2" y="3" width="12" height="10" rx="2" stroke="currentColor" stroke-width="1.4"/><circle cx="8" cy="8" r="2" stroke="currentColor" stroke-width="1.3"/></svg>`, label: 'Ollama', desc: 'Runs locally — no key needed' },
            },
            autonomy_level: {
                ask: { icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.4"/><path d="M8 5.5a1.5 1.5 0 011 2.6L8 9v.5M8 11v.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>`, label: 'Ask first', desc: 'AI confirms before taking any action. Full control.', badge: `<span class="badge badge--success">SAFE</span>` },
                notify: { icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 2a4 4 0 014 4v2.5l1 2H3l1-2V6a4 4 0 014-4z" stroke="currentColor" stroke-width="1.4"/><path d="M6.5 12.5a1.5 1.5 0 003 0" stroke="currentColor" stroke-width="1.3"/></svg>`, label: 'Notify', desc: 'AI acts then tells you. You can undo. Balanced.', badge: `<span class="badge badge--info">DEFAULT</span>` },
                autonomous: { icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 2l1.5 4h4l-3 2.5 1 4L8 10l-3.5 2.5 1-4L2 6h4L8 2z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>`, label: 'Autonomous', desc: 'AI acts silently unless blocked. Fastest.', badge: `<span class="badge badge--warning">ADVANCED</span>` },
            },
        };

        const selected = {
            primary_use: tiles.primary_use[state.primary_use],
            ai_provider: tiles.ai_provider[state.ai_provider],
            autonomy_level: tiles.autonomy_level[state.autonomy_level],
        };

        reviewTable.innerHTML = `
        <!-- Name row -->
        <div class="review-row">
            <span class="review-col">Name</span>
            <span class="review-val">${state.name}</span>
        </div>

        <!-- Primary use tile -->
        <div class="review-row" style="align-items:flex-start;flex-direction:column;gap:var(--space-sm);">
            <span class="review-col">Primary use</span>
            <button class="option-tile is-selected" style="pointer-events:none;width:100%;max-width:220px;">
                <div class="tile-top">${selected.primary_use.icon}</div>
                <div class="tile-label">${selected.primary_use.label}</div>
                <div class="tile-desc">${selected.primary_use.desc}</div>
            </button>
        </div>

        <!-- AI provider tile -->
        <div class="review-row" style="align-items:flex-start;flex-direction:column;gap:var(--space-sm);">
            <span class="review-col">AI provider</span>
            <button class="option-tile option-tile--row is-selected" style="pointer-events:none;width:100%;">
                ${selected.ai_provider.icon}
                <div style="flex:1;">
                    <div class="tile-label">${selected.ai_provider.label}</div>
                    <div class="tile-desc">${selected.ai_provider.desc}</div>
                </div>
            </button>
        </div>

        <!-- Autonomy tile -->
        <div class="review-row" style="align-items:flex-start;flex-direction:column;gap:var(--space-sm);">
            <span class="review-col">Autonomy</span>
            <button class="option-tile option-tile--row is-selected" style="pointer-events:none;width:100%;">
                ${selected.autonomy_level.icon}
                <div style="flex:1;">
                    <div class="tile-label">${selected.autonomy_level.label} ${selected.autonomy_level.badge}</div>
                    <div class="tile-desc">${selected.autonomy_level.desc}</div>
                </div>
            </button>
        </div>
    `;
    }

    function setupApiKeyStep() {
        const isOllama = state.ai_provider === 'ollama';

        apiKeyOllama.style.display = isOllama ? 'block' : 'none';
        apiKeyCloud.style.display = isOllama ? 'none' : 'block';

        if (!isOllama) {
            const hints = {
                claude: { label: 'Anthropic API Key', hint: 'Starts with sk-ant-… — find it at console.anthropic.com', placeholder: 'sk-ant-...' },
                openai: { label: 'OpenAI API Key', hint: 'Starts with sk-… — find it at platform.openai.com', placeholder: 'sk-...' },
            };
            const cfg = hints[state.ai_provider] ?? hints.claude;
            apiKeyLabel.textContent = cfg.label;
            apiKeyHint.textContent = cfg.hint;
            inputApiKey.placeholder = cfg.placeholder;
            inputApiKey.value = state.ai_api_key;
            inputApiKey.focus();
        }
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
            ai_api_key: state.ai_provider === 'ollama' ? null : state.ai_api_key,
            autonomy_level: state.autonomy_level,
            ai_context: state.ai_context,
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