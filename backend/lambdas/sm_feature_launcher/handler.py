import os, json, boto3, uuid

sm = boto3.client("sagemaker")

ROLE_ARN = os.environ["SAGEMAKER_EXEC_ROLE_ARN"]
PROCESS_IMAGE = os.environ["PROCESS_IMAGE_URI"]
SCRIPT_S3_URI = os.environ["FEATURE_SCRIPT_S3"]
OUT_PREFIX = os.environ["FEATURE_OUT_PREFIX"]

def lambda_handler(event, context):
    """
        event expects:
          {
            "bootstrap_key": "s3://.../bootstrap-static_.json",
            "fixtures_key":  "s3://.../fixtures_.json",
            "H": 6
          }
        returns: {"features_s3": "s3://.../refined/features/.../features.parquet"}
    """
    h = int(event.get("H", 6))
    job = f"fpl-feature-{uuid.uuid4().hex[:8]}"
    
    proc_inputs = [
        {
          "InputName": "script",
          "S3Input": {
            "S3Uri": SCRIPT_S3_URI,
            "LocalPath": "/opt/ml/processing/input/code",
            "S3DataType": "S3Prefix",
            "S3InputMode": "File"
          }
        }
    ]

    out_s3 = f"{OUT_PREFIX}{job}/"
    env = {
      "BOOTSTRAP_KEY": event["bootstrap_key"],
      "FIXTURES_KEY": event["fixtures_key"],
      "OUT_PREFIX": out_s3,
      "H": str(h)
    }

    sm.create_processing_job(
        ProcessingJobName=job,
        RoleArn=ROLE_ARN,
        ProcessingInputs=proc_inputs,
        ProcessingOutputConfig={
          "Outputs": [{
            "OutputName":"features",
            "S3Output":{"S3Uri": out_s3, "LocalPath": "/opt/ml/processing/output"}
          }]
        },
        AppSpecification={
          "ImageUri": PROCESS_IMAGE,
          "ContainerArguments": ["python","/opt/ml/processing/input/code/feature_and_join.py"]
        },
        Environment=env,
        ProcessingResources={
          "ClusterConfig":{"InstanceCount":1,"InstanceType":"ml.m5.large","VolumeSizeInGB":30}
        }
    )
    # Let Step Functions poll via DescribeProcessingJob; here just return paths
    return {"features_s3": f"{out_s3}features.parquet"}