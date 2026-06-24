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