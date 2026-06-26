// SPA router for Docket.
//
// Hash-based routing (e.g. #/calendar). PyWebView serves index.html
// from a local HTTP server, but it has no SPA fallback, so a hard
// refresh on a History API path like /calendar would 404. Hash
// routing sidesteps this because the server always returns index.html
// for /, and the hash is client-only.

const ROUTES = [
    { path: "/",         view: "home",     title: "Home"     },
    { path: "/calendar", view: "calendar", title: "Calendar" },
    { path: "/tasks",    view: "tasks",    title: "Tasks"    },
];

const viewByPath = new Map(ROUTES.map(r => [r.path, r]));
const pathByView = new Map(ROUTES.map(r => [r.view, r.path]));

const NOT_FOUND_HTML = `<main data-view="404"><section class="card" data-size="lg"><h1>Not found</h1><p>That route doesn't exist.</p></section></main>`;
const ERROR_HTML    = `<main data-view="error"><section class="card" data-size="lg"><h1>Something went wrong</h1><p>Failed to load this view.</p><button class="nav-icon-btn" type="button" data-action="retry">Retry</button></section></main>`;

const viewCache = new Map();

function pathToView(rawPath) {
    if (!rawPath) return null;
    const key = "/" + rawPath.replace(/^#?\/?/, "").replace(/\/+$/, "");
    return viewByPath.get(key) ?? null;
}

async function fetchView(name) {
    if (viewCache.has(name)) return viewCache.get(name);
    const promise = fetch(`static/views/${name}.html`)
        .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.text(); });
    viewCache.set(name, promise);
    try { return await promise; } catch (e) { viewCache.delete(name); throw e; }
}

function render(route, htmlString) {
    document.getElementById("app").innerHTML = htmlString;
    document.title = `${route.title} · Docket`;
    for (const item of document.querySelectorAll(".nav-segment-item")) {
        item.classList.toggle("is-active", item.getAttribute("href") === "#" + route.path);
    }
}

async function navigate(rawPath, { push = true } = {}) {
    const route = pathToView(rawPath);
    if (!route) {
        render({ path: "/", title: "Not found" }, NOT_FOUND_HTML);
        if (push) history.pushState({}, "", "#/");
        return;
    }
    try {
        render(route, await fetchView(route.view));
        if (push) history.pushState({}, "", "#" + route.path);
    } catch (e) {
        console.error("Docket router: view load failed", e);
        render({ path: "/", title: "Error" }, ERROR_HTML);
    }
}

// Hard-coded model options per provider. Extend when real integrations land.
const MODELS_BY_PROVIDER = {
    openai: [
        { value: "gpt-4o",            label: "GPT-4o" },
        { value: "gpt-4o-mini",       label: "GPT-4o mini" },
        { value: "gpt-4-turbo",       label: "GPT-4 Turbo" },
        { value: "gpt-3.5-turbo",     label: "GPT-3.5 Turbo" },
    ],
    anthropic: [
        { value: "claude-3-5-sonnet-latest", label: "Claude 3.5 Sonnet" },
        { value: "claude-3-5-haiku-latest",  label: "Claude 3.5 Haiku" },
        { value: "claude-3-opus-latest",     label: "Claude 3 Opus" },
    ],
    ollama: [
        { value: "llama3.2",  label: "Llama 3.2" },
        { value: "mistral",   label: "Mistral" },
        { value: "phi3",      label: "Phi-3" },
    ],
};

// Display label for a provider, sourced from the shared tile catalog.
function providerLabel(provider) {
    return window.DocketTiles?.ai_provider?.[provider]?.label || provider || "";
}

// In-memory state for the currently-open settings modal.
let settingsState = null;

function closeModalWithAnimation(dialog) {
    if (!dialog || dialog.classList.contains("closing")) return;
    dialog.classList.add("closing");
    setTimeout(() => {
        dialog.classList.remove("closing");
        dialog.close();
        settingsState = null;
    }, 200);
}

function showToast(message, kind = "success", { sticky = false } = {}) {
    const el = document.getElementById("settings-toast");
    if (!el) return;
    el.textContent = message;
    el.setAttribute("data-state", kind);
    el.classList.add("is-visible");
    if (el._toastTimer) clearTimeout(el._toastTimer);
    if (!sticky) {
        el._toastTimer = setTimeout(() => {
            el.classList.remove("is-visible");
            setTimeout(() => {
                el.removeAttribute("data-state");
                el.textContent = "";
            }, 250);
        }, 2000);
    }
}

