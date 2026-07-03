(() => {
    "use strict";

    const currentScript = document.currentScript;

    if (!currentScript) {
        return;
    }

    const suggestionsPath = currentScript.dataset.suggestionsPath;
    const loadingElementId = currentScript.dataset.loadingElementId;
    const autosuggestElementId = currentScript.dataset.autosuggestElementId;

    let pendingSuggestionRequests = 0;

    function isBusinessActivitySuggestionsRequest(input) {
        const requestUrl = input instanceof Request ? input.url : String(input);

        try {
            const url = new URL(requestUrl, window.location.origin);
            const configuredUrl = new URL(suggestionsPath, window.location.origin);

            return url.pathname === configuredUrl.pathname;
        } catch {
            return requestUrl.includes(suggestionsPath);
        }
    }

    function placeLoadingIndicatorBesideInput() {
        const loadingElement = document.getElementById(loadingElementId);
        const autosuggestInput = document.getElementById(autosuggestElementId);

        if (!loadingElement || !autosuggestInput) {
            return;
        }

        autosuggestInput.classList.add("business-activity-autosuggest-input");
        loadingElement.classList.add("business-activity-loading--inline");

        autosuggestInput.insertAdjacentElement("afterend", loadingElement);
    }

    function setLoadingState(isLoading) {
        const loadingElement = document.getElementById(loadingElementId);
        const autosuggestElement = document.getElementById(autosuggestElementId);

        if (loadingElement) {
            loadingElement.hidden = !isLoading;
        }

        if (autosuggestElement) {
            autosuggestElement.setAttribute("aria-busy", String(isLoading));
        }
    }

    function startLoading() {
        pendingSuggestionRequests += 1;
        setLoadingState(true);
    }

    function stopLoading() {
        pendingSuggestionRequests = Math.max(0, pendingSuggestionRequests - 1);
        setLoadingState(pendingSuggestionRequests > 0);
    }

    function initialiseAutosuggestLoadingIndicator() {
        if (!window.fetch || !suggestionsPath || !loadingElementId) {
            return;
        }

        placeLoadingIndicatorBesideInput();

        const originalFetch = window.fetch.bind(window);

        window.fetch = async (input, init) => {
            if (!isBusinessActivitySuggestionsRequest(input)) {
                return originalFetch(input, init);
            }

            startLoading();

            try {
                return await originalFetch(input, init);
            } finally {
                stopLoading();
            }
        };
    }

    initialiseAutosuggestLoadingIndicator();
})();
