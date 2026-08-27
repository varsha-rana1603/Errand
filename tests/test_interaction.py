from errand.core.interaction import InteractionType, UserInteraction


def test_input_interaction():

    interaction = UserInteraction(
        type=InteractionType.INPUT,
        prompt="What's the recipient's email address?",
        field="recipient_email",
    )

    assert interaction.type == InteractionType.INPUT
    assert interaction.prompt == "What's the recipient's email address?"
    assert interaction.field == "recipient_email"


def test_confirmation_interaction():

    interaction = UserInteraction(
        type=InteractionType.CONFIRMATION,
        prompt="Send it? [y/N]",
    )

    assert interaction.type == InteractionType.CONFIRMATION
    assert interaction.field is None


def test_edit_interaction():

    interaction = UserInteraction(
        type=InteractionType.EDIT,
        prompt="Edit the generated message:",
        field="body",
    )

    assert interaction.type == InteractionType.EDIT
    assert interaction.field == "body"