function hideToast() {
    const el = document.getElementById("settings-toast");
    if (!el) return;
    if (el._toastTimer) clearTimeout(el._toastTimer);
    el.classList.remove("is-visible");
    el.removeAttribute("data-state");
    el.textContent = "";
}

// Mark a single field's `.field` wrapper as having an inline error.
// Pass null/empty to clear.
function setFieldError(fieldName, message) {
    const wrapper = document.querySelector(`[data-field="${fieldName}"]`);
    if (!wrapper) return;
    const helper = wrapper.querySelector("[data-field-helper]");
    if (message) {
        wrapper.setAttribute("data-field-state", "error");
        if (helper) {
            helper.setAttribute("data-state", "error");
            helper.textContent = message;
        }
    } else {
        wrapper.removeAttribute("data-field-state");
        if (helper) {
            helper.removeAttribute("data-state");
            // Restore the original helper text saved at hydration time.
            helper.textContent = helper.dataset.originalText || helper.textContent;
        }
    }
}

function clearAllFieldErrors() {
    document.querySelectorAll(".field[data-field]").forEach(f => {
        const name = f.getAttribute("data-field");
        setFieldError(name, null);
    });
}

function rememberHelperTexts() {
    document.querySelectorAll(".field [data-field-helper]").forEach(h => {
        if (!h.dataset.originalText) h.dataset.originalText = h.textContent;
    });
}

function maskKey(last4) {
    // Stable length so the layout doesn't shift when cards appear/disappear.
    return "•".repeat(12) + (last4 || "");
}

// Settings: hydration
async function hydrateSettingsModal() {
    const modal = document.getElementById("settings-modal");
    if (!modal) return;

    rememberHelperTexts();
    clearAllFieldErrors();
    hideToast();

    let prefs = {};
    try {
        if (window.pywebview?.api?.getPreferences) {
            const res = await window.pywebview.api.getPreferences();
            if (res?.ok) prefs = res.data || {};
        }
    } catch (e) {
        console.error("Failed to load preferences", e);
    }

    settingsState = {
        name: prefs.name || "",
        primary_use: prefs.primary_use || "",
        primary_use_context: prefs.primary_use_context || "",
        ai_provider: prefs.ai_provider || "",
        default_model: prefs.default_model || "",
        autonomy_level: prefs.autonomy_level || "",
        api_keys: prefs.api_keys || {},
    };

    const nameEl = modal.querySelector("#account-name");
    if (nameEl) nameEl.value = settingsState.name;

    // Tile groups — host wrapper and variant mirror onboarding.
    DocketTiles.mount(
        document.getElementById("primary-use-tiles"),
        "primary_use",
        settingsState.primary_use,
        (value) => onTileSelect("primary_use", value)
    );
    DocketTiles.mount(
        document.getElementById("autonomy-tiles"),
        "autonomy_level",
        settingsState.autonomy_level,
        (value) => onTileSelect("autonomy_level", value),
        { variant: "row" }
    );
    DocketTiles.mount(
        document.getElementById("ai-provider-tiles"),
        "ai_provider",
        settingsState.ai_provider,
        (value) => onProviderSelect(value),
        { variant: "row" }
    );

    const ctxEl = modal.querySelector("#primary-use-context");
    if (ctxEl) ctxEl.value = settingsState.primary_use_context;

    populateModelOptions();
    if (settingsState.default_model) {
        const modelEl = modal.querySelector("#default-model");
        if (modelEl) modelEl.value = settingsState.default_model;
    }

    renderKeyCards();
    updateKeyAddAvailability();
}

// Called by DocketTiles.mount when a non-provider tile is clicked.
function onTileSelect(group, value) {
    if (!settingsState) return;
    settingsState[group] = value;
    setFieldError(group, null);
}

// Provider changes reset dependent UI: model dropdown, key cards, add-key input.
function onProviderSelect(value) {
    if (!settingsState) return;
    settingsState.ai_provider = value;
    settingsState.default_model = "";
    populateModelOptions();
    renderKeyCards();
    updateKeyAddAvailability();
    setFieldError("ai_provider", null);
}

