# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import os
from aws_cdk import (
    aws_kms as kms,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    RemovalPolicy,
    CfnOutput,
    aws_iam as iam,
    Aws,
    Duration,
)
from constructs import Construct
from cdk_nag import NagSuppressions


class StorageConstruct(Construct):
    def __init__(self, scope: Construct, id: str, config: dict, **kwargs):
        super().__init__(scope, id)

        self.kms_key = self._create_kms_key()
        self.agent_assets_bucket, self.athena_bucket = self._create_buckets()
        self._upload_files_to_s3(config)

    def _create_kms_key(self):
        kms_key = kms.Key(
            self,
            "KMSKey",
            alias=f"alias/{Aws.STACK_NAME}/genai_key",
            enable_key_rotation=True,
            pending_window=Duration.days(7),
            removal_policy=RemovalPolicy.DESTROY,
        )
        kms_key.grant_encrypt_decrypt(
            iam.AnyPrincipal().with_conditions(
                {
                    "StringEquals": {
                        "kms:CallerAccount": f"{Aws.ACCOUNT_ID}",
                        "kms:ViaService": f"s3.{Aws.REGION}.amazonaws.com",
                    },
                }
            )
        )

        kms_key.grant_encrypt_decrypt(
            iam.ServicePrincipal(f"logs.{Aws.REGION}.amazonaws.com")
        )
        return kms_key

    def _create_buckets(self):
        agent_assets_bucket = s3.Bucket(
            self,
            "AgentAssetsSourceBaseBucket",
            bucket_name=f"{Aws.STACK_NAME}-agent-assets-bucket-{Aws.ACCOUNT_ID}",
            versioned=True,
            auto_delete_objects=True,
            removal_policy=RemovalPolicy.DESTROY,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.kms_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )
        NagSuppressions.add_resource_suppressions(
            agent_assets_bucket,
            suppressions=[
                {
                    "id": "AwsSolutions-S1",
                    "reason": "Demo app hence server access logs not enabled",
                }
            ],
        )

        athena_bucket = s3.Bucket(
            self,
            "AthenaSourceBucket",
            bucket_name=f"{Aws.STACK_NAME}-athena-bucket-{Aws.ACCOUNT_ID}",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.kms_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )
        NagSuppressions.add_resource_suppressions(
            athena_bucket,
            suppressions=[
                {
                    "id": "AwsSolutions-S1",
                    "reason": "Demo app hence server access logs not enabled",
                }
            ],
        )
        return agent_assets_bucket, athena_bucket

    def _upload_files_to_s3(self, config):
        s3deploy.BucketDeployment(
            self,
            "KnowledgeBaseDocumentDeployment",
            sources=[
                s3deploy.Source.asset(
                    os.path.join(
                        os.getcwd(),
                        config["paths"]["assets_folder_name"],
                        f"{config['paths']['knowledgebase_destination_prefix']}/{config['paths']['knowledgebase_file_name']}",
                    )
                )
            ],
            destination_bucket=self.agent_assets_bucket,
            destination_key_prefix=config["paths"]["knowledgebase_destination_prefix"],
            retain_on_delete=False,
        )

        s3deploy.BucketDeployment(
            self,
            "AthenaDataDeployment",
            sources=[
                s3deploy.Source.asset(
                    os.path.join(
                        os.getcwd(),
                        config["paths"]["assets_folder_name"],
                        config["paths"]["athena_data_destination_prefix"],
                    )
                )
            ],
            destination_bucket=self.athena_bucket,
            retain_on_delete=False,
            destination_key_prefix=config["paths"]["athena_data_destination_prefix"],
        )

        s3deploy.BucketDeployment(
            self,
            "AgentAPISchema",
            sources=[
                s3deploy.Source.asset(
                    os.path.join(
                        os.getcwd(),
                        config["paths"]["assets_folder_name"],
                        "agent_api_schema",
                    )
                )
            ],
            destination_bucket=self.agent_assets_bucket,
            retain_on_delete=False,
            destination_key_prefix=config["paths"]["agent_schema_destination_prefix"],
        )
