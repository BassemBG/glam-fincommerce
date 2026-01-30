"""Test how to properly initialize RAGAS metrics with LLM and embeddings"""
from ragas.metrics import answer_relevancy, faithfulness
from openai import OpenAI
from ragas.llms import llm_factory
from langchain_huggingface import HuggingFaceEmbeddings

# Create OpenAI client and llm
api_key = 'sk-test'
client = OpenAI(api_key=api_key)
llm = llm_factory('gpt-4o-mini', client=client)

embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')

print(f'answer_relevancy type: {type(answer_relevancy)}')
print(f'Has llm attr: {hasattr(answer_relevancy, "llm")}')
print(f'Methods: {[x for x in dir(answer_relevancy) if "with" in x or "set" in x]}')
