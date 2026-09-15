"""PyDL - a JHipster JDL dialect for PyReactor Forge.

The syntax is JDL's: the same `entity`, `enum`, `relationship` and option
declarations, the same validations, the same type names. Files use the `.pydl`
extension and are applied with `pyforge import-pydl`.

    entity Product {
      name String required maxlength(100)
      price BigDecimal required min(0)
      description TextBlob
    }

    relationship ManyToOne {
      Product{category} to Category{products}
    }

    paginate Product with pagination
"""

import re
from dataclasses import dataclass
from dataclasses import field as dc_field

from pyreactor_forge.naming import pluralize

# PyDL (JDL) types -> the internal field types the generators understand.
TYPE_MAP = {
    "String": "string",
    "TextBlob": "text",
    "Integer": "integer",
    "Long": "integer",
    "BigDecimal": "float",
    "Float": "float",
    "Double": "float",
    "Boolean": "boolean",
    "LocalDate": "date",
    "Instant": "datetime",
    "ZonedDateTime": "datetime",
    "Duration": "string",
    "UUID": "string",
    "Blob": "text",
    "AnyBlob": "text",
    "ImageBlob": "text",
}

# Accepted by the parser but degraded when generated; the warning says how.
DEGRADED_TYPES = {
    "Blob": "stored as text",
    "AnyBlob": "stored as text",
    "ImageBlob": "stored as text",
    "Duration": "stored as a string",
    "UUID": "stored as a string",
}

VALIDATIONS_NO_ARG = {"required", "unique"}
VALIDATIONS_WITH_ARG = {
    "minlength",
    "maxlength",
    "min",
    "max",
    "minbytes",
    "maxbytes",
    "pattern",
}

RELATIONSHIP_KINDS = {"OneToMany", "ManyToOne", "OneToOne", "ManyToMany"}

# Options carrying a value: `paginate Product with pagination`
VALUE_OPTIONS = {
    "paginate",
    "dto",
    "service",
    "search",
    "microservice",
    "angularSuffix",
    "clientRootFolder",
}
# Flag options: `filter Product`
FLAG_OPTIONS = {"filter", "skipClient", "skipServer", "readOnly", "noFluentMethod"}

# Options PyReactor Forge acts on; the rest are parsed and reported as ignored.
SUPPORTED_OPTIONS = {"paginate", "readOnly", "skipClient"}

RESERVED_FIELD_NAMES = {"id", "created_at", "updated_at"}

BLOCK_KEYWORDS = {"application", "deployment"}


class PydlError(Exception):
    """Raised when a .pydl file cannot be parsed or fails validation."""

    def __init__(self, problems: list[str]):
        self.problems = list(problems)
        super().__init__("\n".join(self.problems))


@dataclass
class Token:
    kind: str
    value: str
    line: int


@dataclass
class Field:
    name: str
    type: str
    validations: dict[str, object] = dc_field(default_factory=dict)
    line: int = 0


@dataclass
class Entity:
    name: str
    fields: list[Field] = dc_field(default_factory=list)
    table_name: str | None = None
    line: int = 0


@dataclass
class Enum:
    name: str
    values: list[str] = dc_field(default_factory=list)
    line: int = 0


@dataclass
class Side:
    entity: str
    field: str | None = None
    display: str | None = None
    required: bool = False


@dataclass
class Relationship:
    kind: str
    source: Side
    target: Side
    line: int = 0


@dataclass
class Option:
    name: str
    entities: list[str]
    value: str | None = None
    excluded: list[str] = dc_field(default_factory=list)
    line: int = 0


@dataclass
class PydlModel:
    entities: list[Entity] = dc_field(default_factory=list)
    enums: list[Enum] = dc_field(default_factory=list)
    relationships: list[Relationship] = dc_field(default_factory=list)
    options: list[Option] = dc_field(default_factory=list)
    warnings: list[str] = dc_field(default_factory=list)

    def entity(self, name: str) -> Entity | None:
        for entity in self.entities:
            if entity.name == name:
                return entity
        return None

    def enum(self, name: str) -> Enum | None:
        for enum in self.enums:
            if enum.name == name:
                return enum
        return None


