from transformers import pipeline
from unsloth import FastLanguageModel, is_bfloat16_supported
from taxonomy import RELEVANT_CLASSES

model, tokenizer = FastLanguageModel.from_pretrained(
  model_name="unsloth/Llama-3.2-3B-Instruct-bnb-4bit",
  max_seq_length=4096,
  load_in_4bit=True,
  dtype=None,
)

FastLanguageModel.for_inference(model)

print(RELEVANT_CLASSES)

longest_output = 0

for c in RELEVANT_CLASSES:
  tokens = tokenizer(c + tokenizer.eos_token)
  longest_output = max(longest_output, len(tokens["input_ids"]))

#output = model.generate(inpt["input_ids"], attention_mask=inpt["attention_mask"], max_new_tokens=longest_output)

pipe = pipeline(task="text-generation", 
                model=model, 
                tokenizer=tokenizer, 
                max_new_tokens=15, 
                temperature=0.1)

result = pipe(prompt)

print(result)


