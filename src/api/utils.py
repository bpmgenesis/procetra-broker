import shortuuid


def create_id() -> str:
    shortuuid.set_alphabet("23456789ABCDEFGHJKLMNPQRSTUVWXYZ")
    return shortuuid.random(length=12)