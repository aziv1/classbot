import sys
import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def load_model():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
    )
    model.to(DEVICE)
    model.eval()
    return tokenizer, model


def main():
    # Read JSON from stdin
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
        prompt = data.get("prompt", "")
    except Exception as e:
        print(json.dumps({"error": f"Invalid input: {e}"}))
        return

    tokenizer, model = load_model()

    inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.7,
            top_p=0.9,
        )

    text = tokenizer.decode(output_ids[0], skip_special_tokens=True)

    print(json.dumps({"output": text}))


if __name__ == "__main__":
    main()