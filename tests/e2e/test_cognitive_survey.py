"""Browser journeys for the cognitive survey definition."""

from playwright.sync_api import Page

from .pages.cognitive_survey import CognitiveSurveyPage
from .pages.home import HomePage


def test_paid_employee_journey(authenticated_page: Page) -> None:
    """Full journey for a paid employee SAYT selection with feedback."""
    HomePage(authenticated_page).open_cognitive_test()

    survey = CognitiveSurveyPage(authenticated_page)
    survey.answer_q1_paid_job("Yes")
    survey.answer_q2_employment_status("Employee")
    survey.answer_q2b_job_title("Software developer")
    survey.answer_q3_job_description("I build and maintain websites for clients.")
    survey.answer_q4_business_activity(
        "software development", "Website design and development: 62012"
    )
    survey.answer_q5_business_name("Example Software Ltd")
    survey.answer_q6_business_location("Cardiff")
    survey.expect_survey_section_complete()

    survey.continue_g2()
    survey.answer_fq1_survey_ease("Easy")
    survey.answer_fq2_survey_relevance("Relevant")
    survey.answer_fq3_survey_comfort("Comfortable")
    survey.answer_fq4_other_feedback("Overall good experience")
    survey.expect_feedback_complete()


def test_own_business_journey(authenticated_page: Page) -> None:
    """Survey journey for own business with an unlisted activity."""
    HomePage(authenticated_page).open_cognitive_test()
    survey = CognitiveSurveyPage(authenticated_page)
    survey.answer_q1_paid_job("No")
    survey.answer_q1a_own_business("Yes")
    survey.answer_q2_employment_status("Self-employed")
    survey.answer_q2b_job_title("Freelance illustrator")
    survey.answer_q3_job_description("I draw illustrations for books and magazines.")

    survey.answer_q4_business_activity_not_listed("Illustration for print publications")
    survey.answer_q5_business_name("Example Design Studio")
    survey.answer_q6_business_location("Bristol")
    survey.expect_survey_section_complete()


def test_early_exit_journey(authenticated_page: Page) -> None:
    """Early exit journey when the respondent has no job or business."""
    HomePage(authenticated_page).open_cognitive_test()
    survey = CognitiveSurveyPage(authenticated_page)
    survey.answer_q1_paid_job("No")
    survey.answer_q1a_own_business("No")
    survey.expect_survey_section_complete()


def test_business_activity_requires_a_selection(authenticated_page: Page) -> None:
    """Requires a business activity selection before continuing."""
    HomePage(authenticated_page).open_cognitive_test()
    survey = CognitiveSurveyPage(authenticated_page)
    survey.answer_q1_paid_job("Yes")
    survey.answer_q2_employment_status("Employee")
    survey.answer_q2b_job_title("Software developer")
    survey.answer_q3_job_description("I build software for clients.")
    survey.save_button.click()
    survey.expect_q4_selection_required()
    survey.enter_q4_unselected_activity("software development")
    survey.expect_q4_selection_required()
    survey.expect_text_answer("business-activity", "software development")


def test_previous_navigation_preserves_answers(authenticated_page: Page) -> None:
    """Preserve answers to previously saved questions after navigating back."""
    HomePage(authenticated_page).open_cognitive_test()
    survey = CognitiveSurveyPage(authenticated_page)
    survey.answer_q1_paid_job("Yes")
    survey.answer_q2_employment_status("Employee")
    survey.answer_q2b_job_title("Software developer")
    survey.answer_q3_job_description("I build software for clients.")

    survey.previous()
    survey.expect_text_answer("job-description", "I build software for clients.")
    survey.previous()
    survey.expect_text_answer("job-title", "Software developer")
    survey.previous()
    survey.expect_radio_answer("Employee")
    survey.previous()
    survey.expect_radio_answer("Yes")

    survey.answer_q1_paid_job("No")
    survey.answer_q1a_own_business("Yes")
    survey.answer_q2_employment_status("Self-employed")
    survey.answer_q2b_job_title("Freelance illustrator")
    survey.answer_q3_job_description("I draw illustrations for books and magazines.")

    survey.previous()
    survey.expect_text_answer("job-description", "I draw illustrations for books and magazines.")
    survey.previous()
    survey.expect_text_answer("job-title", "Freelance illustrator")
    survey.previous()
    survey.expect_radio_answer("Self-employed")
    survey.previous()
    survey.expect_radio_answer("Yes")
    survey.previous()
    survey.expect_radio_answer("No")
