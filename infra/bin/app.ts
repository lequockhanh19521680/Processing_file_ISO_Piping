#!/usr/bin/env node
import "dotenv/config";
import * as cdk from "aws-cdk-lib";
import { ProcessingFileISOPipingStack } from "../lib/stack";

const app = new cdk.App();

// Ưu tiên lấy từ biến môi trường, hoặc hard-code luôn 'ap-southeast-1' nếu muốn chắc chắn
const env = {
  account:
    process.env.CDK_DEPLOY_ACCOUNT ||
    process.env.CDK_DEFAULT_ACCOUNT ||
    "492098925520",
  region:
    process.env.CDK_DEPLOY_REGION ||
    process.env.CDK_DEFAULT_REGION ||
    "ap-southeast-1",
};

new ProcessingFileISOPipingStack(app, "ProcessingFileISOPipingStack", { env });

console.log(
  `Preparing deploy for Account: ${env.account} | Region: ${env.region}`,
);
