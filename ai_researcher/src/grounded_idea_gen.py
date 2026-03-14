from utils import call_api, create_client, shuffle_dict_and_convert_to_string
import argparse
import json
import os
from lit_review_tools import format_papers_for_printing
from utils import cache_output
import random 
import retry
import sys

@retry.retry(tries=3, delay=2)
def idea_generation(method, existing_ideas, paper_bank, grounding_k, examples, ideas_n, topic_description, openai_client, model, seed, temperature, top_p, max_tokens, RAG=True, client_type=None):
    ## retrieve top papers (with some randomization)
    top_papers = paper_bank[ : int(grounding_k * 2)]
    random.shuffle(top_papers)
    grounding_papers = top_papers[ : grounding_k]

    prompt = "You are an expert researcher in mobile graphics and real-time rendering. Now I want you to help me brainstorm some new research project ideas on the topic of: " + topic_description + ".\n\n"
    if RAG:
        prompt += "Here are some relevant papers on this topic just for your background knowledge:\n" + format_papers_for_printing(grounding_papers, include_score=False, include_id=False) + "\n"
    prompt += "You should generate {} different ideas on this topic. Try to be creative and diverse in the idea generation, and do not repeat any similar ideas. ".format(str(ideas_n))
    if RAG:
        prompt += "The above papers are only for inspiration and you should not cite them and just make some incremental modifications. Instead, you should make sure your ideas are novel and distinct from the prior literature. "
    prompt += "You should aim for projects that can potentially win best paper awards at top graphics conferences like SIGGRAPH and Eurographics.\n"
    prompt += "Each idea should be described as: (1) Problem: State the problem statement, which should be closely related to the topic description and a real challenge in mobile graphics or real-time rendering. (2) Existing Methods: Mention some existing benchmarks and baseline methods if there are any. (3) Motivation: Explain the inspiration of the proposed method and why it would work well. (4) Proposed Method: Propose your new method and describe it in detail. The proposed method should be maximally different from all existing work and baselines, and be more advanced and effective than the baselines. You should be as creative as possible in proposing new methods, we love unhinged ideas that sound crazy. This should be the most detailed section of the proposal. (5) Experiment Plan: Specify the experiment steps, baselines, and evaluation metrics (e.g., frame rate, PSNR/SSIM, power consumption, GPU memory usage).\n"
    prompt += "You can follow these examples to get a sense of how the ideas should be formatted (but don't borrow the ideas themselves):\n" + examples + "\n"
    prompt += "You should make sure to come up with your own novel and different ideas for the specified problem: " + topic_description + ". You should try to tackle important problems that are well recognized in the mobile graphics and game engine community and considered challenging for current hardware and software. For example, think of novel solutions for problems with existing benchmarks and baselines. In rare cases, you can propose to tackle a new problem, but you will have to justify why it is important and how to set up proper evaluation.\n"
    if "claude" in model:
        prompt += "You should make each idea standalone and not dependent on the other ideas.\n"
    if method == "rendering_optimization":
        prompt += "Focus on novel rendering optimization ideas for mobile GPUs. The proposed method should specify how to optimize the rendering pipeline, including shader optimizations, draw call reduction, LOD strategies, texture compression, or bandwidth-saving techniques. All methods must be feasible on mobile GPUs (Adreno, Mali, Apple GPU) with limited VRAM and bandwidth.\n"
    elif method == "neural_graphics":
        prompt += "Focus on novel neural graphics ideas optimized for mobile deployment. The proposed method should specify the neural network architecture, how to achieve real-time inference on mobile GPUs, and what rendering quality vs. performance tradeoffs are made. Consider techniques like model distillation, quantization, or hybrid neural-traditional rendering.\n"
    else:
        prompt += "Focus on proposing novel methods for mobile graphics and game engine optimization, which can include rendering pipeline optimization, neural rendering, engine architecture improvements, GPU API optimization, etc. The proposed method section should specify all the details involved, such as the rendering technique, target hardware constraints, performance metrics, and evaluation methodology.\n"
    if existing_ideas:
        prompt += "You should avoid repeating the following existing ideas and try to be different and diverse: " + existing_ideas + "\n"
    prompt += "Please write down your {} ideas (each idea should be described as one paragraph. Output the ideas in json format as a dictionary, where you should generate a short idea name (e.g., \"Adaptive LOD for Mobile\", or \"Neural Texture Compression\") as the key and the actual idea description as the value (following the above format). Do not repeat idea names or contents.".format(str(ideas_n))

    prompt_messages = [{"role": "user", "content": prompt}]
    response, cost = call_api(openai_client, model, prompt_messages, temperature=temperature, top_p=top_p, max_tokens=max_tokens, seed=seed, json_output=True, client_type=client_type)
    return prompt, response, cost

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', type=str, default='claude-3-opus-20240229', help='api engine; https://openai.com/api/')
    parser.add_argument('--paper_cache', type=str, default=None, required=True, help='cache file name for the retrieved papers')
    parser.add_argument('--idea_cache', type=str, default=None, required=True, help='where to store the generated ideas')
    parser.add_argument('--RAG', type=str, default="True", required=True, help='whether to do RAG for idea generation')
    parser.add_argument('--method', type=str, default='rendering_optimization', help='either rendering_optimization, neural_graphics, or engine_architecture')
    parser.add_argument('--grounding_k', type=int, default=10, help='how many papers to use for grounding')
    parser.add_argument('--append_existing_ideas', type=str, default="True", help='whether to append existing ideas to the idea cache')
    parser.add_argument('--max_tokens', type=int, default=30000, help='max tokens in the output')
    parser.add_argument('--temperature', type=float, default=1.0, help='temperature in sampling')
    parser.add_argument('--top_p', type=float, default=1.0, help='top p in sampling')
    parser.add_argument('--ideas_n', type=int, default=5, help="how many ideas to generate")
    parser.add_argument('--seed', type=int, default=2024, help="seed for GPT-4 generation")
    parser.add_argument('--debug', action='store_true', help="enable debug mode")
    args = parser.parse_args()

    client, client_type = create_client(args.engine)
    random.seed(args.seed)
    
    with open(args.paper_cache, "r") as f:
        lit_review = json.load(f)
    
    topic_description = lit_review["topic_description"]
    paper_bank = lit_review["paper_bank"]

    ## cache dir and file
    if args.RAG == "True":
        print ("RAG is enabled for idea generation")
    else:
        print ("RAG is disabled for idea generation")
    ideas_file = args.idea_cache
    
    # extract existing ideas
    existing_ideas = None
    if os.path.exists(ideas_file) and args.append_existing_ideas == "True":
        with open(ideas_file, "r") as f:
            ideas_cache = json.load(f)
        if "ideas" in ideas_cache:
            existing_ideas = [key for idea in ideas_cache["ideas"] for key in idea.keys()]
            existing_ideas = list(set(existing_ideas))
            existing_ideas = "; ".join(existing_ideas)
            print ("Appending previous ideas.")
    else:
        print ("Not appending previous ideas.")
    
    if args.method == "rendering_optimization":
        with open("prompts/idea_examples_prompting_method.json", "r") as f:
            method_idea_examples = json.load(f)
            method_idea_examples = shuffle_dict_and_convert_to_string(method_idea_examples)
    elif args.method == "neural_graphics":
        with open("prompts/idea_examples_finetuning_method.json", "r") as f:
            method_idea_examples = json.load(f)
            method_idea_examples = shuffle_dict_and_convert_to_string(method_idea_examples)
    else:
        with open("prompts/idea_examples_method.json", "r") as f:
            method_idea_examples = json.load(f)
            method_idea_examples = shuffle_dict_and_convert_to_string(method_idea_examples, n=4)
    
    print ("topic: ", topic_description)
    print ("existing ideas: ", existing_ideas)
    print ("\n")
    print ("generating {} ideas...".format(str(args.ideas_n)))
    
    if not args.debug:
        try:
            prompt, response, cost = idea_generation(args.method, existing_ideas, paper_bank, args.grounding_k, method_idea_examples, args.ideas_n, topic_description, client, args.engine, args.seed, args.temperature, args.top_p, args.max_tokens, args.RAG, client_type=client_type)
        except:
            print ("Error in idea generation...")
            sys.exit(1)
    else:
        prompt, response, cost = idea_generation(args.method, existing_ideas, paper_bank, args.grounding_k, method_idea_examples, args.ideas_n, topic_description, client, args.engine, args.seed, args.temperature, args.top_p, args.max_tokens, args.RAG, client_type=client_type)
    
    print ("idea generation cost: ", cost)
    # print ("prompt: ", prompt)
    # print ("response: ", response)
    # print ("---------------------------------------\n")

    response = json.loads(response.strip())
    ideas = {"topic_description": topic_description, "ideas": [response]}
    
    ## if the idea_cache already exists, directly add to the current list
    if os.path.exists(ideas_file):
        with open(ideas_file, "r") as f:
            ideas_cache = json.load(f)
        ideas_cache["ideas"].append(response)
        ideas = ideas_cache
    
    print ("#ideas generated so far: ", sum(len(d) for d in ideas["ideas"]))

    ## save the cache
    cache_dir = os.path.dirname(ideas_file)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    cache_output(ideas, ideas_file)