function populateModelOptions() {
    const modelEl = document.querySelector("#default-model");
    if (!modelEl) return;
    const provider = settingsState?.ai_provider;
    modelEl.innerHTML = "";

    if (!provider) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = "Choose a provider first";
        modelEl.appendChild(opt);
        modelEl.disabled = true;
        return;
    }

    modelEl.disabled = false;
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Select a model…";
    modelEl.appendChild(placeholder);

    const models = MODELS_BY_PROVIDER[provider] || [];
    for (const m of models) {
        const opt = document.createElement("option");
        opt.value = m.value;
        opt.textContent = m.label;
        modelEl.appendChild(opt);
    }

    if (settingsState?.default_model && models.some(m => m.value === settingsState.default_model)) {
        modelEl.value = settingsState.default_model;
    } else {
        modelEl.value = "";
    }
}

function renderKeyCards() {
    const container = document.getElementById("key-cards");
    if (!container) return;
    container.innerHTML = "";

    const provider = settingsState?.ai_provider;
    const keys = settingsState?.api_keys || {};

    if (!provider) {
        const empty = document.createElement("div");
        empty.className = "key-empty";
        empty.textContent = "Choose an AI provider to manage API keys.";
        container.appendChild(empty);
        return;
    }

    if (keys[provider]) {
        container.appendChild(buildKeyCard(provider, keys[provider], true));
    }

    const others = Object.keys(keys).filter(p => p !== provider);
    if (others.length) {
        const heading = document.createElement("div");
        heading.style.fontSize = "var(--font-text-sm)";
        heading.style.color = "var(--color-text-tertiary)";
        heading.style.marginTop = "var(--space-xs)";
        heading.textContent = "Other configured providers";
        container.appendChild(heading);
        for (const p of others) {
            container.appendChild(buildKeyCard(p, keys[p], false));
        }
    }
}

function buildKeyCard(provider, entry, isActive) {
    const card = document.createElement("div");
    card.className = "key-card";
    if (isActive) card.setAttribute("data-state", "active");

    const body = document.createElement("div");
    body.className = "key-card-body";

    const providerRow = document.createElement("div");
    providerRow.className = "key-card-provider";
    if (isActive) {
        const dot = document.createElement("span");
        dot.className = "key-card-active-dot";
        providerRow.appendChild(dot);
        providerRow.appendChild(document.createTextNode("Active · "));
    }
    providerRow.appendChild(document.createTextNode(providerLabel(provider)));
    body.appendChild(providerRow);

    const value = document.createElement("div");
    value.className = "key-card-value";
    // last4 is derived for display only — never persisted.
    value.textContent = maskKey((entry.key || "").slice(-4));
    body.appendChild(value);

    const actions = document.createElement("div");
    actions.className = "key-card-actions";

    const del = document.createElement("button");
    del.type = "button";
    del.setAttribute("data-btn", "danger");
    del.setAttribute("data-size", "sm");
    del.dataset.action = "delete-key";
    del.dataset.provider = provider;
    del.textContent = "Delete";
    actions.appendChild(del);

    card.appendChild(body);
    card.appendChild(actions);
    return card;
}

function updateKeyAddAvailability() {
    const input = document.getElementById("key-add-input");
    const btn = document.getElementById("key-add-btn");
    const provider = settingsState?.ai_provider;
    const enabled = !!provider;
    if (input) {
        input.disabled = !enabled;
        input.value = "";
        input.placeholder = enabled
            ? `Paste a key for ${providerLabel(provider)}`
            : "Choose a provider to add a key";
    }
    if (btn) {
        btn.disabled = !enabled;
    }
}

