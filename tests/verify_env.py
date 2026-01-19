import sys
import torch
import cshogi
import transformers
import os

def check_env():
    print(f"Python version: {sys.version}")
    
    print("-" * 20)
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"Device: {torch.cuda.get_device_name(0)}")
    
    print("-" * 20)
    # cshogi often doesn't expose __version__ at top level in some builds, so we just check import
    print(f"cshogi imported successfully: {cshogi}")
    board = cshogi.Board()
    print("cshogi Board test passed")
    
    print("-" * 20)
    print(f"transformers version: {transformers.__version__}")

    print("-" * 20)
    try:
        import openai
        print(f"openai version: {openai.__version__}")
    except ImportError:
        print("openai is not installed")

if __name__ == "__main__":
    check_env()
