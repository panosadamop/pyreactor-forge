"""Tests for the PyDL (JDL dialect) parser."""

import pytest

from pyreactor_forge import pydl

SHOP = """
/** A small shop model. */
entity Category {
  name String required unique maxlength(50)
  description TextBlob   // free text
}

entity Product(products_tbl) {
  name String required minlength(2) maxlength(100)
  price BigDecimal required min(0) max(999999)
  status Status required
  releasedOn LocalDate
}

enum Status {
  DRAFT, ACTIVE, DISCONTINUED
}

entity Tag {
  label String required
}

relationship ManyToOne {
  Product{category(name) required} to Category{products}
}

relationship ManyToMany {
  Product{tags} to Tag{products}
}

paginate Product, Category with pagination
dto * with mapstruct
"""


class TestParsing:
    def test_entities_fields_and_types(self):
        model = pydl.parse(SHOP)

        assert [entity.name for entity in model.entities] == ["Category", "Product", "Tag"]
        product = model.entity("Product")
        assert product.table_name == "products_tbl"
        assert [field.name for field in product.fields] == [
            "name",
            "price",
            "status",
            "releasedOn",
        ]

        name = product.fields[0]
        assert name.validations == {"required": True, "minlength": 2, "maxlength": 100}
        assert pydl.TYPE_MAP[name.type] == "string"
        assert pydl.TYPE_MAP[product.fields[3].type] == "date"

    def test_enum_and_comments(self):
        model = pydl.parse(SHOP)
        assert model.enum("Status").values == ["DRAFT", "ACTIVE", "DISCONTINUED"]

    def test_relationship_sides(self):
        model = pydl.parse(SHOP)
        many_to_one = model.relationships[0]
        assert many_to_one.kind == "ManyToOne"
        assert many_to_one.source.entity == "Product"
        assert many_to_one.source.field == "category"
        assert many_to_one.source.display == "name"
        assert many_to_one.source.required is True
        assert many_to_one.target.field == "products"

    def test_pattern_validation(self):
        model = pydl.parse("entity A {\n  code String pattern(/^[A-Z]+$/)\n}")
        assert model.entity("A").fields[0].validations["pattern"] == "^[A-Z]+$"

    def test_application_block_is_skipped_with_a_warning(self):
        model = pydl.parse(
            "application {\n  config { baseName shop }\n  entities *\n}\n"
            "entity A {\n  name String\n}"
        )
        assert [entity.name for entity in model.entities] == ["A"]
        assert any("application" in warning for warning in model.warnings)


class TestSpecConversion:
    def test_foreign_key_lands_on_the_many_side(self):
        specs = {spec["name"]: spec for spec in pydl.to_entity_specs(pydl.parse(SHOP))}

        product = [r for r in specs["Product"]["relationships"] if r["target"] == "Category"][0]
        assert product["kind"] == "many-to-one"
        assert product["name"] == "category"
        assert product["back_populates"] == "products"
        assert product["required"] is True
        assert product["display"] == "name"

        category = specs["Category"]["relationships"][0]
        assert category["kind"] == "one-to-many"
        assert category["target"] == "Product"
        assert category["name"] == "products"

    def test_one_to_many_declaration_puts_the_key_on_the_target(self):
        model = pydl.parse(
            "entity Category { name String }\n"
            "entity Product { name String }\n"
            "relationship OneToMany { Category{products} to Product{category} }"
        )
        specs = {spec["name"]: spec for spec in pydl.to_entity_specs(model)}
        assert specs["Product"]["relationships"][0]["kind"] == "many-to-one"
        assert specs["Category"]["relationships"][0]["kind"] == "one-to-many"

    def test_injected_names_default_to_the_other_entity(self):
        model = pydl.parse(
            "entity Category { name String }\n"
            "entity Product { name String }\n"
            "relationship ManyToOne { Product to Category }"
        )
        specs = {spec["name"]: spec for spec in pydl.to_entity_specs(model)}
        assert specs["Product"]["relationships"][0]["name"] == "category"
        assert specs["Category"]["relationships"] == []  # no injected field, no inverse

    def test_enum_field_becomes_a_string_with_values(self):
        specs = {spec["name"]: spec for spec in pydl.to_entity_specs(pydl.parse(SHOP))}
        status = [f for f in specs["Product"]["fields"] if f["name"] == "status"][0]
        assert status["type"] == "string"
        assert status["enum_values"] == ["DRAFT", "ACTIVE", "DISCONTINUED"]

    def test_options_apply_to_the_named_entities(self):
        specs = {spec["name"]: spec for spec in pydl.to_entity_specs(pydl.parse(SHOP))}
        assert specs["Product"]["options"]["paginate"] == "pagination"
        assert "paginate" not in specs["Tag"]["options"]
        assert specs["Tag"]["options"]["dto"] == "mapstruct"  # dto * with mapstruct

    def test_unsupported_options_are_reported(self):
        notes = pydl.describe_unsupported(pydl.parse(SHOP))
        assert any("'dto'" in note for note in notes)


class TestValidation:
    @pytest.mark.parametrize(
        "source,expected",
        [
            ("entity A {\n  name Strin\n}", "unknown type"),
            ("entity A {\n  name String\n}\nentity A {\n  x String\n}", "already defined"),
            ("entity A {\n  name String\n  name Integer\n}", "already defined"),
            ("entity A {\n  id String\n}", "reserved"),
            ("entity a {\n  name String\n}", "PascalCase"),
            ("entity A {\n  n String minlength(9) maxlength(2)\n}", "greater than"),
            ("entity A {\n  n Integer maxlength(2)\n}", "only applies to text"),
            ("entity A {\n  n String min(2)\n}", "only applies to numeric"),
            (
                "entity A {\n  n String\n}\nrelationship ManyToOne { A{b} to B{a} }",
                "unknown entity",
            ),
            ("entity A {\n  n String\n}\npaginate B with pagination", "unknown entity"),
        ],
    )
    def test_rejects(self, source, expected):
        with pytest.raises(pydl.PydlError) as excinfo:
            pydl.parse(source)
        assert expected in str(excinfo.value)

    def test_syntax_errors_carry_a_line_number(self):
        with pytest.raises(pydl.PydlError) as excinfo:
            pydl.parse("entity A {\n  name String\n\nentity B {\n  x String\n}")
        assert "line" in str(excinfo.value)

    def test_unknown_relationship_kind(self):
        with pytest.raises(pydl.PydlError) as excinfo:
            pydl.parse("entity A { n String }\nrelationship SomeToMany { A to A }")
        assert "unknown relationship kind" in str(excinfo.value)

    def test_relationship_to_the_builtin_user_is_allowed(self):
        model = pydl.parse(
            "entity Post {\n  title String\n}\nrelationship ManyToOne { Post{author} to User }"
        )
        specs = pydl.to_entity_specs(model)
        assert specs[0]["relationships"][0]["target"] == "User"
