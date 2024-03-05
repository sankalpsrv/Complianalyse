from decouple import config

import json
from exampleprompts import examples_legaldocml, examples_legalruleml
from langchain_core.output_parsers import StrOutputParser
output_parser = StrOutputParser()

from langchain.schema import HumanMessage
from langchain_community.llms.azureml_endpoint import AzureMLEndpointApiType
from langchain_community.chat_models.azureml_endpoint import AzureMLChatOnlineEndpoint
from langchain_community.chat_models.azureml_endpoint import LlamaChatContentFormatter


from langchain.prompts.few_shot import FewShotChatMessagePromptTemplate
from langchain.prompts.prompt import PromptTemplate
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate


from langchain_community.llms.huggingface_pipeline import HuggingFacePipeline
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from langchain_openai import ChatOpenAI, OpenAI
from langchain_core.example_selectors.base import BaseExampleSelector


import torch, gc
hf_global = HuggingFacePipeline()
llm_global = "OpenAI"
openai_key = config('OPENAI_API_KEY')
openai_chain = ChatOpenAI(openai_api_key=openai_key)

global_metamodel = ' '
global_metamodel_number = ''

class CustomExampleSelector(BaseExampleSelector):
    def __init__(self):
        self.examples_legalruleml = examples_legalruleml
        self.examples_legaldocml = examples_legaldocml

    def add_example(self, example):
        self.examples.append(example)

    def select_examples(self, input_variables):
        # This assumes knowledge that part of the input will be a 'text' key
        new_word = input_variables["format_chosen"]

        if new_word == "legalruleml":
            return self.examples_legalruleml
        else:
            return self.examples_legaldocml



# https://discuss.pytorch.org/t/how-can-we-release-gpu-memory-cache/14530/27
def clear_torch_cache():
    '''def _optimizer_to(device):
        for param in self.optimizer.state.values():
            # Not sure there are any global tensors in the state dict
            if isinstance(param, torch.Tensor):
                param.data = param.data.to(device)
                if param._grad is not None:
                    param._grad.data = param._grad.data.to(device)
            elif isinstance(param, dict):
                for subparam in param.values():
                    if isinstance(subparam, torch.Tensor):
                        subparam.data = subparam.data.to(device)
                        if subparam._grad is not None:
                            subparam._grad.data = subparam._grad.data.to(device)
    _optimizer_to(torch.device('cpu'))
    '''
    gc.collect()
    torch.cuda.empty_cache()



def instantiate_model(llm="OpenAI"):
    global llm_global
    llm_global = llm
    if llm == "Llama-2-7b-chat":

        ## THIS PART IS COMMENTED OUT ON LOCAL CPU DEPLOYMENT

        model_name_or_path = "TheBloke/Llama-2-7B-Chat-GPTQ"
        # To use a different branch, change revision
        # For example: revision="main"
        model = AutoModelForCausalLM.from_pretrained(model_name_or_path,
                                                     device_map="auto",
                                                     trust_remote_code=True,
                                                     revision="main")

        tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, use_fast=True)

        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_length=4000,
            do_sample=True,
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            repetition_penalty=1.1
        )
        global hf_global
        hf = HuggingFacePipeline(pipeline=pipe)
        hf_global = hf


    # noinspection PyUnreachableCode
def send_request(section_for_conversion, llm, format_chosen="legaldocml"):
    instantiate_model(llm)
    global llm_global
    global hf_global
    hf = hf_global

    example_prompt = ChatPromptTemplate.from_messages(
        [
            ("human", "{question}"),
            ("ai", "{answer}"),
        ]

    )

    example_selector = CustomExampleSelector()

    examples = example_selector.select_examples({"format_chosen": format_chosen})

    few_shot_prompt = FewShotChatMessagePromptTemplate(
        example_prompt=example_prompt,
        examples=examples,
    )
    if format_chosen == "legalruleml":
        sys_prompt = "You are a LegalRuleML converter who takes the statute text as input and outputs the XML format for the same with reference to the documentation available at http://docs.oasis-open.org/legalruleml/legalruleml-core-spec/v1.0/legalruleml-core-spec-v1.0.html"
    else:
        sys_prompt = "You are a LegalDocML converter who takes the statute text as input and outputs the XML format for the same with reference to the documentation available at http://docs.oasis-open.org/legaldocml/akn-core/v1.0/akn-core-v1.0-part1-vocabulary.html"
    final_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", sys_prompt),
            few_shot_prompt,
            ("human", "{question}"),
        ]
    )
    if llm_global == "OpenAI":
        llm_chain = final_prompt | openai_chain | output_parser
    else:
        llm_chain = final_prompt | hf

    result = llm_chain.invoke({"question": section_for_conversion})

    return result

def RAGPrompt (RetrieverObj, text_value, metamodel, metamodel_number):
    global global_metamodel
    global_metamodel= metamodel
    global global_metamodel_number
    global_metamodel_number = metamodel_number
    instantiate_model(llm=llm_global)
    global hf_global
    hf = hf_global

    # Since the context window did not have system_prompt, it was returning a deficient output (asking for more information or context)
    # In this strategy, the human_prompt itself is being used to provide the system prompt as context, using the tags accepted by Llama2 (see https://huggingface.co/blog/llama2)
    sys_prompt = """ou are an assistant that takes the XML generated and tweaks it in accordance with the rdfs metamodel provided to you below as context. 
        The XML is in compliance with the LegalRuleML core specification, whereas the metamodel provides an overview of what the XML should be for a particular category of XML elements."""
    human_prompt = """
        ### [INST] 
            <<SYS>>
            {system_prompt}

            The category being implemented is defined as follows:

            {metamodel_definition}

             <</SYS>>
            Use the following metamodel in RDFS to ensure that the XML generated is in terms of the definition of the metamodel provided in the LegalRuleML specification.

            {metamodel_XML}


            ### LEGAL_XML:
            {question} 
            [/INST]
        """
    # Use the following values as placeholders
    def get_relevant_metamodel(RetrieverObj):
        docs = RetrieverObj.get_relevant_documents("query")

        docs = docs.replace('\n', '')
        docs = docs.replace('\t', '')

        data = json.loads(docs)

        relevant_metamodel = data[2]["deontic"]
        return relevant_metamodel

    def get_relevant_definition(RetrieverObj):
        docs = RetrieverObj.get_relevant_documents("query")
        docs = docs.replace('\n', '')
        docs = docs.replace('\t', '')

        data = json.loads(docs)

        relevant_definition = data[2]["description"]
        return relevant_definition

    template = ChatPromptTemplate.from_messages([
        ("system", sys_prompt),
        ("human", human_prompt)
    ])

    metamodel_definition = get_relevant_metamodel(RetrieverObj)
    metamodel = get_relevant_metamodel(RetrieverObj)

    input_dict = {
        "system_prompt": sys_prompt,
        "metamodel_definition": metamodel_definition,
        "metamodel_XML": metamodel,
        "question": text_value,
    }
    print("Input_dict is ", input_dict)

    with open ("_cache/input_dict", "w") as fn:
        fn.write(str(input_dict))

    if llm_global == "OpenAI":
        openai = OpenAI(openai_api_key = openai_key)
        llm_chain = LLMChain(llm = openai_chain, prompt = template)
    else:
        llm_chain = LLMChain(llm=hf, prompt=template)

    new_text_value = llm_chain.invoke(input=input_dict)

    return new_text_value