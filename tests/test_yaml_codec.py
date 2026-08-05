from metisone_ai_platform.semantic_edit.cube_yaml.yaml_codec import YamlCodec


def test_yaml_codec_dumps_flow_style_as_block_style() -> None:
    codec = YamlCodec()
    data = codec.load(
        "\n".join(
            [
                "pre_aggregations:",
                "  [",
                "    {",
                "      name: main,",
                "      measures: [ film_category.count ],",
                "      dimensions: [ film_category.category.name, actor.full_name ]",
                "    }",
                "  ]",
                "",
            ]
        )
    )

    dumped = codec.dump(data)

    assert "{" not in dumped
    assert "}" not in dumped
    assert "[ film_category.count ]" not in dumped
    assert "- name: main" in dumped
    assert "measures:" in dumped
    assert "- film_category.count" in dumped
