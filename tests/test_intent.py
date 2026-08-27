from errand.core.intent import Intent


def test_intent_creation():
    intent = Intent(
        action="open_url",
        fields={
            "url": "https://youtube.com",
            "browser": "Safari",
        },
    )

    assert intent.action == "open_url"
    assert intent.fields["url"] == "https://youtube.com"
    assert intent.fields["browser"] == "Safari"


def test_intent_can_have_missing_fields():
    intent = Intent(
        action="send_email",
        fields={
            "recipient_name": "PR Deepa",
            "recipient_email": None,
            "body": "I'll be late to class",
        },
    )

    assert intent.fields["recipient_email"] is None