"""Smoke manual: una sola consulta pequeña, fuera de la suite determinista."""

import json

from infrastructure.library_of_congress import LibraryOfCongressDocumentaryPresenceProbe


if __name__ == "__main__":
    result = LibraryOfCongressDocumentaryPresenceProbe().observe("wireless headphones")
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
