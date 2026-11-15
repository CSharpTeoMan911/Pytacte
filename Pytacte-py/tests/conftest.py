import os


def pytest_addoption(parser):
    parser.addoption(
        "--database-url",
        action="store",
        default=os.environ.get("FIREBASE_DATABASE_URL"),
        help="Firebase Realtime Database URL for integration tests",
    )
