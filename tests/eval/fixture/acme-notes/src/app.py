"""Acme Notes: a tiny in-memory notes app."""

NOTES: list[dict] = []


def add_note(title: str, body: str = "") -> dict:
    note = {"title": title, "body": body}
    NOTES.append(note)
    return note


def search(query: str) -> list[dict]:
    q = query.lower()
    return [n for n in NOTES if q in n["title"].lower()]


if __name__ == "__main__":
    add_note("hello", "first note")
    print(search("hel"))
