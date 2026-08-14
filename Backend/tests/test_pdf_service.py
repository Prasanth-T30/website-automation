import unittest

from app.services.pdf_service import generate_offer_letter


class OfferLetterCustomMessageTests(unittest.TestCase):
    def test_generate_offer_letter_accepts_custom_message(self):
        pdf_bytes = generate_offer_letter(
            {
                "name": "Test User",
                "registration_id": "REG20260099",
                "college": "Example College",
                "domain": "AI & ML",
                "duration": "30 Days",
                "start_date": "2026-01-01",
                "end_date": "2026-02-01",
                "category": "Internship",
                "place": "Chennai",
            },
            custom_message="Dear Test User,\n\nYour registration is approved and the offer letter has been updated with your custom approval note.\n\nThank you.\nTraining Team",
        )
        self.assertGreater(len(pdf_bytes), 0)


if __name__ == "__main__":
    unittest.main()
