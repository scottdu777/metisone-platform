from __future__ import annotations

import json

from metisone_ai_platform.semantic_layer.edit_service import (
    SemanticEditServiceClient,
)


def main() -> None:
    client = SemanticEditServiceClient()

    print("Health:")
    print(json.dumps(client.health(), indent=2, ensure_ascii=False))

    print("\nCubes:")
    print(json.dumps(client.list_cubes(), indent=2, ensure_ascii=False))

    print("\nChat endpoint is available. Example:")
    print(
        'client.chat(\'create measure revenue on payment sql amount type sum title "Revenue"\')'
    )


if __name__ == "__main__":
    main()
