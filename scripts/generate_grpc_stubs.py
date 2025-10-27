#!/usr/bin/env python3
"""
Script to generate gRPC Python stubs from .proto files
"""

import os
import subprocess
import sys
from pathlib import Path

def generate_grpc_stubs():
    """Generate gRPC Python stubs from proto files"""
    
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    protos_dir = project_root / "protos"
    generated_dir = project_root / "generated"
    
    # Create generated directory if it doesn't exist
    generated_dir.mkdir(exist_ok=True)
    
    # Create __init__.py file
    (generated_dir / "__init__.py").touch()
    
    # Find all .proto files
    proto_files = list(protos_dir.glob("*.proto"))
    
    if not proto_files:
        print("No .proto files found in protos directory")
        return
    
    print(f"Found {len(proto_files)} proto files:")
    for proto_file in proto_files:
        print(f"  - {proto_file.name}")
    
    # Generate Python stubs for each proto file
    for proto_file in proto_files:
        print(f"\nGenerating stubs for {proto_file.name}...")
        
        try:
            # Generate Python gRPC stubs
            cmd = [
                "python", "-m", "grpc_tools.protoc",
                f"--proto_path={protos_dir}",
                f"--python_out={generated_dir}",
                f"--grpc_python_out={generated_dir}",
                str(proto_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✓ Successfully generated stubs for {proto_file.name}")
            else:
                print(f"✗ Failed to generate stubs for {proto_file.name}")
                print(f"Error: {result.stderr}")
                
        except FileNotFoundError:
            print("✗ grpc_tools not found. Please install it with: pip install grpcio-tools")
            return
        except Exception as e:
            print(f"✗ Error generating stubs for {proto_file.name}: {e}")
    
    print(f"\nGenerated files are in: {generated_dir}")
    print("\nTo use the generated stubs, import them like:")
    print("from generated import user_service_pb2")
    print("from generated import user_service_pb2_grpc")

if __name__ == "__main__":
    generate_grpc_stubs()



