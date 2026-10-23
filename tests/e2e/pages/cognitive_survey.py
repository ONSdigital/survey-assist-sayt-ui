"""Browser interactions for the cognitive survey."""

from playwright.sync_api import Page, expect


class CognitiveSurveyPage:
    """Enter answers on survey and feedback pages."""

    PATH = "/survey"

    def __init__(self, page: Page) -> None:
        self.page = page
        self.save_button = page.get_by_role("button", name="Save and continue")

    def expect_survey_section_complete(self) -> None:
        """Verify the splash screen before feedback."""
        expect(
            self.page.get_by_role("heading", name="Thanks for participating", exact=True)
        ).to_be_visible()

    def expect_feedback_complete(self) -> None:
        """Verify the final splash screen after feedback."""
        expect(self.page).to_have_url(f"{self.PATH}/complete")
        expect(self.page.get_by_role("heading", name="Survey complete", exact=True)).to_be_visible()

        panel = self.page.locator("#survey-complete-panel")
        expect(panel).to_be_visible()
        expect(panel).to_contain_text("You have reached the end of the survey")
        expect(panel).to_contain_text("Thank you for taking part.")
        expect(self.page.get_by_role("link", name="Continue", exact=True)).not_to_be_visible()
        expect(self.page.get_by_role("button", name="Submit feedback")).not_to_be_visible()

    def previous(self) -> None:
        """Use the survey's Previous link."""
        self.page.get_by_role("link", name="Previous").click()

    def _answer_radio(self, answer: str) -> None:
        self.page.get_by_role("radio", name=answer, exact=True).check()
        self.save_button.click()

    def expect_radio_answer(self, answer: str) -> None:
        """Verify the saved radio answer."""
        expect(self.page.get_by_role("radio", name=answer, exact=True)).to_be_checked()

    def expect_text_answer(self, field_name: str, answer: str) -> None:
        """Verify the saved text answer."""
        expect(self.page.locator(f'[name="{field_name}"]')).to_have_value(answer)

    def answer_q1_paid_job(self, answer: str) -> None:
        """Answer the paid job question."""
        self._answer_radio(answer)

    def answer_q1a_own_business(self, answer: str) -> None:
        """Answer the own business question."""
        self._answer_radio(answer)

    def answer_q2_employment_status(self, answer: str) -> None:
        """Answer the employment status question."""
        self._answer_radio(answer)

    def answer_q2b_job_title(self, title: str) -> None:
        """Enter the job title."""
        self.page.locator('[name="job-title"]').fill(title)
        self.save_button.click()

    def answer_q3_job_description(self, description: str) -> None:
        """Enter the job description."""
        self.page.locator('[name="job-description"]').fill(description)
        self.save_button.click()

    def answer_q4_business_activity(self, query: str, suggestion: str) -> None:
        """Select a business activity from the suggestions."""
        activity = self.page.get_by_role("combobox")
        activity.fill(query)
        option = self.page.get_by_role("listbox", name="Suggested industries").get_by_role(
            "option", name=suggestion, exact=True
        )
        expect(option).to_be_visible()
        option.click()
        expect(activity).to_have_value(suggestion)
        self.save_button.click()

    def answer_q4_business_activity_not_listed(self, description: str) -> None:
        """Describe an activity that is not listed."""
        self.page.get_by_label("Not listed").check()
        activity = self.page.get_by_role("combobox")
        expect(activity).to_be_disabled()
        own_answer = self.page.get_by_label("Describe it in your own words")
        own_answer.fill(description)
        expect(own_answer).to_have_value(description)
        self.save_button.click()

    def enter_q4_unselected_activity(self, query: str) -> None:
        """Submit text without selecting an autosuggest result."""
        self.page.get_by_role("combobox").fill(query)
        self.save_button.click()

    def expect_q4_selection_required(self) -> None:
        """Verify the error for an unselected business activity."""
        expect(self.page.locator("#q4-api-autosuggest-error")).to_contain_text(
            "Select an answer from the suggestions or select Not listed"
        )
        expect(self.page.get_by_role("combobox")).to_be_visible()

    def answer_q5_business_name(self, name: str) -> None:
        """Enter the business name."""
        self.page.locator('[name="business-name"]').fill(name)
        self.save_button.click()

    def answer_q6_business_location(self, location: str) -> None:
        """Enter the business location."""
        self.page.locator('[name="business-location"]').fill(location)
        self.save_button.click()

    def continue_g2(self) -> None:
        """Continue from the guidance page."""
        self.page.get_by_role("button", name="Continue", exact=True).click()

    def answer_fq1_survey_ease(self, answer: str) -> None:
        """Answer the survey ease question."""
        self._answer_radio(answer)

    def answer_fq2_survey_relevance(self, answer: str) -> None:
        """Answer the survey relevance question."""
        self._answer_radio(answer)

    def answer_fq3_survey_comfort(self, answer: str) -> None:
        """Answer the survey comfort question."""
        self._answer_radio(answer)

    def answer_fq4_other_feedback(self, answer: str = "") -> None:
        """Submit optional survey feedback."""
        if answer:
            self.page.locator('[name="other-feedback"]').fill(answer)
        self.page.get_by_role("button", name="Submit feedback").click()
