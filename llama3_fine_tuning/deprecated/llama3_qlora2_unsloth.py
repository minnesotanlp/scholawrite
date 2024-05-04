for attemp in range(2):
    try:
        import os
        import pandas as pd
        import torch
        from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
        from torch.distributed.fsdp import CPUOffload
        import torch.distributed as dist
        from torch import cuda, bfloat16
        from transformers import AutoModelForCausalLM, TrainingArguments, AutoTokenizer, BitsAndBytesConfig, pipeline
        from peft import LoraConfig, get_peft_model
        import accelerate # not used in code but reuqired for device_map='auto'
        from datasets import load_dataset
        from trl import SFTTrainer
        import json
        import random
        from unsloth import FastLanguageModel
    except ImportError:
        os.system("pip install --no-cache-dir -r requirements.txt")
        continue


HF_TOKEN = os.getenv("HF_TOKEN")
with open("labels_for_computation.json", 'r') as file:
    labels = json.load(file)


def formatting_prompts_func(examples):
    instruct_tune_template="""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a writing assistant that can generate ideas, implement ideas, and revise paper for scholarly writing. The paper is written in LaTeX. The context of the Paper is provided below, paired with instruction that describes a writing task. Write a response that appropriately completes the request. Do not repeat any instructions. Do not output any instructions. You are not allowed to talk about yourself.<|eot_id|>
<|start_header_id|>user<|end_header_id|>

{BEFORE_TEXT}.

{VERBALIZER}.<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>

{AFTER_TEXT}<|eot_id|>"""

    BEFORE_TEXTs    = examples["before_text"]
    INTENTIONs      = examples["writing_intention"]
    AFTER_TEXTs     = examples["after_text"]
    
    tune_ready_prompts = []

    for BEFORE_TEXT, INTENTION, AFTER_TEXT in zip(BEFORE_TEXTs, INTENTIONs, AFTER_TEXTs):
        VERBALIZER           = random.choice(labels[INTENTION]["verbalizer"])

        tune_ready_prompt = instruct_tune_template.format(
                            VERBALIZER = VERBALIZER,
                            BEFORE_TEXT = BEFORE_TEXT,
                            AFTER_TEXT = AFTER_TEXT)
        tune_ready_prompts.append(tune_ready_prompt)
    
    return {"tune" : tune_ready_prompts}


def prepare_data():
    if not os.path.exists("test.csv"):
        df = pd.read_csv('fine_tuning.csv')
        random_row = df.sample(n=28)
        random_row.to_csv('test.csv', index=False)
        df = df.drop(random_row.index)
        df.to_csv('fine_tuning.csv', index=False)

    dataset = load_dataset("csv", data_files={"train": "fine_tuning.csv",
                                                "test": "test.csv"})
    dataset = dataset.map(formatting_prompts_func, batched = True)
    
    return dataset


def print_trainable_parameters(model):
    """
    Prints the number of trainable parameters in the model.
    """
    trainable_params = 0
    all_param = 0
    for _, param in model.named_parameters():
        all_param += param.numel()
        if param.requires_grad:
            trainable_params += param.numel()
    print(
        f"trainable params: {trainable_params} || all params: {all_param} || trainable%: {100 * trainable_params / all_param}"
    )


def load_model_and_tokenizer():
    max_seq_length = 4600   # Choose any! We auto support RoPE Scaling internally!
    dtype = None            # None for auto detection. Float16 for Tesla T4, V100, Bfloat16 for Ampere+
    load_in_4bit = True     # Use 4bit quantization to reduce memory usage. Can be False.

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = "unsloth/llama-3-8b-bnb-4bit",
        max_seq_length = max_seq_length,
        dtype = dtype,
        load_in_4bit = load_in_4bit,
        token = HF_TOKEN
    )
    tokenizer.add_special_tokens({'pad_token': '<|end_of_text|>'})
    
    model = FastLanguageModel.get_peft_model(
        model,
        r = 16,                                         # Choose any number > 0 ! Suggested 8, 16, 32, 64, 128
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                      "gate_proj", "up_proj", "down_proj",],
        lora_alpha = 16,                                # From unsloth
        lora_dropout = 0,                               # Supports any, but = 0 is optimized
        bias = "none",                                  # Supports any, but = "none" is optimized
        use_rslora = False,                            # Better perfformance with similar computing cost https://huggingface.co/docs/peft/main/en/package_reference/lora#peft.LoraConfig.use_rslora
        loftq_config = None,     # Minimize error, Improve performance. huggingface.co/docs/peft/v0.8.0/en/developer_guides/quantization#loftq-initialization
        # task_type="CAUSAL_LM",                          # set this for CLM or Seq2Seq
        modules_to_save = ["lm_head", "embed_tokens"],   # if we want to use the special tokens and template from Llama 3 instruct for Lora
        use_gradient_checkpointing = "unsloth"
    )

    return model, tokenizer


def setup_trainer(model, tokenizer, dataset):
    trainer = SFTTrainer(
        model = model,
        tokenizer = tokenizer,
        train_dataset = dataset["train"],
        eval_dataset=dataset["test"],
        dataset_text_field = "tune",
        max_seq_length = 4600,
        # packing = False, # Can make training 5x faster for short sequences.
        dataset_kwargs={
            "add_special_tokens": False,  # We template with special tokens
            "append_concat_token": False,  # No need to add additional separator token
        },
        args = TrainingArguments(
            output_dir = "output",
            per_device_train_batch_size = 1,
            per_device_eval_batch_size = 1,
            gradient_accumulation_steps = 4,
            warmup_steps = 5,
            learning_rate = 2e-4,
            fp16 = not torch.cuda.is_bf16_supported(),
            bf16 = torch.cuda.is_bf16_supported(),
            logging_steps = 1,
            optim = "adamw_8bit",
            weight_decay = 0.01,
            lr_scheduler_type = "linear",
            seed = 3407,
            num_train_epochs= 5,
            evaluation_strategy = "epoch",
            gradient_checkpointing = True,
            report_to = "tensorboard"
        ),
    )

    return trainer


# def setup_fsdp():
#     rank = int(os.environ['LOCAL_RANK'])
#     os.environ['MASTER_ADDR'] = 'localhost'
#     os.environ['MASTER_PORT'] = '12345'
#     dist.init_process_group("nccl", rank=rank, world_size=2)
#     torch.cuda.set_device(rank)


def main():
    print(accelerate.Accelerator().device)
    print(accelerate.Accelerator().state)
    # setup_fsdp()

    model, tokenizer = load_model_and_tokenizer()

    dataset = prepare_data()

    trainer = setup_trainer(model, tokenizer, dataset)

    trainer_stats = trainer.train()

    print(trainer_stats)
    merged_model = model.merge_and_unload()
    merged_model.save_pretrained("4th_scholawrite_instruct_llama", safe_serialization=True)
    # # model.push_to_hub("BbRrOoKk/2st_scholawrite_instruct_llama", token = HF_TOKEN)

    # dist.destroy_process_group()


if __name__ == "__main__":
    main()