function bindSettingsEvents() {
    const modal = document.getElementById("settings-modal");
    if (!modal) return;

    modal.querySelector("#account-name")?.addEventListener("input", (e) => {
        if (!settingsState) return;
        settingsState.name = e.target.value;
        if (e.target.value.trim()) setFieldError("name", null);
    });

    modal.querySelector("#primary-use-context")?.addEventListener("input", (e) => {
        if (!settingsState) return;
        settingsState.primary_use_context = e.target.value;
    });

    // Model change (provider is selected via tiles, not a <select>)
    modal.querySelector("#default-model")?.addEventListener("change", (e) => {
        if (!settingsState) return;
        settingsState.default_model = e.target.value;
        if (e.target.value) setFieldError("default_model", null);
    });

    // Add key
    const keyInput = modal.querySelector("#key-add-input");
    const keyBtn = modal.querySelector("#key-add-btn");
    const tryAddKey = async () => {
        if (!settingsState) return;
        const provider = settingsState.ai_provider;
        const value = keyInput?.value?.trim();
        if (!provider || !value) return;
        // Only persist the key itself; the masked display derives last4 on render.
        settingsState.api_keys = {
            ...settingsState.api_keys,
            [provider]: { key: value },
        };
        keyInput.value = "";
        renderKeyCards();
        updateKeyAddAvailability();
    };
    keyInput?.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            tryAddKey();
        }
    });
    keyBtn?.addEventListener("click", (e) => {
        e.preventDefault();
        tryAddKey();
    });

    // Delete key (event-delegated — cards re-render)
    const keyCards = modal.querySelector("#key-cards");
    keyCards?.addEventListener("click", async (event) => {
        const target = event.target.closest('[data-action="delete-key"]');
        if (!target || !settingsState) return;
        const provider = target.dataset.provider;
        if (!provider) return;
        const label = providerLabel(provider);
        if (!window.confirm(`Delete the saved API key for ${label}? You'll need to re-add it to use ${label} again.`)) {
            return;
        }
        try {
            if (window.pywebview?.api?.deleteApiKey) {
                const res = await window.pywebview.api.deleteApiKey(provider);
                if (!res?.ok) {
                    showToast(res?.error || "Failed to delete key.", "error", { sticky: true });
                    return;
                }
            }
            const next = { ...settingsState.api_keys };
            delete next[provider];
            settingsState.api_keys = next;
            renderKeyCards();
            updateKeyAddAvailability();
            showToast(`Removed ${label} key.`);
        } catch (err) {
            showToast(`Delete failed: ${err.message}`, "error", { sticky: true });
        }
    });
}

function validateSettings(state) {
    if (!state.name || !state.name.trim())      return { field: "name",           message: "Please enter your full name." };
    if (!state.primary_use)                       return { field: "primary_use",    message: "Pick a primary use." };
    if (!state.ai_provider)                       return { field: "ai_provider",    message: "Pick an AI provider." };
    if (!state.default_model)                      return { field: "default_model",  message: "Pick a default model." };
    if (!state.autonomy_level)                    return { field: "autonomy_level", message: "Pick an autonomy level." };
    return null;
}

async function saveSettings() {
    if (!settingsState) return;
    clearAllFieldErrors();
    hideToast();

    const error = validateSettings(settingsState);
    if (error) {
        setFieldError(error.field, error.message);
        const wrapper = document.querySelector(`[data-field="${error.field}"]`);
        wrapper?.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
    }
    try {
        const res = await window.pywebview.api.savePreferences({
            name: settingsState.name.trim(),
            primary_use: settingsState.primary_use,
            primary_use_context: settingsState.primary_use_context,
            ai_provider: settingsState.ai_provider,
            default_model: settingsState.default_model,
            autonomy_level: settingsState.autonomy_level,
            api_keys: settingsState.api_keys,
        });
        if (!res?.ok) {
            showToast(res?.error || "Failed to save.", "error", { sticky: true });
            return;
        }
        showToast("Saved.");
        setTimeout(() => closeModalWithAnimation(document.getElementById("settings-modal")), 800);
    } catch (err) {
        showToast(`Save failed: ${err.message}`, "error", { sticky: true });
    }
}

// Global click router (data-action + Esc + backdrop)
document.addEventListener("click", (event) => {
    const actionTarget = event.target.closest("[data-action]");
    if (actionTarget) {
        event.preventDefault();
        const action = actionTarget.dataset.action;
        if (action === "open-settings") document.getElementById("settings-modal")?.showModal();
        else if (action === "retry") navigate(window.location.hash || "#/", { push: false });
        return;
    }
    const anchor = event.target.closest("a");
    if (!anchor) return;
    const href = anchor.getAttribute("href");
    if (href?.startsWith("#/")) {
        event.preventDefault();
        navigate(href);
    }
});

window.addEventListener("popstate", () => navigate(window.location.hash || "#/", { push: false }));

navigate(window.location.hash || "#/", { push: false });