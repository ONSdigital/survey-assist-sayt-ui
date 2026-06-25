import AutosuggestUI from '@ons/design-system/components/autosuggest/autosuggest.ui.js'

function initialiseRemoteAutosuggest(container) {
  const apiUrl = container.dataset.autosuggestApiUrl
  const queryParam =
    container.dataset.autosuggestApiQueryParam || 'q'

  let autosuggest

  async function fetchSuggestions(query) {
    const url = new URL(apiUrl, window.location.origin)
    url.searchParams.set(queryParam, query)

    const response = await fetch(url, {
      headers: {
        Accept: 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(
        `Autosuggest request failed with status ${response.status}`,
      )
    }

    const payload = await response.json()
    const results = Array.isArray(payload)
      ? payload
      : payload.results || []

    return {
      status: response.status,
      results,
      totalResults: results.length,
      limit: 20,
    }
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
