class InteractionManager:
    """
    Handles interactive collection of missing information.
    """

    def ask(self, skill, field: str) -> str:

        question = skill.input_questions.get(field)

        if question is None:
            question = self._default_question(field)

        return input(question + " ")

    def _default_question(self, field: str) -> str:
        """
        Generate a reasonable fallback question from a field name.
        """

        words = field.replace("_", " ")

        return f"What is the {words}?"