# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

from dataclasses import dataclass
from typing import Optional

IS_CONFIG = "is_config"
CONFIG = "config"


@dataclass
class Config:
    stream_url: Optional[str]
    monitoring_instructions: Optional[str]
    l1_email: Optional[str]
    l1_phone: Optional[str]
    l2_email: Optional[str]
    l2_phone: Optional[str]


@dataclass
class Query:
    query: str
    session_id: str


@dataclass
class Payload:
    body: Query
