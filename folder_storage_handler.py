import boto3
from botocore.client import Config
from pathlib import Path
import os
import re

class FolderStorageHandler:
    def __init__(self, config):
        # Initialize S3 client for the single bucket
        self.session = boto3.client(
            's3',
            endpoint_url=config['endpoint_url'],
            aws_access_key_id=config['access_key'],
            aws_secret_access_key=config['secret_key'],
            region_name=config['region'],
            config=Config(signature_version='s3v4')
        )
        self.bucket = config['bucket_name']
        self.endpoint_url = config['endpoint_url']
        
        # Define folder paths
        self.key_folder = "Example_folder_for_Key"
        self.m3u8_folder = "Example_folder_for_m3u8"
        self.ts_folder = "Example_folder_for_TS"

    def check_connection(self):
        """Check if we can connect to the storage bucket"""
        try:
            # Check bucket
            self.session.head_bucket(Bucket=self.bucket)
            print(f"Successfully connected to bucket: {self.bucket}!")
            
            return True
        except Exception as e:
            print(f"Failed to connect to storage: {str(e)}")
            return False

    def upload_key_file(self, local_path: str, object_key: str) -> bool:
        """Upload key file to the key folder"""
        try:
            full_key = f"{self.key_folder}/{object_key}"
            print(f"Uploading key file {local_path} to {full_key}...")
            self.session.upload_file(local_path, self.bucket, full_key)
            print(f"Successfully uploaded key file {full_key}")
            return True
        except Exception as e:
            print(f"Failed to upload key file {object_key}: {str(e)}")
            return False

    def upload_m3u8_file(self, local_path: str, object_key: str, video_name: str, key_filename: str) -> bool:
        """Upload m3u8 file to the m3u8 folder with updated URLs"""
        try:
            # First update the m3u8 file with correct URLs
            self._update_m3u8_file(local_path, video_name, key_filename)
            
            full_key = f"{self.m3u8_folder}/{object_key}"
            print(f"Uploading m3u8 file {local_path} to {full_key}...")
            self.session.upload_file(local_path, self.bucket, full_key)
            print(f"Successfully uploaded m3u8 file {full_key}")
            return True
        except Exception as e:
            print(f"Failed to upload m3u8 file {object_key}: {str(e)}")
            return False

    def _update_m3u8_file(self, local_path: str, video_name: str, key_filename: str):
        """Update the m3u8 file to use the correct URLs for key and TS files"""
        try:
            with open(local_path, 'r') as f:
                content = f.read()
            
            # Replace the key URL
            key_url = f"{self.endpoint_url}/{self.bucket}/{self.key_folder}/{key_filename}"
            content = re.sub(r'#EXT-X-KEY:METHOD=AES-128,URI="[^"]*"', f'#EXT-X-KEY:METHOD=AES-128,URI="{key_url}"', content)
            
            # Replace the TS file URL if it's a stream.m3u8 file
            if "stream.m3u8" in local_path:
                ts_url = f"{self.endpoint_url}/{self.bucket}/{self.ts_folder}/{video_name}/{video_name}.ts"
                # Find the line with the .ts file and replace it with the full URL
                content = re.sub(r'(^[^#].*\.ts$)', ts_url, content, flags=re.MULTILINE)
            
            with open(local_path, 'w') as f:
                f.write(content)
                
            print(f"Updated URLs in {local_path}")
            return True
        except Exception as e:
            print(f"Error updating m3u8 file {local_path}: {str(e)}")
            return False

    def upload_ts_file(self, local_path: str, object_key: str) -> bool:
        """Upload TS file to the TS folder"""
        try:
            full_key = f"{self.ts_folder}/{object_key}"
            print(f"Uploading TS file {local_path} to {full_key}...")
            self.session.upload_file(local_path, self.bucket, full_key)
            print(f"Successfully uploaded TS file {full_key}")
            return True
        except Exception as e:
            print(f"Failed to upload TS file {object_key}: {str(e)}")
            return False

    def upload_video_files(self, video_dir: Path, video_name: str, key_filename: str) -> bool:
        """Upload all files related to a video to their respective folders"""
        try:
            # 1. Upload key file to key folder
            key_file = video_dir / key_filename
            if key_file.exists():
                if not self.upload_key_file(str(key_file), key_filename):
                    return False
            else:
                print(f"Warning: Key file {key_file} does not exist, skipping upload")
                return False

            # 2. Upload m3u8 files to m3u8 folder
            m3u8_files = [
                (video_dir / "stream.m3u8", f"{video_name}/stream.m3u8"),
                (video_dir / "iframe.m3u8", f"{video_name}/iframe.m3u8")
            ]

            for local_file, object_key in m3u8_files:
                if local_file.exists():
                    if not self.upload_m3u8_file(str(local_file), object_key, video_name, key_filename):
                        return False
                else:
                    print(f"Warning: M3U8 file {local_file} does not exist, skipping upload")

            # 3. Upload TS file to TS folder
            # First check for the video_name.ts file
            ts_file = video_dir / f"{video_name}.ts"
            
            # If not found, check for stream0.ts (FFmpeg default output)
            if not ts_file.exists():
                ts_file = video_dir / "stream0.ts"
                if not ts_file.exists():
                    # If still not found, look for any .ts files
                    ts_files = list(video_dir.glob("*.ts"))
                    if ts_files:
                        ts_file = ts_files[0]
                    else:
                        print(f"Error: No .ts files found for {video_name}")
                        return False
            
            # Upload the TS file
            object_key = f"{video_name}/{video_name}.ts"
            if not self.upload_ts_file(str(ts_file), object_key):
                return False

            print(f"Successfully uploaded all files for {video_name}")
            return True

        except Exception as e:
            print(f"Error uploading video files for {video_name}: {str(e)}")
            return False

    def generate_presigned_url(self, object_key: str, folder: str = None, expiration: int = 3600) -> str:
        """Generate a presigned URL for an object from the specified folder"""
        try:
            # If folder is specified, prepend it to the object key
            full_key = object_key
            if folder:
                full_key = f"{folder}/{object_key}"
                
            url = self.session.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': full_key
                },
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            print(f"Error generating presigned URL: {str(e)}")
            return None 