import AutosuggestUI from '@ons/design-system/components/autosuggest/autosuggest.ui.js'

function initialiseRemoteAutosuggest(container) {
  const apiUrl = container.dataset.autosuggestApiUrl
  const queryParam =
    container.dataset.autosuggestApiQueryParam || 'q'

  const debounceMs = 300
  let debounceTimer = null
  let abortController = null
  let latestRequestId = 0
  let lastNormalisedQuery = ''
  let lastResultEnvelope = {
    status: 200,
    results: [],
    totalResults: 0,
    limit: 20,
  }
  let autosuggest

  function normaliseQueryForSearch(value) {
    return value
      .toLowerCase()
      .trim()
      .replace(/\s+/g, ' ')
  }

  function waitForDebounce() {
    return new Promise((resolve) => {
      window.clearTimeout(debounceTimer)
      debounceTimer = window.setTimeout(resolve, debounceMs)
    })
  }

  async function fetchSuggestions(query) {
    // If the query is effectively the same, return the last result envelope
    const normalisedQuery = normaliseQueryForSearch(query)

    if (normalisedQuery === lastNormalisedQuery) {
      return lastResultEnvelope
    }

    await waitForDebounce()

    abortController?.abort()
    abortController = new AbortController()

    const requestId = ++latestRequestId

    const url = new URL(apiUrl, window.location.origin)
    url.searchParams.set(queryParam, query)

    const response = await fetch(url, {
      signal: abortController.signal,
      headers: {
        Accept: 'application/json',
      },
    })

    if (requestId !== latestRequestId) {
      throw new DOMException('Stale autosuggest response', 'AbortError')
    }

    if (!response.ok) {
      throw new Error(
        `Autosuggest request failed with status ${response.status}`,
      )
    }

    const payload = await response.json()
    const results = Array.isArray(payload)
      ? payload
      : payload.results || []

    // Store result as the last normalised query for future reference
    lastResultEnvelope = {
      status: response.status,
      results: results.slice(0, 20),
      totalResults: results.length,
      limit: 20,
    }

    return lastResultEnvelope
  }

  autosuggest = new AutosuggestUI({
    context: container,
    suggestionFunction: fetchSuggestions,

    onSelect(result) {
      autosuggest.input.value = result.displayText
    },
  })
}

function initialiseRemoteAutosuggests() {
  document
    .querySelectorAll('[data-autosuggest-api-url]')
    .forEach(initialiseRemoteAutosuggest)
}

if (document.readyState === 'loading') {
  document.addEventListener(
    'DOMContentLoaded',
    initialiseRemoteAutosuggests,
  )
} else {
  initialiseRemoteAutosuggests()
}
