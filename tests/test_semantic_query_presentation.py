from metisone_ai_platform.semantic_query.presentation import format_query_answer


def test_formats_action_movie_count_as_natural_language() -> None:
    answer = format_query_answer(
        [{"film.count": 64}],
        question="how many action movies are there?",
    )

    assert answer == "There are 64 Action movies."


def test_formats_action_actor_count_as_natural_language() -> None:
    answer = format_query_answer(
        [{"actor.count": 166}],
        question="how many actors were playing in action movies?",
    )

    assert answer == "There are 166 actors who appeared in Action movies."


def test_uses_response_hint_for_non_count_scalar_answer() -> None:
    answer = format_query_answer(
        [{"film.title": "Spy Mile"}],
        question="Check if film titled Spy Mile exists",
        response_hint="Matching film title",
    )

    assert answer == "Matching film title: Spy Mile."
