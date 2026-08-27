from errand.core.intent import Intent
from errand.parser.gemini import parsed_intent_to_intent
from errand.parser.schema import ParsedField, ParsedIntent


def make_parsed_intent(action, **fields):
    return ParsedIntent(
        action=action,
        fields=[
            ParsedField(name=name, value=value)
            for name, value in fields.items()
        ],
    )


def test_play_music():
    parsed = make_parsed_intent(
        "play_music",
        track="Criminal",
        artist="Britney Spears",
    )

    intent = parsed_intent_to_intent(parsed)

    assert intent.action == "play_music"
    assert intent.fields["track"] == "Criminal"
    assert intent.fields["artist"] == "Britney Spears"


def test_play_music_with_platform():
    parsed = make_parsed_intent(
        "play_music",
        track="Black Swan",
        artist="BTS",
        platform="Spotify",
    )

    intent = parsed_intent_to_intent(parsed)

    assert intent.action == "play_music"
    assert intent.fields["track"] == "Black Swan"
    assert intent.fields["artist"] == "BTS"
    assert intent.fields["platform"] == "Spotify"


def test_play_music_without_platform():
    parsed = make_parsed_intent(
        "play_music",
        track="Criminal",
        artist="Britney Spears",
    )

    intent = parsed_intent_to_intent(parsed)

    assert intent.action == "play_music"
    assert intent.fields["track"] == "Criminal"
    assert intent.fields["artist"] == "Britney Spears"

    assert "platform" not in intent.fields


def test_open_url():
    parsed = make_parsed_intent(
        "open_url",
        url="https://youtube.com",
        browser="Safari",
    )

    intent = parsed_intent_to_intent(parsed)

    assert intent.action == "open_url"
    assert intent.fields["url"] == "https://youtube.com"
    assert intent.fields["browser"] == "Safari"


def test_send_email():
    parsed = make_parsed_intent(
        "send_email",
        recipient_name="Deepa",
        recipient_email=None,
        body="I'll be late",
    )

    intent = parsed_intent_to_intent(parsed)

    assert intent.action == "send_email"
    assert intent.fields["recipient_name"] == "Deepa"
    assert intent.fields["recipient_email"] is None
    assert intent.fields["body"] == "I'll be late"

def test_parsed_intent_json():
    json_response = """
    {
        "action": "play_music",
        "fields": [
            {
                "name": "track",
                "value": "Criminal"
            },
            {
                "name": "artist",
                "value": "Britney Spears"
            }
        ]
    }
    """

    parsed = ParsedIntent.model_validate_json(json_response)

    assert parsed.action == "play_music"
    assert len(parsed.fields) == 2

    assert parsed.fields[0].name == "track"
    assert parsed.fields[0].value == "Criminal"

    assert parsed.fields[1].name == "artist"
    assert parsed.fields[1].value == "Britney Spears"

def test_missing_email_is_preserved():
    parsed = make_parsed_intent(
        "send_email",
        recipient_name="Deepa",
        recipient_email=None,
        body="I'll be late to class",
    )

    intent = parsed_intent_to_intent(parsed)

    assert intent.fields["recipient_name"] == "Deepa"
    assert intent.fields["recipient_email"] is None
    assert intent.fields["body"] == "I'll be late to class"