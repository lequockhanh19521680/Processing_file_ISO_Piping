import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as iam from "aws-cdk-lib/aws-iam";
import * as apigatewayv2 from "aws-cdk-lib/aws-apigatewayv2";
import * as apigatewayv2_integrations from "aws-cdk-lib/aws-apigatewayv2-integrations";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as lambdaEventSources from "aws-cdk-lib/aws-lambda-event-sources";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import * as ssm from "aws-cdk-lib/aws-ssm";
import * as amplify from "aws-cdk-lib/aws-amplify";
import { Construct } from "constructs";

export class ProcessingFileISOPipingStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ============================================================
    // Secrets Management - Store sensitive credentials securely
    // ============================================================

    // AWS Secrets Manager for Google Drive API credentials
    // These should be manually set after deployment using AWS CLI or Console:
    // aws secretsmanager put-secret-value --secret-id processing-file-iso/google-drive-credentials \
    //   --secret-string '{"access_token":"YOUR_TOKEN","refresh_token":"YOUR_REFRESH","client_id":"YOUR_CLIENT_ID","client_secret":"YOUR_CLIENT_SECRET"}'
    const googleDriveSecret = new secretsmanager.Secret(
      this,
      "GoogleDriveAPICredentials",
      {
        secretName: "processing-file-iso/google-drive-credentials",
        description: "Google Drive API OAuth credentials for file processing",
        generateSecretString: {
          secretStringTemplate: JSON.stringify({
            access_token: "PLACEHOLDER_SET_AFTER_DEPLOYMENT",
            refresh_token: "PLACEHOLDER_SET_AFTER_DEPLOYMENT",
            client_id: "PLACEHOLDER_SET_AFTER_DEPLOYMENT",
            client_secret: "PLACEHOLDER_SET_AFTER_DEPLOYMENT",
          }),
          generateStringKey: "placeholder",
        },
      },
    );

    // S3 Bucket for storing results
    const resultsBucket = new s3.Bucket(this, "ResultsBucket", {
      versioned: false,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      cors: [
        {
          allowedMethods: [
            s3.HttpMethods.GET,
            s3.HttpMethods.PUT,
            s3.HttpMethods.POST,
          ],
          allowedOrigins: ["*"],
          allowedHeaders: ["*"],
        },
      ],
    });

    // DynamoDB Table for storing processing results
    const processResultsTable = new dynamodb.Table(
      this,
      "ProcessResultsTable",
      {
        partitionKey: {
          name: "session_id",
          type: dynamodb.AttributeType.STRING,
        },
        sortKey: { name: "file_name", type: dynamodb.AttributeType.STRING },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.DESTROY,
      },
    );

    // SQS Queue for file processing
    const processingQueue = new sqs.Queue(this, "ProcessingQueue", {
      visibilityTimeout: cdk.Duration.seconds(180), // 6x Lambda timeout for retries
      retentionPeriod: cdk.Duration.days(1),
    });

    // Lambda Layer for dependencies (boto3, etc.)
    const dependenciesLayer = new lambda.LayerVersion(
      this,
      "DependenciesLayer",
      {
        code: lambda.Code.fromAsset("../backend/layer"),
        compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
        description: "Dependencies layer for processing handler",
      },
    );

    // Lambda function for dispatching files to SQS (formerly ProcessHandler)
    const scanDispatcher = new lambda.Function(this, "ScanDispatcher", {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "process_handler.handler",
      code: lambda.Code.fromAsset("../backend/src"),
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      environment: {
        QUEUE_URL: processingQueue.queueUrl,
        TABLE_NAME: processResultsTable.tableName,
        GOOGLE_DRIVE_SECRET_ARN: googleDriveSecret.secretArn,
      },
      layers: [dependenciesLayer],
    });

    // Grant permissions to ScanDispatcher
    processingQueue.grantSendMessages(scanDispatcher);
    processResultsTable.grantWriteData(scanDispatcher);
    googleDriveSecret.grantRead(scanDispatcher);

    // Lambda function for processing files from SQS (new worker)
    const scanWorker = new lambda.Function(this, "ScanWorker", {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "worker_handler.handler",
      code: lambda.Code.fromAsset("../backend/src"),
      timeout: cdk.Duration.seconds(30),
      memorySize: 1024,
      environment: {
        TABLE_NAME: processResultsTable.tableName,
        RESULTS_BUCKET: resultsBucket.bucketName,
        GOOGLE_DRIVE_SECRET_ARN: googleDriveSecret.secretArn,
      },
      layers: [dependenciesLayer],
    });

    // Grant permissions to ScanWorker
    processResultsTable.grantReadWriteData(scanWorker);
    resultsBucket.grantReadWrite(scanWorker);
    googleDriveSecret.grantRead(scanWorker);

    // Add SQS as event source for ScanWorker
    scanWorker.addEventSource(
      new lambdaEventSources.SqsEventSource(processingQueue, {
        batchSize: 10,
      }),
    );

    // Lambda functions for WebSocket connection management
    const connectHandler = new lambda.Function(this, "ConnectHandler", {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "index.handler",
      code: lambda.Code.fromInline(`
def handler(event, context):
    return {
        'statusCode': 200,
        'body': 'Connected'
    }
`),
      timeout: cdk.Duration.seconds(30),
    });

    const disconnectHandler = new lambda.Function(this, "DisconnectHandler", {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "index.handler",
      code: lambda.Code.fromInline(`
def handler(event, context):
    return {
        'statusCode': 200,
        'body': 'Disconnected'
    }
`),
      timeout: cdk.Duration.seconds(30),
    });

    const defaultHandler = new lambda.Function(this, "DefaultHandler", {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "index.handler",
      code: lambda.Code.fromInline(`
def handler(event, context):
    return {
        'statusCode': 200,
        'body': 'Default route'
    }
`),
      timeout: cdk.Duration.seconds(30),
    });

    // WebSocket API
    const webSocketApi = new apigatewayv2.WebSocketApi(this, "WebSocketApi", {
      apiName: "ProcessingFileWebSocket",
      description: "WebSocket API for real-time file processing updates",
      connectRouteOptions: {
        integration: new apigatewayv2_integrations.WebSocketLambdaIntegration(
          "ConnectIntegration",
          connectHandler,
        ),
      },
      disconnectRouteOptions: {
        integration: new apigatewayv2_integrations.WebSocketLambdaIntegration(
          "DisconnectIntegration",
          disconnectHandler,
        ),
      },
      defaultRouteOptions: {
        integration: new apigatewayv2_integrations.WebSocketLambdaIntegration(
          "DefaultIntegration",
          defaultHandler,
        ),
      },
    });

    // Add start_scan route
    webSocketApi.addRoute("start_scan", {
      integration: new apigatewayv2_integrations.WebSocketLambdaIntegration(
        "StartScanIntegration",
        scanDispatcher,
      ),
    });

    // WebSocket Stage
    const webSocketStage = new apigatewayv2.WebSocketStage(
      this,
      "WebSocketStage",
      {
        webSocketApi,
        stageName: "prod",
        autoDeploy: true,
      },
    );

    // Grant Dispatcher permission to manage WebSocket connections
    const apiGatewayManagementPolicyDispatcher = new iam.PolicyStatement({
      actions: ["execute-api:ManageConnections"],
      resources: [
        `arn:aws:execute-api:${this.region}:${this.account}:${webSocketApi.apiId}/${webSocketStage.stageName}/*`,
      ],
    });
    scanDispatcher.addToRolePolicy(apiGatewayManagementPolicyDispatcher);

    // Grant Worker permission to manage WebSocket connections
    const apiGatewayManagementPolicyWorker = new iam.PolicyStatement({
      actions: ["execute-api:ManageConnections"],
      resources: [
        `arn:aws:execute-api:${this.region}:${this.account}:${webSocketApi.apiId}/${webSocketStage.stageName}/*`,
      ],
    });
    scanWorker.addToRolePolicy(apiGatewayManagementPolicyWorker);

    // Add WebSocket URL to Lambda environments
    scanDispatcher.addEnvironment("WEBSOCKET_API_ENDPOINT", webSocketStage.url);
    scanWorker.addEnvironment("WEBSOCKET_API_ENDPOINT", webSocketStage.url);

    // ============================================================
    // Parameter Store - Store WebSocket URL for frontend access
    // ============================================================

    // Store WebSocket URL in Parameter Store for easy frontend access
    const websocketUrlParameter = new ssm.StringParameter(
      this,
      "WebSocketUrlParameter",
      {
        parameterName: "/processing-file-iso/websocket-url",
        stringValue: webSocketStage.url,
        description: "WebSocket API URL for frontend configuration",
        tier: ssm.ParameterTier.STANDARD,
      },
    );

    // ============================================================
    // AWS Amplify - Frontend Hosting Configuration
    // ============================================================

    // Create Amplify App for hosting the React frontend
    // Note: You need to connect your GitHub repository manually in the AWS Console
    // or provide a GitHub token for automatic deployment
    const amplifyApp = new amplify.CfnApp(this, "AmplifyApp", {
      name: "ProcessingFileISOPipingFrontend",
      description: "Real-time file processing dashboard",
      repository:
        "https://github.com/lequockhanh19521680/Processing_file_ISO_Piping",
      // Note: For automatic deployments, add accessToken property with GitHub personal access token
      // accessToken: 'your-github-token', // Store this in Secrets Manager and reference it
      iamServiceRole: this.createAmplifyServiceRole().roleArn,
      buildSpec: `version: 1
frontend:
  phases:
    preBuild:
      commands:
        - cd frontend
        - npm ci
    build:
      commands:
        - echo "VITE_WEBSOCKET_URL=${webSocketStage.url}" > .env.production
        - npm run build
  artifacts:
    baseDirectory: frontend/dist
    files:
      - '**/*'
  cache:
    paths:
      - frontend/node_modules/**/*
`,
      environmentVariables: [
        {
          name: "VITE_WEBSOCKET_URL",
          value: webSocketStage.url,
        },
      ],
    });

    // Create Amplify branch for main/master branch
    const amplifyBranch = new amplify.CfnBranch(this, "AmplifyBranch", {
      appId: amplifyApp.attrAppId,
      branchName: "main",
      enableAutoBuild: true,
      environmentVariables: [
        {
          name: "VITE_WEBSOCKET_URL",
          value: webSocketStage.url,
        },
      ],
    });

    // Outputs
    new cdk.CfnOutput(this, "WebSocketURL", {
      value: webSocketStage.url,
      description: "WebSocket API URL",
      exportName: "WebSocketURL",
    });

    new cdk.CfnOutput(this, "ResultsBucketName", {
      value: resultsBucket.bucketName,
      description: "S3 Bucket for results",
      exportName: "ResultsBucketName",
    });

    new cdk.CfnOutput(this, "GoogleDriveSecretArn", {
      value: googleDriveSecret.secretArn,
      description: "ARN of Google Drive API credentials secret",
      exportName: "GoogleDriveSecretArn",
    });

    new cdk.CfnOutput(this, "WebSocketUrlParameterName", {
      value: websocketUrlParameter.parameterName,
      description: "SSM Parameter name for WebSocket URL",
      exportName: "WebSocketUrlParameterName",
    });

    new cdk.CfnOutput(this, "AmplifyAppId", {
      value: amplifyApp.attrAppId,
      description: "Amplify App ID",
      exportName: "AmplifyAppId",
    });

    new cdk.CfnOutput(this, "AmplifyAppUrl", {
      value: `https://main.${amplifyApp.attrAppId}.amplifyapp.com`,
      description: "Amplify App URL",
      exportName: "AmplifyAppUrl",
    });

    new cdk.CfnOutput(this, "WebSocketApiId", {
      value: webSocketApi.apiId,
      description: "WebSocket API ID",
      exportName: "WebSocketApiId",
    });

    new cdk.CfnOutput(this, "ProcessingQueueUrl", {
      value: processingQueue.queueUrl,
      description: "SQS Queue URL for file processing",
      exportName: "ProcessingQueueUrl",
    });

    new cdk.CfnOutput(this, "ProcessResultsTableName", {
      value: processResultsTable.tableName,
      description: "DynamoDB Table for processing results",
      exportName: "ProcessResultsTableName",
    });
  }

  /**
   * Create IAM service role for AWS Amplify
   * This role allows Amplify to access necessary AWS services
   */
  private createAmplifyServiceRole(): iam.Role {
    const role = new iam.Role(this, "AmplifyServiceRole", {
      assumedBy: new iam.ServicePrincipal("amplify.amazonaws.com"),
      description: "Service role for AWS Amplify",
    });

    // Add permissions for Amplify to access necessary resources
    role.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName("AdministratorAccess-Amplify"),
    );

    return role;
  }
}
