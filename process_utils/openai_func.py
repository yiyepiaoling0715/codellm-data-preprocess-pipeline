from openai import OpenAI

token='7e1083f4-f7e8-4975-8775-5e73a7038d88'



def ask_llm(prompt,model='gpt4-o'):
    client = OpenAI(
    api_key=token,
    
    base_url=f"xxx",
    )
    chat_completion = client.chat.completions.create(
                                                    # model="GPT-4-TURBO",
                                                    model=model,
                                                    stream=False,
                                                    messages=[{
                                                        "role":"user",
                                                        "content":prompt
                                                    }])
    content=chat_completion.choices[0].message.content
    
    return content


if __name__=='__main__':
    prompt='怎么写测试用例'
    ask_llm(prompt=prompt)
