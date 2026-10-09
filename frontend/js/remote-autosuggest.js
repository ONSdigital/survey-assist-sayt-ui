import AutosuggestUI from '@ons/design-system/components/autosuggest/autosuggest.ui.js'

function initialiseRemoteAutosuggest(container) {
  const apiUrl = container.dataset.autosuggestApiUrl
  const queryParam =
    container.dataset.autosuggestApiQueryParam || 'q'
  const selectionFieldName =
    container.dataset.autosuggestSelectionFieldName
  const initialSelectionValue =
    container.dataset.autosuggestSelectionValue || ''

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
  let selectionInput = null

  function normaliseQueryForSearch(value) {
    return value
      .toLowerCase()
      .trim()
      .replace(/\s+/g, ' ')
  }

  function initialiseSelectionInput() {
    if (!selectionFieldName) {
      return
    }

    const form = container.closest('form')

    if (!form) {
      return
    }

    const existingField =
      form.elements.namedItem(selectionFieldName)

    if (existingField instanceof HTMLInputElement) {
      selectionInput = existingField
    } else {
      selectionInput = document.createElement('input')
      selectionInput.type = 'hidden'
      selectionInput.name = selectionFieldName
      form.appendChild(selectionInput)
    }

    selectionInput.value = initialSelectionValue
  }

  function clearSelectionIfInputChanged() {
    if (
      selectionInput &&
      autosuggest.input.value !== selectionInput.value
    ) {
      selectionInput.value = ''
    }
  }

  function waitForDebounce() {
    return new Promise((resolve) => {
      window.clearTimeout(debounceTimer)
      debounceTimer = window.setTimeout(resolve, debounceMs)
    })
  }

  async function fetchSuggestions(query) {
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
      throw new DOMException(
        'Stale autosuggest response',
        'AbortError',
      )
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

    lastResultEnvelope = {
      status: response.status,
      results: results.slice(0, 20),
      totalResults: results.length,
      limit: 20,
    }

    lastNormalisedQuery = normalisedQuery

    return lastResultEnvelope
  }

  autosuggest = new AutosuggestUI({
    context: container,
    suggestionFunction: fetchSuggestions,

    async onSelect(result) {
      autosuggest.input.value = result.displayText

      if (selectionInput) {
        selectionInput.value = result.displayText
      }
    },
  })

  initialiseSelectionInput()

  autosuggest.input.addEventListener(
    'input',
    clearSelectionIfInputChanged,
  )
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
