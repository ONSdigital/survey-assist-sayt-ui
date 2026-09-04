(() => {
    "use strict";

    const currentScript = document.currentScript;

    if (!currentScript) {
        return;
    }

    const notListedCheckboxId =
        currentScript.dataset.notListedCheckboxId;
    const autosuggestInputId =
        currentScript.dataset.autosuggestInputId;
    const selfDescribeInputId =
        currentScript.dataset.selfDescribeInputId;

    function initialiseSelfDescribe() {
        if (
            !notListedCheckboxId ||
            !autosuggestInputId ||
            !selfDescribeInputId
        ) {
            return;
        }

        const notListedCheckbox =
            document.getElementById(notListedCheckboxId);
        const autosuggestInput =
            document.getElementById(autosuggestInputId);
        const selfDescribeInput =
            document.getElementById(selfDescribeInputId);

        if (
            !notListedCheckbox ||
            !autosuggestInput ||
            !selfDescribeInput
        ) {
            return;
        }

        const selfDescribeField =
            selfDescribeInput.closest(".ons-field");
        const selfDescribeErrorPanel =
            selfDescribeInput.closest(".ons-panel--error");

        const selfDescribeContainer =
            selfDescribeErrorPanel || selfDescribeField;

        if (!selfDescribeContainer) {
            return;
        }

        function updateState() {
            const isNotListed = notListedCheckbox.checked;

            if (isNotListed) {
                autosuggestInput.value = "";
                autosuggestInput.dispatchEvent(
                    new Event("input", {
                        bubbles: true,
                    }),
                );
            }

            autosuggestInput.disabled = isNotListed;

            selfDescribeContainer.classList.toggle(
                "ons-u-d-no",
                !isNotListed,
            );
            selfDescribeInput.disabled = !isNotListed;

            notListedCheckbox.setAttribute(
                "aria-expanded",
                String(isNotListed),
            );
        }

        notListedCheckbox.addEventListener(
            "change",
            updateState,
        );

        updateState();
    }

    initialiseSelfDescribe();
})();
