# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

from aws_cdk import (
    aws_glue as glue,
    aws_iam as iam,
    Aws,
)
from constructs import Construct
from cdk_nag import NagSuppressions


class DatabaseConstruct(Construct):
    def __init__(
        self, scope: Construct, id: str, athena_bucket, kms_key, config, **kwargs
    ):
        super().__init__(scope, id)

        self.glue_role = self._create_glue_role(athena_bucket, kms_key)
        self.glue_database = self._create_glue_database()
        self.glue_crawler = self._create_glue_crawler(athena_bucket, kms_key, config)

    def _create_glue_role(self, athena_bucket, kms_key):
        glue_role = iam.Role(
            self,
            "GlueRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSGlueServiceRole"
                )
            ],
        )
        athena_bucket.grant_read(glue_role)
        kms_key.grant_encrypt_decrypt(glue_role)
        glue_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=["*"],
                actions=["logs:AssociateKmsKey"],
            )
        )
        return glue_role

    def _create_glue_database(self):
        return glue.CfnDatabase(
            self,
            "AgentTextToSQLDatabase",
            catalog_id=Aws.ACCOUNT_ID,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name=f"{Aws.STACK_NAME}-text2sql-db"
            ),
        )

    def _create_glue_crawler(self, athena_bucket, kms_key, config):
        security_config = glue.CfnSecurityConfiguration(
            self,
            "SecurityConfiguration",
            encryption_configuration=glue.CfnSecurityConfiguration.EncryptionConfigurationProperty(
                cloud_watch_encryption=glue.CfnSecurityConfiguration.CloudWatchEncryptionProperty(
                    cloud_watch_encryption_mode="SSE-KMS", kms_key_arn=kms_key.key_arn
                ),
                s3_encryptions=[
                    glue.CfnSecurityConfiguration.S3EncryptionProperty(
                        kms_key_arn=kms_key.key_arn, s3_encryption_mode="SSE-KMS"
                    )
                ],
            ),
            name=f"{Aws.STACK_NAME}-security-config",
        )

        crawler = glue.CfnCrawler(
            self,
            "text2sqlTableCrawler",
            role=self.glue_role.role_name,
            crawler_security_configuration=security_config.name,
            targets=glue.CfnCrawler.TargetsProperty(
                s3_targets=[
                    glue.CfnCrawler.S3TargetProperty(
                        path=f"s3://{athena_bucket.bucket_name}/{config['paths']['athena_data_destination_prefix']}/{config['paths']['athena_table_data_prefix']}",
                    )
                ]
            ),
            database_name=self.glue_database.ref,
            description="Crawler job for Bedrock Agent text to SQL table",
            name=f"{Aws.STACK_NAME}-text2sql-table-crawler",
        )

        NagSuppressions.add_resource_suppressions(
            crawler,
            suppressions=[
                {
                    "id": "AwsSolutions-GL1",
                    "reason": "Logs encryption enabled for the crawler. False positive warning",
                }
            ],
        )

        return crawler
