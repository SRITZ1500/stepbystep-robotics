#!/usr/bin/env python3
"""
Bedrock Client Module
Handles AWS Bedrock async invocation and polling for Luma Ray2 video generation
"""

import json
import time
from typing import Dict, List, Optional
from datetime import datetime

try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
except ImportError:
    print("ERROR: boto3 not installed. Install with: pip install boto3")
    exit(1)


class BedrockClient:
    """Client for AWS Bedrock Runtime async invocation"""
    
    def __init__(self, region: str = "us-west-2", profile: Optional[str] = None):
        """
        Initialize Bedrock client
        
        Args:
            region: AWS region (default: us-west-2)
            profile: AWS profile name (optional)
        """
        self.region = region
        self.profile = profile
        
        # Create boto3 session
        if profile:
            session = boto3.Session(profile_name=profile, region_name=region)
        else:
            session = boto3.Session(region_name=region)
        
        # Create Bedrock Runtime client
        self.client = session.client('bedrock-runtime')
        self.s3_client = session.client('s3')
        
        print(f"✓ Bedrock client initialized (region: {region})")
    
    def submit_shot(
        self,
        shot_id: int,
        prompt: str,
        duration: str,
        resolution: str,
        bucket: str,
        prefix: str,
        reference_image_b64: Optional[str] = None
    ) -> Dict:
        """
        Submit a shot for async video generation
        
        Args:
            shot_id: Shot ID
            prompt: Text prompt for video generation
            duration: Duration string ("5s" or "9s")
            resolution: "previz" (540p) or "full" (720p)
            bucket: S3 bucket name for output
            prefix: S3 prefix for output (e.g., "stepbystep/jesse/darker/20240225_120000")
            reference_image_b64: Optional base64-encoded reference image
            
        Returns:
            Dict with invocation_arn, s3_output_uri, prompt, duration
            
        Raises:
            ClientError: If Bedrock API call fails
        """
        # Build model input
        model_input = {
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": "9:16"
        }
        
        # Set resolution
        if resolution == "previz":
            model_input["resolution"] = "540p"
        else:
            model_input["resolution"] = "720p"
        
        # Add reference image if provided (image-to-video mode)
        if reference_image_b64:
            model_input["image"] = reference_image_b64
        
        # Build S3 output configuration
        s3_output_uri = f"s3://{bucket}/{prefix}/shot_{shot_id:02d}/"
        output_config = {
            "s3OutputDataConfig": {
                "s3Uri": s3_output_uri
            }
        }
        
        try:
            # Call StartAsyncInvoke
            response = self.client.start_async_invoke(
                modelId="luma.ray-v2:0",
                modelInput=model_input,
                outputDataConfig=output_config
            )
            
            invocation_arn = response['invocationArn']
            
            print(f"  ✓ Shot {shot_id} submitted (ARN: {invocation_arn[-12:]}...)")
            
            return {
                "shot_id": shot_id,
                "invocation_arn": invocation_arn,
                "s3_output_uri": s3_output_uri,
                "prompt": prompt,
                "duration": duration
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            print(f"  ✗ Shot {shot_id} failed: {error_code} - {error_msg}")
            raise
    
    def get_invocation_status(self, invocation_arn: str) -> Dict:
        """
        Get status of an async invocation
        
        Args:
            invocation_arn: Invocation ARN from submit_shot
            
        Returns:
            Dict with status, output_uri (if completed), error (if failed)
        """
        try:
            response = self.client.get_async_invoke(
                invocationArn=invocation_arn
            )
            
            status = response['status']
            result = {
                "status": status,
                "invocation_arn": invocation_arn
            }
            
            # Add output URI if completed
            if status == "Completed" and 'outputDataConfig' in response:
                result["output_uri"] = response['outputDataConfig']['s3OutputDataConfig']['s3Uri']
            
            # Add error if failed
            if status == "Failed" and 'failureMessage' in response:
                result["error"] = response['failureMessage']
            
            return result
            
        except ClientError as e:
            return {
                "status": "Error",
                "invocation_arn": invocation_arn,
                "error": str(e)
            }
    
    def poll_jobs(
        self,
        jobs: List[Dict],
        poll_interval: int = 10,
        max_retries: int = 5
    ) -> List[Dict]:
        """
        Poll jobs until all complete or fail
        
        Args:
            jobs: List of job dicts from submit_shot
            poll_interval: Seconds between polls (default: 10)
            max_retries: Max retries on throttling (default: 5)
            
        Returns:
            List of completed job results
        """
        print(f"\n{'='*60}")
        print(f"POLLING {len(jobs)} JOBS")
        print(f"{'='*60}\n")
        
        pending_jobs = {job['invocation_arn']: job for job in jobs}
        completed_jobs = []
        retry_count = 0
        backoff_delay = 2  # Start with 2 seconds
        
        while pending_jobs:
            time.sleep(poll_interval)
            
            print(f"Checking status... ({len(pending_jobs)} pending)")
            
            for arn in list(pending_jobs.keys()):
                job = pending_jobs[arn]
                
                try:
                    status_result = self.get_invocation_status(arn)
                    status = status_result['status']
                    
                    if status == "Completed":
                        print(f"  ✓ Shot {job['shot_id']} completed")
                        job['status'] = "Completed"
                        job['output_uri'] = status_result.get('output_uri')
                        completed_jobs.append(job)
                        del pending_jobs[arn]
                        retry_count = 0  # Reset retry count on success
                        
                    elif status == "Failed":
                        print(f"  ✗ Shot {job['shot_id']} failed: {status_result.get('error', 'Unknown error')}")
                        job['status'] = "Failed"
                        job['error'] = status_result.get('error')
                        completed_jobs.append(job)
                        del pending_jobs[arn]
                        retry_count = 0
                        
                    elif status == "InProgress":
                        print(f"  ⋯ Shot {job['shot_id']} in progress...")
                        
                    else:
                        print(f"  ? Shot {job['shot_id']} status: {status}")
                
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    
                    if error_code == "ThrottlingException":
                        print(f"  ⚠ Throttled, backing off {backoff_delay}s...")
                        time.sleep(backoff_delay)
                        retry_count += 1
                        
                        if retry_count >= max_retries:
                            print(f"  ✗ Max retries reached, marking shot {job['shot_id']} as failed")
                            job['status'] = "Failed"
                            job['error'] = "Max throttling retries exceeded"
                            completed_jobs.append(job)
                            del pending_jobs[arn]
                            retry_count = 0
                        else:
                            # Exponential backoff: 2s, 4s, 8s, 16s
                            backoff_delay = min(backoff_delay * 2, 16)
                    else:
                        print(f"  ✗ Shot {job['shot_id']} error: {error_code}")
                        job['status'] = "Failed"
                        job['error'] = str(e)
                        completed_jobs.append(job)
                        del pending_jobs[arn]
            
            if pending_jobs:
                print(f"\nWaiting {poll_interval}s before next poll...\n")
        
        print(f"\n{'='*60}")
        print(f"POLLING COMPLETE")
        print(f"{'='*60}\n")
        
        # Summary
        completed_count = sum(1 for j in completed_jobs if j['status'] == 'Completed')
        failed_count = sum(1 for j in completed_jobs if j['status'] == 'Failed')
        
        print(f"Completed: {completed_count}")
        print(f"Failed:    {failed_count}")
        print()
        
        return completed_jobs


def create_bedrock_client(region: str = "us-west-2", profile: Optional[str] = None) -> BedrockClient:
    """
    Create and return a Bedrock client
    
    Args:
        region: AWS region (default: us-west-2)
        profile: AWS profile name (optional)
        
    Returns:
        BedrockClient instance
    """
    return BedrockClient(region=region, profile=profile)


if __name__ == "__main__":
    # Basic test
    print("Bedrock Client Module")
    print("Testing client initialization...")
    
    try:
        client = create_bedrock_client()
        print("✓ Client created successfully")
    except Exception as e:
        print(f"✗ Client creation failed: {e}")
