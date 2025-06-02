# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

from sqlalchemy import create_engine
from llama_index.core.objects import ObjectIndex, SQLTableNodeMapping, SQLTableSchema
from llama_index.core.indices.struct_store import SQLTableRetrieverQueryEngine
from llama_index.core import VectorStoreIndex, SQLDatabase, Settings
from llama_index.embeddings.bedrock import BedrockEmbedding
from llama_index.core.prompts import Prompt
from connections import Connections
from prompt_templates import SQL_TEMPLATE_STR, RESPONSE_TEMPLATE_STR, table_details
from llama_index.core.prompts import PromptTemplate
from connections import Connections

logger = Connections.logger


def create_sql_engine():
    """
    Connects to Amazon Athena.

    Args:
        None

    Returns:
        engine (sqlalchemy.engine.base.Engine): SQL Alchemy engine.
    """
    s3_staging_dir = Connections.athena_bucket_name
    region = Connections.region_name
    database = Connections.text2sql_database
    # Construct the connection string
    conn_url = f"awsathena+rest://athena.{region}.amazonaws.com/{database}?s3_staging_dir=s3://{s3_staging_dir}"
    # Create an SQLAlchemy engine
    engine = create_engine(conn_url)
    return engine


SQL_PROMPT = PromptTemplate(SQL_TEMPLATE_STR)

RESPONSE_PROMPT = Prompt(RESPONSE_TEMPLATE_STR)


def create_query_engine():
    """Generates a query engine and object index fo answering questions using SQL retrieval.

    Args:
        SQL_PROMPT (PromptTemplate): Prompt for generating SQL. Defaults to SQL_PROMPT.
        RESPONSE_PROMPT (Prompt): Prompt for generating final response. Defaults to RESPONSE_PROMPT.

    Returns:
        query_engine (SQLTableRetrieverQueryEngine): SQLTableRetrieverQueryEngine object.
        obj_index (ObjectIndex): ObjectIndex object.
    """
    # create sql database object
    engine = create_sql_engine()
    sql_database = SQLDatabase(engine, sample_rows_in_table_info=5)

    embed_model = BedrockEmbedding(
        client=Connections.bedrock_client, model_name="amazon.titan-embed-text-v1"
    )

    # initialize llm
    llm = Connections.get_bedrock_llm(max_tokens=1024)

    Settings.llm = llm
    Settings.embed_model = embed_model

    table_node_mapping = SQLTableNodeMapping(sql_database)
    table_schema_objs = []
    tables = list(sql_database._all_tables)
    for table in tables:
        table_schema_objs.append(
            (SQLTableSchema(table_name=table, context_str=table_details[table]))
        )

    obj_index = ObjectIndex.from_objects(
        table_schema_objs,
        table_node_mapping,
        VectorStoreIndex,
    )

    query_engine = SQLTableRetrieverQueryEngine(
        sql_database,
        obj_index.as_retriever(similarity_top_k=5),
        text_to_sql_prompt=SQL_PROMPT,
        response_synthesis_prompt=RESPONSE_PROMPT,
    )
    prompts_dict = query_engine.get_prompts()
    logger.info(f"prompts_dict{prompts_dict}")

    return query_engine, obj_index


query_engine, obj_index = create_query_engine()
