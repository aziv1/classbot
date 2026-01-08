import sys
import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from config import (
    SYSTEM_PROMPT_SUMMARIZE,
    SYSTEM_PROMPT_FINISH,
    MAX_LENGTH,
    MAX_NEW_TOKENS,
    LOCAL_MODEL_PATH
)

# Load model once
tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL_PATH, local_files_only=True)
model = AutoModelForCausalLM.from_pretrained(
    LOCAL_MODEL_PATH,
    torch_dtype=torch.float16,
    device_map="auto",
    local_files_only=True
)

def run_model(system_prompt, user_text):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text}
    ]
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            max_length=MAX_LENGTH,
            temperature=0.7,
            do_sample=True
        )
    decoded = tokenizer.decode(output[0], skip_special_tokens=True)
    # Extract assistant output
    if "assistant" in decoded:
        return decoded.split("assistant")[-1].strip()
    return decoded

for line in sys.stdin:
    try:
        packet = json.loads(line)
    except:
        continue
    command = packet.get("command")
    override_prompt = packet.get("system_prompt")
    if command == "summarize":
        system_prompt = override_prompt or SYSTEM_PROMPT_SUMMARIZE
        text = packet.get("text", "")
        summary = run_model(system_prompt, text)
        response = {
            "command": "summary",
            "summary": summary
        }
    elif command == "finish":
        system_prompt = override_prompt or SYSTEM_PROMPT_FINISH
        summaries = packet.get("summaries", [])
        merged_text = "\n".join(summaries)

        final_summary = run_model(system_prompt, merged_text)

        response = {
            "command": "final_summary",
            "summary": final_summary
        }
    else:
        response = {"error": "unknown_command"}
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()