TOKEN_RE = re.compile(
    r"""
      (?P<ws>\s+)
    | (?P<comment>//[^\n]*|/\*(?:[^*]|\*(?!/))*\*/)
    | (?P<regex>/[^/\n]+/)
    | (?P<number>-?\d+(?:\.\d+)?)
    | (?P<string>"[^"\n]*")
    | (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
    | (?P<punct>[{}(),*=<>:;.\[\]-])
    """,
    re.VERBOSE,
)


def tokenize(source: str) -> list[Token]:
    """Turn PyDL source into a token list, dropping whitespace and comments."""
    tokens: list[Token] = []
    pos, line = 0, 1
    while pos < len(source):
        match = TOKEN_RE.match(source, pos)
        if match is None:
            raise PydlError([f"line {line}: unexpected character {source[pos]!r}"])
        kind = match.lastgroup
        text = match.group()
        if kind not in ("ws", "comment"):
            tokens.append(Token(kind, text, line))
        line += text.count("\n")
        pos = match.end()
    tokens.append(Token("eof", "", line))
    return tokens


class _Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self.model = PydlModel()

    # -- token helpers ----------------------------------------------------
    @property
    def current(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        token = self.tokens[self.pos]
        if token.kind != "eof":
            self.pos += 1
        return token

    def at(self, value: str) -> bool:
        return self.current.value == value

    def at_keyword(self, word: str) -> bool:
        return self.current.kind == "ident" and self.current.value == word

    def fail(self, message: str):
        raise PydlError([f"line {self.current.line}: {message}"])

    def expect(self, value: str) -> Token:
        if not self.at(value):
            self.fail(f"expected {value!r}, found {self.current.value!r}")
        return self.advance()

    def expect_ident(self, what: str) -> Token:
        if self.current.kind != "ident":
            self.fail(f"expected {what}, found {self.current.value!r}")
        return self.advance()

    # -- grammar ----------------------------------------------------------
    def parse(self) -> PydlModel:
        while self.current.kind != "eof":
            word = self.current.value
            if word == "entity":
                self.parse_entity()
            elif word == "enum":
                self.parse_enum()
            elif word == "relationship":
                self.parse_relationship()
            elif word in VALUE_OPTIONS or word in FLAG_OPTIONS:
                self.parse_option()
            elif word in BLOCK_KEYWORDS:
                self.skip_block(word)
            else:
                self.fail(f"unexpected {self.current.value!r}")
        return self.model

    def parse_entity(self):
        line = self.advance().line  # 'entity'
        name = self.expect_ident("an entity name").value
        entity = Entity(name=name, line=line)

        if self.at("("):
            self.advance()
            entity.table_name = self.expect_ident("a table name").value
            self.expect(")")

        if self.at("{"):
            self.advance()
            while not self.at("}"):
                if self.current.kind == "eof":
                    raise PydlError([f"line {line}: unterminated entity {name!r}"])
                entity.fields.append(self.parse_field())
                if self.at(","):
                    self.advance()
            self.expect("}")

        self.model.entities.append(entity)

    def parse_field(self) -> Field:
        token = self.expect_ident("a field name")
        field = Field(name=token.value, type="", line=token.line)
        field.type = self.expect_ident("a field type").value

        while self.current.kind == "ident" and (
            self.current.value in VALIDATIONS_NO_ARG
            or self.current.value in VALIDATIONS_WITH_ARG
        ):
            rule = self.advance()
            if rule.value in VALIDATIONS_NO_ARG:
                field.validations[rule.value] = True
                continue

            self.expect("(")
            argument = self.advance()
            if rule.value == "pattern":
                if argument.kind != "regex":
                    raise PydlError([f"line {argument.line}: pattern() expects /a regex/"])
                field.validations["pattern"] = argument.value[1:-1]
            else:
                if argument.kind != "number":
                    raise PydlError(
                        [f"line {argument.line}: {rule.value}() expects a number"]
                    )
                text = argument.value
                field.validations[rule.value] = float(text) if "." in text else int(text)
            self.expect(")")

        return field

    def parse_enum(self):
        line = self.advance().line  # 'enum'
        name = self.expect_ident("an enum name").value
        enum = Enum(name=name, line=line)
        self.expect("{")
        while not self.at("}"):
            if self.current.kind == "eof":
                raise PydlError([f"line {line}: unterminated enum {name!r}"])
            enum.values.append(self.expect_ident("an enum value").value)
            if self.at("("):  # JDL allows VALUE (custom value)
                self.advance()
                self.advance()
                self.expect(")")
            if self.at(","):
                self.advance()
        self.expect("}")
        self.model.enums.append(enum)

    def parse_relationship(self):
        line = self.advance().line  # 'relationship'
        kind = self.expect_ident("a relationship kind").value
        if kind not in RELATIONSHIP_KINDS:
            raise PydlError(
                [
                    f"line {line}: unknown relationship kind {kind!r} (expected one of "
                    f"{', '.join(sorted(RELATIONSHIP_KINDS))})"
                ]
            )
        self.expect("{")
        while not self.at("}"):
            if self.current.kind == "eof":
                raise PydlError([f"line {line}: unterminated relationship block"])
            source = self.parse_side()
            if not self.at_keyword("to"):
                self.fail(f"expected 'to', found {self.current.value!r}")
            self.advance()
            target = self.parse_side()
            self.model.relationships.append(
                Relationship(kind=kind, source=source, target=target, line=line)
            )
            if self.at(","):
                self.advance()
        self.expect("}")

    def parse_side(self) -> Side:
        side = Side(entity=self.expect_ident("an entity name").value)
        if self.at("{"):
            self.advance()
            side.field = self.expect_ident("an injected field name").value
            if self.at("("):
                self.advance()
                side.display = self.expect_ident("a display field name").value
                self.expect(")")
            if self.at_keyword("required"):
                self.advance()
                side.required = True
            self.expect("}")
        return side

    def parse_option(self):
        token = self.advance()
        name, line = token.value, token.line
        entities, excluded = self.parse_entity_list()
        value = None
        if self.at_keyword("with"):
            self.advance()
            value = self.expect_ident("an option value").value
        elif name in VALUE_OPTIONS:
            raise PydlError([f"line {line}: option {name!r} needs a 'with <value>' clause"])
        self.model.options.append(
            Option(name=name, entities=entities, value=value, excluded=excluded, line=line)
        )

    def parse_entity_list(self):
        entities: list[str] = []
        excluded: list[str] = []
        if self.at("*") or self.at_keyword("all"):
            self.advance()
            entities.append("*")
        else:
            entities.append(self.expect_ident("an entity name").value)
            while self.at(","):
                self.advance()
                entities.append(self.expect_ident("an entity name").value)
        if self.at_keyword("except"):
            self.advance()
            excluded.append(self.expect_ident("an entity name").value)
            while self.at(","):
                self.advance()
                excluded.append(self.expect_ident("an entity name").value)
        return entities, excluded

    def skip_block(self, keyword: str):
        line = self.advance().line
        self.model.warnings.append(
            f"line {line}: '{keyword}' blocks are ignored - "
            f"use 'pyforge new' to configure the application itself"
        )
        if not self.at("{"):
            return
        depth = 0
        while self.current.kind != "eof":
            if self.at("{"):
                depth += 1
            elif self.at("}"):
                depth -= 1
                if depth == 0:
                    self.advance()
                    return
            self.advance()
        raise PydlError([f"line {line}: unterminated '{keyword}' block"])


def parse(source: str) -> PydlModel:
    """Parse PyDL source and validate it. Raises PydlError with every problem."""
    model = _Parser(tokenize(source)).parse()
    problems = validate(model)
    if problems:
        raise PydlError(problems)
    return model


def parse_file(path) -> PydlModel:
    """Parse a .pydl file from disk."""
    return parse(path.read_text(encoding="utf-8"))


def validate(model: PydlModel) -> list[str]:
    """Return every semantic problem found in a parsed model."""
    problems: list[str] = []
    enum_names = {enum.name for enum in model.enums}
    seen_entities: dict[str, int] = {}

    for enum in model.enums:
        if not enum.values:
            problems.append(f"line {enum.line}: enum {enum.name!r} has no values")

    for entity in model.entities:
        if entity.name in seen_entities:
            problems.append(
                f"line {entity.line}: entity {entity.name!r} is already defined "
                f"on line {seen_entities[entity.name]}"
            )
            continue
        seen_entities[entity.name] = entity.line

        if not entity.name[0].isupper():
            problems.append(
                f"line {entity.line}: entity name {entity.name!r} must be PascalCase"
            )

        seen_fields: dict[str, int] = {}
        for field in entity.fields:
            if field.name in RESERVED_FIELD_NAMES:
                problems.append(
                    f"line {field.line}: {entity.name}.{field.name} is reserved - "
                    f"every entity already has id, created_at and updated_at"
                )
            if field.name in seen_fields:
                problems.append(
                    f"line {field.line}: {entity.name}.{field.name} is already defined "
                    f"on line {seen_fields[field.name]}"
                )
            seen_fields[field.name] = field.line

            if field.type not in TYPE_MAP and field.type not in enum_names:
                problems.append(
                    f"line {field.line}: unknown type {field.type!r} for "
                    f"{entity.name}.{field.name} (known types: "
                    f"{', '.join(sorted(TYPE_MAP))})"
                )
            problems.extend(_validate_field_rules(entity, field))

        if entity.name in enum_names:
            problems.append(
                f"line {entity.line}: {entity.name!r} is declared as both an entity and an enum"
            )

    for relationship in model.relationships:
        for side in (relationship.source, relationship.target):
            if side.entity == "User":
                continue  # the built-in user table
            if model.entity(side.entity) is None:
                problems.append(
                    f"line {relationship.line}: relationship references unknown "
                    f"entity {side.entity!r}"
                )
        if relationship.source.entity == relationship.target.entity and (
            relationship.kind == "ManyToMany"
        ):
            problems.append(
                f"line {relationship.line}: self-referencing ManyToMany is not supported"
            )

    for option in model.options:
        for name in option.entities + option.excluded:
            if name != "*" and model.entity(name) is None:
                problems.append(
                    f"line {option.line}: option {option.name!r} references unknown "
                    f"entity {name!r}"
                )

    return problems


def _validate_field_rules(entity: Entity, field: Field) -> list[str]:
    problems: list[str] = []
    rules = field.validations
    internal = TYPE_MAP.get(field.type, "string")

    for length_rule in ("minlength", "maxlength"):
        if length_rule in rules and internal not in ("string", "text"):
            problems.append(
                f"line {field.line}: {length_rule}() only applies to text fields, "
                f"not {entity.name}.{field.name} ({field.type})"
            )
    for bound_rule in ("min", "max"):
        if bound_rule in rules and internal not in ("integer", "float"):
            problems.append(
                f"line {field.line}: {bound_rule}() only applies to numeric fields, "
                f"not {entity.name}.{field.name} ({field.type})"
            )
    if "pattern" in rules and internal not in ("string", "text"):
        problems.append(
            f"line {field.line}: pattern() only applies to text fields, "
            f"not {entity.name}.{field.name} ({field.type})"
        )

    lo, hi = rules.get("minlength"), rules.get("maxlength")
    if isinstance(lo, int) and isinstance(hi, int) and lo > hi:
        problems.append(
            f"line {field.line}: {entity.name}.{field.name} has "
            f"minlength({lo}) greater than maxlength({hi})"
        )
    lo, hi = rules.get("min"), rules.get("max")
    if isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and lo > hi:
        problems.append(
            f"line {field.line}: {entity.name}.{field.name} has "
            f"min({lo}) greater than max({hi})"
        )
    return problems


def _default_field_name(other_entity: str, many: bool) -> str:
    base = other_entity[0].lower() + other_entity[1:]
    return pluralize(base) if many else base


def _relationship_pairs(relationship: Relationship):
    """Return (owner_side, inverse_side, owner_kind, inverse_kind).

    The owner is the side that carries the foreign key, exactly as in JDL:
    ManyToOne/OneToOne/ManyToMany put it on the source, OneToMany on the target.
    """
    if relationship.kind == "OneToMany":
        return relationship.target, relationship.source, "many-to-one", "one-to-many"
    if relationship.kind == "ManyToOne":
        return relationship.source, relationship.target, "many-to-one", "one-to-many"
    if relationship.kind == "OneToOne":
        return relationship.source, relationship.target, "one-to-one", "one-to-one-inverse"
    return relationship.source, relationship.target, "many-to-many", "many-to-many-inverse"


def to_entity_specs(model: PydlModel) -> list[dict]:
    """Convert a parsed PyDL model into entity specs the generators consume."""
    specs: dict[str, dict] = {}
    for entity in model.entities:
        specs[entity.name] = {
            "name": entity.name,
            "table": entity.table_name,
            "fields": [_field_spec(model, field) for field in entity.fields],
            "relationships": [],
            "options": {},
        }

    for relationship in model.relationships:
        owner, inverse, owner_kind, inverse_kind = _relationship_pairs(relationship)
        owner_many = owner_kind in ("one-to-many", "many-to-many", "many-to-many-inverse")
        inverse_many = inverse_kind in ("one-to-many", "many-to-many", "many-to-many-inverse")
        owner_name = owner.field or _default_field_name(inverse.entity, owner_many)
        inverse_name = inverse.field or _default_field_name(owner.entity, inverse_many)

        if owner.entity in specs:
            specs[owner.entity]["relationships"].append(
                {
                    "kind": owner_kind,
                    "target": inverse.entity,
                    "name": owner_name,
                    "back_populates": inverse_name if inverse.field else None,
                    "required": owner.required,
                    "display": owner.display,
                }
            )
        if inverse.entity in specs and inverse.field:
            specs[inverse.entity]["relationships"].append(
                {
                    "kind": inverse_kind,
                    "target": owner.entity,
                    "name": inverse_name,
                    "back_populates": owner_name,
                    "required": False,
                    "display": inverse.display,
                }
            )

    for option in model.options:
        targets = (
            [name for name in specs if name not in option.excluded]
            if option.entities == ["*"]
            else [name for name in option.entities if name not in option.excluded]
        )
        for name in targets:
            if name in specs:
                specs[name]["options"][option.name] = (
                    option.value if option.value is not None else True
                )

    return [specs[entity.name] for entity in model.entities]


def _field_spec(model: PydlModel, field: Field) -> dict:
    enum = model.enum(field.type)
    rules = field.validations
    spec = {
        "name": field.name,
        "type": TYPE_MAP.get(field.type, "string"),
        "pydl_type": field.type,
        "required": bool(rules.get("required", False)),
        "unique": bool(rules.get("unique", False)),
    }
    for rule in ("minlength", "maxlength", "min", "max", "pattern"):
        if rule in rules:
            spec[rule] = rules[rule]
    if enum is not None:
        spec["enum"] = enum.name
        spec["enum_values"] = list(enum.values)
    return spec


def describe_unsupported(model: PydlModel) -> list[str]:
    """Warnings for declarations parsed faithfully but not acted on."""
    notes: list[str] = list(model.warnings)

    for option in model.options:
        if option.name not in SUPPORTED_OPTIONS:
            notes.append(
                f"line {option.line}: option '{option.name}' is a JHipster/Java concept "
                f"with no PyReactor Forge equivalent - ignored"
            )

    degraded = {}
    for entity in model.entities:
        for field in entity.fields:
            if field.type in DEGRADED_TYPES:
                degraded.setdefault(field.type, []).append(f"{entity.name}.{field.name}")
    for pydl_type, where in sorted(degraded.items()):
        notes.append(
            f"type {pydl_type} is {DEGRADED_TYPES[pydl_type]} ({', '.join(sorted(where))})"
        )

    enum_fields = []
    for entity in model.entities:
        for field in entity.fields:
            if model.enum(field.type) is not None:
                enum_fields.append(f"{entity.name}.{field.name}")
    if enum_fields:
        notes.append(
            "enum fields are stored as strings and validated against their values "
            f"({', '.join(sorted(enum_fields))})"
        )

    return notes
