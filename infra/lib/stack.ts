import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as apigatewayv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as apigatewayv2_integrations from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import { Construct } from 'constructs';

export class ProcessingFileISOPipingStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // S3 Bucket for storing results
    const resultsBucket = new s3.Bucket(this, 'ResultsBucket', {
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
          allowedOrigins: ['*'],
          allowedHeaders: ['*'],
        },
      ],
    });

    // Lambda Layer for dependencies (boto3, etc.)
    const dependenciesLayer = new lambda.LayerVersion(this, 'DependenciesLayer', {
      code: lambda.Code.fromAsset('../backend/layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'Dependencies layer for processing handler',
    });

    // Lambda function for processing files
    const processHandler = new lambda.Function(this, 'ProcessHandler', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'process_handler.handler',
      code: lambda.Code.fromAsset('../backend/src'),
      timeout: cdk.Duration.minutes(15),
      memorySize: 2048,
      environment: {
        RESULTS_BUCKET: resultsBucket.bucketName,
      },
      layers: [dependenciesLayer],
    });

    // Grant S3 permissions
    resultsBucket.grantReadWrite(processHandler);

    // Grant Textract permissions
    processHandler.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          'textract:DetectDocumentText',
          'textract:AnalyzeDocument',
          'textract:StartDocumentTextDetection',
          'textract:GetDocumentTextDetection',
        ],
        resources: ['*'],
      })
    );

    // Lambda functions for WebSocket connection management
    const connectHandler = new lambda.Function(this, 'ConnectHandler', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
def handler(event, context):
    return {
        'statusCode': 200,
        'body': 'Connected'
    }
`),
      timeout: cdk.Duration.seconds(30),
    });

    const disconnectHandler = new lambda.Function(this, 'DisconnectHandler', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
def handler(event, context):
    return {
        'statusCode': 200,
        'body': 'Disconnected'
    }
`),
      timeout: cdk.Duration.seconds(30),
    });

    const defaultHandler = new lambda.Function(this, 'DefaultHandler', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.handler',
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
    const webSocketApi = new apigatewayv2.WebSocketApi(this, 'WebSocketApi', {
      apiName: 'ProcessingFileWebSocket',
      description: 'WebSocket API for real-time file processing updates',
      connectRouteOptions: {
        integration: new apigatewayv2_integrations.WebSocketLambdaIntegration(
          'ConnectIntegration',
          connectHandler
        ),
      },
      disconnectRouteOptions: {
        integration: new apigatewayv2_integrations.WebSocketLambdaIntegration(
          'DisconnectIntegration',
          disconnectHandler
        ),
      },
      defaultRouteOptions: {
        integration: new apigatewayv2_integrations.WebSocketLambdaIntegration(
          'DefaultIntegration',
          defaultHandler
        ),
      },
    });

    // Add start_scan route
    webSocketApi.addRoute('start_scan', {
      integration: new apigatewayv2_integrations.WebSocketLambdaIntegration(
        'StartScanIntegration',
        processHandler
      ),
    });

    // WebSocket Stage
    const webSocketStage = new apigatewayv2.WebSocketStage(this, 'WebSocketStage', {
      webSocketApi,
      stageName: 'prod',
      autoDeploy: true,
    });

    // Grant processHandler permission to manage WebSocket connections
    const apiGatewayManagementPolicy = new iam.PolicyStatement({
      actions: ['execute-api:ManageConnections'],
      resources: [
        `arn:aws:execute-api:${this.region}:${this.account}:${webSocketApi.apiId}/${webSocketStage.stageName}/*`,
      ],
    });
    processHandler.addToRolePolicy(apiGatewayManagementPolicy);

    // Add WebSocket URL to Lambda environment
    processHandler.addEnvironment('WEBSOCKET_API_ENDPOINT', webSocketStage.url);

    // Outputs
    new cdk.CfnOutput(this, 'WebSocketURL', {
      value: webSocketStage.url,
      description: 'WebSocket API URL',
      exportName: 'WebSocketURL',
    });

    new cdk.CfnOutput(this, 'ResultsBucketName', {
      value: resultsBucket.bucketName,
      description: 'S3 Bucket for results',
      exportName: 'ResultsBucketName',
    });

    new cdk.CfnOutput(this, 'WebSocketApiId', {
      value: webSocketApi.apiId,
      description: 'WebSocket API ID',
      exportName: 'WebSocketApiId',
    });
  }
}
