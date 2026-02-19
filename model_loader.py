import os
from llama_cpp import Llama
from dotenv import load_dotenv

load_dotenv()

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["LLAMA_CPP_FORCE_CPU"] = "1"

print("🚀 Loading LLaMA model...")

llm = Llama(
    model_path=os.getenv("MODEL_PATH"),
    n_ctx=1024,
    n_threads=8,
    n_batch=64,
    verbose=True
)

print("✅ Model loaded")
