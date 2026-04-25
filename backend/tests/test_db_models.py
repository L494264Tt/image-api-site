from app.models import ImageGeneration, User


def test_models_export_expected_tables() -> None:
    assert User.__tablename__ == "users"
    assert ImageGeneration.__tablename__ == "image_generations"
