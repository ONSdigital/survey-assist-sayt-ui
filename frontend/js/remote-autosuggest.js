import AutosuggestUI from '@ons/design-system/components/autosuggest/autosuggest.ui.js'

function initialiseRemoteAutosuggest(container) {
  const apiUrl = container.dataset.autosuggestApiUrl
  const queryParam =
    container.dataset.autosuggestApiQueryParam || 'q'
  const selectionFieldName =
    container.dataset.autosuggestSelectionFieldName
  const initialSelectionValue =
    container.dataset.autosuggestSelectionValue || ''

  const form = container.closest('form')

  const suggestionsFieldName = selectionFieldName?.replace(
    /-selected$/,
    '-suggestions',
  )

  const queriesFieldName = selectionFieldName?.replace(
    /-selected$/,
    '-queries',
  )

  function parseSavedJson(fieldName) {
    const field = form?.elements.namedItem(fieldName)

    if (!(field instanceof HTMLInputElement)) {
      return []
    }

    try {
      const value = JSON.parse(field.value || '[]')
      return Array.isArray(value) ? value : []
    } catch {
      return []
    }
  }

  const savedSuggestions = parseSavedJson(suggestionsFieldName)
  const savedQueries = parseSavedJson(queriesFieldName)

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
  let suggestionsInput = null
  let queriesInput = null
  const queryHistory = [...savedQueries]

  function normaliseQueryForSearch(value) {
    return value
      .toLowerCase()
      .trim()
      .replace(/\s+/g, ' ')
  }

  function initialiseInput(fieldName, value) {
    if (!fieldName || !form) {
      return null
    }

    let input = form.elements.namedItem(fieldName)

    if (!(input instanceof HTMLInputElement)) {
      input = document.createElement('input')
      input.type = 'hidden'
      input.name = fieldName
      form.appendChild(input)
    }

    input.value = value
    return input
  }

  function recordQuery(query) {
    if (!queriesInput || !query) {
      return
    }

    queryHistory.unshift({
      value: query.value,
      time_start: query.time_start,
      time_end: query.time_end,
    })

    queriesInput.value = JSON.stringify(queryHistory)
  }

  let savedHistoryCleared = false
  let originalInputValue = ''

  function clearSavedHistoryOnInput() {
    if (
      savedHistoryCleared ||
      autosuggest.input.value === originalInputValue
    ) {
      return
    }

    savedHistoryCleared = true
    queryHistory.length = 0

    if (queriesInput) {
      queriesInput.value = '[]'
    }

    if (suggestionsInput) {
      suggestionsInput.value = '[]'
    }
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

    if (requestId !== latestRequestId) {
      throw new DOMException(
        'Stale autosuggest response',
        'AbortError',
      )
    }

    if (!Array.isArray(payload) && payload.query) {
      recordQuery(payload.query)
    }

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

  const originalHandleResults =
  autosuggest.handleResults.bind(autosuggest)

  autosuggest.handleResults = (envelope) => {
    originalHandleResults(envelope)

    if (!suggestionsInput) {
      return
    }

    const descriptions = autosuggest.results.map((result) => {
      const item = result.item ?? result

      return item[autosuggest.lang] ?? item.formattedAddress
    })

    suggestionsInput.value = JSON.stringify(descriptions)
  }

  selectionInput = initialiseInput(
    selectionFieldName,
    initialSelectionValue,
  )
  suggestionsInput = initialiseInput(
    suggestionsFieldName,
    JSON.stringify(savedSuggestions),
  )
  queriesInput = initialiseInput(
    queriesFieldName,
    JSON.stringify(queryHistory),
  )

  originalInputValue = autosuggest.input.value

  autosuggest.input.addEventListener(
    'input',
    clearSavedHistoryOnInput,
  )

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
