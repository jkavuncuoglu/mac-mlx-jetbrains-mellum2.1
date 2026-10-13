import os
from huggingface_hub import login
from mlx_lm import load, generate

# 1. (Optional) Authenticate with Hugging Face if you haven't globally logged in
# You can uncomment the lines below and insert your token if the model requires it.
# HF_TOKEN = "your_hugging_face_token_here"
# login(token=HF_TOKEN)

def main():
    # 2. Define the model path
    # We use a 6-bit quantized version which easily fits in your 32GB RAM while keeping high quality
    model_id = "mlx-community/Mellum2.1-12B-A2.5B-Thinking-6bit"
    
    print(f"🚀 Loading {model_id} onto M4 GPU cores...")
    
    # load() automatically fetches from Hugging Face and caches it locally
    model, tokenizer = load(model_id)
    
    print("\n✨ Model loaded successfully!")
    
    # 3. Formulate your prompt
    prompt = "Explain quantum computing in one short paragraph."
    
    print(f"\n💬 Prompt: '{prompt}'")
    print("🤖 Mellum 2.1 is thinking...\n")
    
    # 4. Generate the response utilizing local M4 hardware acceleration
    response = generate(
        model, 
        tokenizer, 
        prompt=prompt, 
        max_tokens=400,     # Maximum length of the output
        verbose=True        # Prints tokens sequentially as they generate
    )

if __name__ == "__main__":
    main()
