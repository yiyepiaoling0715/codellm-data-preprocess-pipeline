import torch
from vllm import LLM, SamplingParams

def trans_dtype(dtype):
    dtype_map={
        'fp16': torch.float16,
        'fp32': torch.float32,
        'bf16': torch.bfloat16,
        'bfloat16': torch.bfloat16,
        'int8': torch.int8
    }
    return dtype_map[dtype]

def load_model(model_name_or_path,tp_size,model_type,dtype,model_max_tokens):
    torch_dtype=trans_dtype(dtype)
    print(f'enter in model_type= {torch_dtype}')
    if model_type in ["codelm", "codelm_cfc"]:
        model = AutoModelForCausalLM.from_pretrained(
            model_name_or_path,
            torch_dtype=dtype,
            trust_remote_code=True,
            revision="main"
        )
    elif  model_type in ['codelm_lora']:
        # peft_model_id = "smangrul/twitter_complaints_bigscience_T0_3B_LORA_SEQ_2_SEQ_LM"
        saved_train_info_jsonpath=os.path.join(args.peft_model_id,'saved_train_info.json')
        with open(saved_train_info_jsonpath,'r') as fr:
            saved_train_info_dict=json.load(fr)
            model_name_or_path=saved_train_info_dict['pretrained_model_path']
        print(f'loading pretrained model from {model_name_or_path}')
        # model = AutoModelForSeq2SeqLM.from_pretrained(pretrained_model_path)
        model = AutoModelForCausalLM.from_pretrained(model_name_or_path)
        peft_config = PeftConfig.from_pretrained(args.peft_model_id)
        # model = PeftModel.from_pretrained(model, peft_model_id=args.peft_model_id, peft_config=peft_config)
        model = PeftModel.from_pretrained(model, model_id=args.peft_model_id, peft_config=peft_config)
        # tokenizer = AutoTokenizer.from_pretrained(config.base_model_name_or_path)
    elif model_type in ['vllm_ft','vllm_pretrain']:
        # load model
        model = LLM(model=model_name_or_path, tensor_parallel_size=torch.cuda.device_count(), 
                    max_model_len=model_max_tokens)
        # tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
        # sampling_params = SamplingParams(temperature=args.temperature, top_p=args.top_p, max_tokens=args.generation_max_tokens)
    else:
        raise ValueError("Unknown model type")
    return model

def load_tokenizer(model_name_or_path):
    tokenizer = AutoTokenizer.from_pretrained(model, trust_remote_code=True)
    return tokenizer
    
def load_sampling_params(temperature,top_p,generation_max_tokens):
    sampling_params = SamplingParams(temperature=temperature, top_p=top_p, max_tokens=generation_max_tokens)
    return sampling_params


