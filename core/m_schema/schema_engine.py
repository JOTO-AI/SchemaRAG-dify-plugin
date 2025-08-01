from typing import Dict, List, Optional
from sqlalchemy import (
    MetaData,
    Table,
    select,
)

from sqlalchemy.engine import Engine
from llama_index.core import SQLDatabase
from utils import examples_to_str
from core.m_schema.m_schema import MSchema


class SchemaEngine(SQLDatabase):
    def __init__(
        self,
        engine: Engine,
        schema: Optional[str] = None,
        metadata: Optional[MetaData] = None,
        ignore_tables: Optional[List[str]] = None,
        include_tables: Optional[List[str]] = None,
        sample_rows_in_table_info: int = 3,
        indexes_in_table_info: bool = False,
        custom_table_info: Optional[dict] = None,
        view_support: bool = False,
        max_string_length: int = 300,
        mschema: Optional[MSchema] = None,
        db_name: Optional[str] = "",
    ):
        super().__init__(
            engine,
            schema,
            metadata,
            ignore_tables,
            include_tables,
            sample_rows_in_table_info,
            indexes_in_table_info,
            custom_table_info,
            view_support,
            max_string_length,
        )

        self._db_name = db_name
        # Dictionary to store table names and their corresponding schema
        self._tables_schemas: Dict[
            str, str
        ] = {}  # For MySQL and similar databases, if no schema is specified but db_name is provided,
        # use db_name as the schema to avoid getting tables from all databases
        if schema is None and db_name:
            if self._engine.dialect.name == "mysql":
                schema = db_name
            elif self._engine.dialect.name == "postgresql":
                # For PostgreSQL, use 'public' as default schema
                schema = "public"

        # If a schema is specified, filter by that schema and store that value for every table.
        if schema:
            self._usable_tables = [
                table_name
                for table_name in self._usable_tables
                if self._inspector.has_table(table_name, schema)
            ]
            for table_name in self._usable_tables:
                self._tables_schemas[table_name] = schema
        else:
            all_tables = []
            # Iterate through all available schemas
            for s in self.get_schema_names():
                tables = self._inspector.get_table_names(schema=s)
                all_tables.extend(tables)
                for table in tables:
                    self._tables_schemas[table] = s
            self._usable_tables = all_tables

        self._dialect = engine.dialect.name
        if mschema is not None:
            self._mschema = mschema
        else:
            self._mschema = MSchema(db_id=db_name, schema=schema)
            self.init_mschema()

    @property
    def mschema(self) -> MSchema:
        """Return M-Schema"""
        return self._mschema

    def get_pk_constraint(self, table_name: str) -> Dict:
        return self._inspector.get_pk_constraint(
            table_name, self._tables_schemas[table_name]
        )["constrained_columns"]

    def get_table_comment(self, table_name: str):
        try:
            return self._inspector.get_table_comment(
                table_name, self._tables_schemas[table_name]
            )["text"]
        except Exception:  # sqlite does not support comments
            return ""

    def default_schema_name(self) -> Optional[str]:
        return self._inspector.default_schema_name

    def get_schema_names(self) -> List[str]:
        return self._inspector.get_schema_names()

    def get_foreign_keys(self, table_name: str):
        return self._inspector.get_foreign_keys(
            table_name, self._tables_schemas[table_name]
        )

    def get_unique_constraints(self, table_name: str):
        return self._inspector.get_unique_constraints(
            table_name, self._tables_schemas[table_name]
        )

    def fectch_distinct_values(
        self, table_name: str, column_name: str, max_num: int = 5
    ):
        table = Table(
            table_name,
            self.metadata_obj,
            autoload_with=self._engine,
            schema=self._tables_schemas[table_name],
        )
        # Construct SELECT DISTINCT query
        query = select(table.c[column_name]).distinct().limit(max_num)
        values = []
        with self._engine.connect() as connection:
            result = connection.execute(query)
            distinct_values = result.fetchall()
            for value in distinct_values:
                if value[0] is not None and value[0] != "":
                    values.append(value[0])
        return values

    def init_mschema(self):
        # print(f"Debug: Database dialect = {self._engine.dialect.name}")
        # print(f"Debug: DB name = {self._db_name}")
        # print(f"Debug: Available schemas = {self.get_schema_names()}")
        # print(f"Debug: Usable tables = {self._usable_tables}")
        # print(f"Debug: Tables schemas mapping = {self._tables_schemas}")

        for table_name in self._usable_tables:
            table_comment = self.get_table_comment(table_name)
            table_comment = (
                "" if table_comment is None else table_comment.strip()
            )  # For MySQL, avoid duplicate schema name in table identifier
            # For PostgreSQL, include schema name if it's not 'public'
            schema_name = self._tables_schemas[table_name]
            if self._engine.dialect.name == "mysql" and schema_name == self._db_name:
                table_with_schema = table_name
            elif self._engine.dialect.name == "postgresql" and schema_name == "public":
                table_with_schema = table_name
            else:
                table_with_schema = schema_name + "." + table_name
            self._mschema.add_table(table_with_schema, fields={}, comment=table_comment)
            pks = self.get_pk_constraint(table_name)

            fks = self.get_foreign_keys(table_name)
            for fk in fks:
                referred_schema = fk["referred_schema"]
                for c, r in zip(fk["constrained_columns"], fk["referred_columns"]):
                    self._mschema.add_foreign_key(
                        table_with_schema, c, referred_schema, fk["referred_table"], r
                    )

            fields = self._inspector.get_columns(
                table_name, schema=self._tables_schemas[table_name]
            )
            for field in fields:
                field_type = f"{field['type']!s}"
                field_name = field["name"]
                primary_key = field_name in pks
                field_comment = field.get("comment", None)
                field_comment = "" if field_comment is None else field_comment.strip()
                autoincrement = field.get("autoincrement", False)
                default = field.get("default", None)
                if default is not None:
                    default = f"{default}"

                try:
                    examples = self.fectch_distinct_values(table_name, field_name, 5)
                except Exception:
                    examples = []
                examples = examples_to_str(examples)

                self._mschema.add_field(
                    table_with_schema,
                    field_name,
                    field_type=field_type,
                    primary_key=primary_key,
                    nullable=field["nullable"],
                    default=default,
                    autoincrement=autoincrement,
                    comment=field_comment,
                    examples=examples,
                )
