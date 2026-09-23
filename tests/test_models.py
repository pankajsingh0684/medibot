from medibot.models import (
    COLLECTION_ACCESS_ROLES,
    ROLE_COLLECTIONS,
    Collection,
    Role,
)


def test_role_collection_access_matches_assignment() -> None:
    assert ROLE_COLLECTIONS[Role.DOCTOR] == [Collection.CLINICAL, Collection.GENERAL]
    assert ROLE_COLLECTIONS[Role.NURSE] == [Collection.NURSING, Collection.GENERAL]
    assert ROLE_COLLECTIONS[Role.BILLING_EXECUTIVE] == [
        Collection.BILLING,
        Collection.GENERAL,
    ]
    assert ROLE_COLLECTIONS[Role.TECHNICIAN] == [
        Collection.EQUIPMENT,
        Collection.GENERAL,
    ]
    assert ROLE_COLLECTIONS[Role.ADMIN] == list(Collection)


def test_collection_access_roles_are_inverse_mapping() -> None:
    for collection, roles in COLLECTION_ACCESS_ROLES.items():
        assert all(collection in ROLE_COLLECTIONS[role] for role in roles)
