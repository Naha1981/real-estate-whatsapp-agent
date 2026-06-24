"""
Tests for the Intent Classifier (fallback mode — no API key needed).
"""
import pytest
from app.ai.intent import IntentClassifier, classifier


@pytest.fixture
def intent_classifier():
    return IntentClassifier()


class TestIntentClassifier:
    """Test the rule-based fallback classifier."""

    def test_greeting_simple(self, intent_classifier):
        result = intent_classifier._fallback_classify("hello")
        assert result.intent == "greeting"

    def test_greeting_zulu(self, intent_classifier):
        result = intent_classifier._fallback_classify("sawubona")
        assert result.intent == "greeting"

    def test_greeting_sotho(self, intent_classifier):
        result = intent_classifier._fallback_classify("dumela")
        assert result.intent == "greeting"

    def test_property_search_basic(self, intent_classifier):
        result = intent_classifier._fallback_classify(
            "looking for a 2 bedroom house in Pimville under R400K"
        )
        assert result.intent == "property_search"
        assert result.entities.get("bedrooms") == 2
        assert result.entities.get("max_price") == 400000
        assert result.entities.get("area") == "Pimville"

    def test_property_search_zulu_mix(self, intent_classifier):
        result = intent_classifier._fallback_classify(
            "ngifuna i-house eSoweto 3 bedroom"
        )
        assert result.intent == "property_search"
        assert result.entities.get("bedrooms") == 3
        assert "soweto" in result.entities.get("area", "").lower()

    def test_property_search_rent(self, intent_classifier):
        result = intent_classifier._fallback_classify(
            "do you have a flat to rent in Hillbrow?"
        )
        assert result.intent == "property_search"
        assert result.entities.get("price_type") == "rent"

    def test_valuation_request(self, intent_classifier):
        result = intent_classifier._fallback_classify(
            "value: 3 bed Diepkloof Zone 4"
        )
        assert result.intent == "valuation_request"

    def test_pipeline_check(self, intent_classifier):
        result = intent_classifier._fallback_classify("pipeline")
        assert result.intent == "pipeline_check"

    def test_bond_query(self, intent_classifier):
        result = intent_classifier._fallback_classify(
            "can I afford a R400K bond?"
        )
        assert result.intent == "bond_query"

    def test_listing_add(self, intent_classifier):
        result = intent_classifier._fallback_classify(
            "add listing: 3 bed Pimville R450K"
        )
        assert result.intent == "listing_add"

    def test_deal_update(self, intent_classifier):
        result = intent_classifier._fallback_classify(
            "update deal #14: offer accepted R415K"
        )
        assert result.intent == "deal_update"

    def test_viewing_request(self, intent_classifier):
        result = intent_classifier._fallback_classify(
            "can I view the house on Saturday?"
        )
        assert result.intent == "viewing_request"

    def test_maintenance(self, intent_classifier):
        result = intent_classifier._fallback_classify(
            "the geyser is leaking in unit 3"
        )
        assert result.intent == "maintenance"

    def test_rental_query(self, intent_classifier):
        result = intent_classifier._fallback_classify(
            "has the tenant paid rent this month?"
        )
        assert result.intent == "rental_query"

    def test_unknown(self, intent_classifier):
        result = intent_classifier._fallback_classify("xyzzy random text")
        assert result.intent == "unknown"
        assert result.needs_human is True

    def test_entity_extraction_rdp(self, intent_classifier):
        result = intent_classifier._fallback_classify(
            "I'm looking for a 3 bedroom RDP in Diepsloot"
        )
        assert result.intent == "property_search"
        assert result.entities.get("area") == "Diepsloot"
        assert result.entities.get("bedrooms") == 3

    def test_price_k_notation(self, intent_classifier):
        result = intent_classifier._fallback_classify(
            "house under R500K in Soweto"
        )
        assert result.intent == "property_search"
        assert result.entities.get("max_price") == 500000

    def test_price_m_notation(self, intent_classifier):
        result = intent_classifier._fallback_classify(
            "looking for property under 1.2M in Sandton"
        )
        assert result.intent == "property_search"
        assert result.entities.get("max_price") == 1_200_000
