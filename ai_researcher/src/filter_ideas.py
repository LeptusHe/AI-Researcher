from utils import call_api, create_client
import argparse
import json
import os
from utils import cache_output, format_plan_json, avg_score
import random 
from tqdm import tqdm
import retry
from collections import defaultdict
from lit_review import collect_papers
from lit_review_tools import format_papers_for_printing, print_top_papers_from_paper_bank
random.seed(2024)

@retry.retry(tries=3, delay=2)
def self_novelty_score(experiment_plan, openai_client, model, seed, client_type=None):
    prompt = "You are a professor specialized in Mobile Graphics, Real-time Rendering, and Game Engine Optimization. You are given a project proposal and you need to decide whether it is novel enough.\n"
    prompt += "The project proposal is:\n\n" 
    prompt += format_plan_json(experiment_plan)
    prompt += "\nReturn yes if the project is significantly different from existing work (both classic ones and recent ones), otherwise return no. Give a short rationale and then change to a new line to return either yes or no and then end the response.\n"
    prompt += "In the rationale, reference the most similar works and explain how the proposed project is similar to or different from them. You should return no if the proposed project is only a minor modification or combination of the existing ideas.\n"

    prompt_messages = [{"role": "user", "content": prompt}]
    response, cost = call_api(openai_client, model, prompt_messages, temperature=0., max_tokens=3000, seed=seed, json_output=False, client_type=client_type)
    return prompt, response, cost

@retry.retry(tries=3, delay=2)
def feasibility_score(experiment_plan, openai_client, model, seed, client_type=None):
    prompt = "You are a professor specialized in Mobile Graphics, Real-time Rendering, and Game Engine Optimization. You are given a project proposal and you need to decide whether it is feasible.\n"
    prompt += "The project proposal is:\n\n"
    prompt += format_plan_json(experiment_plan)
    prompt += "\nLook specifically at the hardware and resource requirements: return no if the experiments require hardware that is not readily available (e.g., custom silicon, unreleased GPUs), or require creating entirely new 3D assets/scenes from scratch with significant manual modeling effort. Return yes if the proposed experiments can be conducted using existing mobile devices (Android/iOS phones or tablets), publicly available 3D scene datasets (e.g., from graphics research benchmarks), standard GPU profiling tools, and common game engine frameworks (Unity, Unreal, or custom lightweight engines). The principle is that we cannot afford to create new 3D assets from scratch if it requires too much manual effort or specialized hardware.\n"
    prompt += "Give a short explanation first and then change to a new line to return either yes or no and then end the response.\n"

    prompt_messages = [{"role": "user", "content": prompt}]
    response, cost = call_api(openai_client, model, prompt_messages, temperature=0., max_tokens=3000, seed=seed, json_output=False, client_type=client_type)
    return prompt, response, cost

@retry.retry(tries=3, delay=2)
def consistency_score(experiment_plan, openai_client, model, seed, client_type=None):
    prompt = "You are a professor specialized in Mobile Graphics, Real-time Rendering, and Game Engine Optimization. You are given a project proposal and you need to decide whether it is consistent in the methodology and experiment design.\n"
    prompt += "The project proposal is:\n\n"
    prompt += format_plan_json(experiment_plan)
    prompt += "\nYou should return no if the proposed method claims to target mobile devices but proposes experiments that require desktop-class GPUs (e.g., NVIDIA RTX 4090, high-end workstation GPUs) or resources far exceeding mobile constraints (e.g., >8GB VRAM, >100W power budget). You should also reject ideas that claim real-time performance but propose methods with computational complexity clearly incompatible with real-time constraints on mobile (e.g., full-resolution ray tracing without acceleration structures, unoptimized neural networks with millions of parameters running per-pixel). Additionally, reject proposals that mix incompatible graphics APIs (e.g., claiming Vulkan optimization but testing only on OpenGL ES without justification) or propose infeasible experiments (e.g., measuring power consumption without access to hardware power measurement tools).\n"
    prompt += "Only return yes if the proposed method is consistent: the target platform matches the experimental setup, the claimed performance characteristics are plausible given the hardware constraints, and all proposed experiments are indeed feasible to execute on the stated target hardware. Give a short explanation first and then change to a new line to return either yes or no and then end the response.\n"

    prompt_messages = [{"role": "user", "content": prompt}]
    response, cost = call_api(openai_client, model, prompt_messages, temperature=0., max_tokens=3000, seed=seed, json_output=False, client_type=client_type)
    return prompt, response, cost

@retry.retry(tries=3, delay=2)
def significance_score(experiment_plan, openai_client, model, seed, client_type=None):
    prompt = "You are a professor specialized in Mobile Graphics, Real-time Rendering, and Game Engine Optimization. You are given a project proposal and you need to decide whether the problem that it is solving is significant enough.\n"
    prompt += "The project proposal is:\n\n"
    prompt += format_plan_json(experiment_plan)
    prompt += "\nYou should return no if the problem to be solved is not particularly important for mobile graphics or game engines. For example, optimizing rendering for hardware that is already fast enough (e.g., desktop GPUs) without mobile constraints is not significant for our focus. You should also say no to ideas that are just minor parameter tuning of existing rendering pipelines. You should also say no to ideas that are too niche or outdated (i.e., already well solved by modern mobile GPUs or existing engine features). You should also say no to ideas that are too simple or trivial, for example just enabling an existing engine feature or adjusting quality settings without proposing a new algorithmic approach.\n"
    prompt += "Only return yes if the proposed problem is either: 1) a well-recognized problem in mobile graphics with existing benchmarks and baselines (e.g., mobile rendering quality, frame rate stability, power efficiency); or 2) a new problem that has been overlooked by the research community and has high significance for mobile gaming or AR/VR applications. Give a short explanation first and then change to a new line to return either yes or no and then end the response.\n"

    prompt_messages = [{"role": "user", "content": prompt}]
    response, cost = call_api(openai_client, model, prompt_messages, temperature=0., max_tokens=3000, seed=seed, json_output=False, client_type=client_type)
    return prompt, response, cost

@retry.retry(tries=3, delay=2)
def relevance_score(experiment_plan, topic, openai_client, model, seed, client_type=None):
    prompt = "You are a professor specialized in Mobile Graphics, Real-time Rendering, and Game Engine Optimization. You are given a project proposal and you need to decide whether the project proposal is directly relevant to the specified topic.\n"
    prompt += "The project proposal is:\n\n"
    prompt += format_plan_json(experiment_plan)
    prompt += "\n\nThe specified topic is:\n" + topic + "\n\n"
    prompt += "\nYou should return no if the project proposal is off-topic or is only loosely relevant. For example, if the topic is about mobile rendering optimization, then projects about desktop-only ray tracing or general machine learning without graphics applications should not be accepted because they are not directly relevant."
    prompt += "Only return yes if the project is directly relevant to the specific topic. Give a short explanation first and then change to a new line to return either yes or no and then end the response.\n"

    prompt_messages = [{"role": "user", "content": prompt}]
    response, cost = call_api(openai_client, model, prompt_messages, temperature=0., max_tokens=3000, seed=seed, json_output=False, client_type=client_type)
    return prompt, response, cost

@retry.retry(tries=3, delay=2)
def retrieve_novelty_score(experiment_plan, related_paper, openai_client, model, seed, client_type=None):
    ## use gpt4 to give novelty judgment wrt one individual paper
    prompt = "You are a professor specialized in Mobile Graphics and Real-time Rendering. You have a project proposal and want to decide whether it is novel or has been done before.\n\n"
    prompt += "The project proposal is:\n" + format_plan_json(experiment_plan) + ".\n\n"
    prompt += "We have found a related paper:\n" + format_papers_for_printing([related_paper], include_score=False) + "\n\n"
    prompt += "The project proposal and paper abstract are considered a match if both the research problem and the approach are the same. For example, if they are both trying to improve code generation accuracy and both propose to use retrieval augmentation. You should answer yes if the proposed project is exploring essentially the same idea as the given related paper, and answer no otherwise.\n"
    prompt += "You should first specify what is the proposed research problem and approach. If answering yes, your explanation should be the one-sentence summary of both the abstract and the proposal and their similarity (e.g., they are both about probing biases of language models via fictional characters). If answering no, give the short summaries of the abstract and proposal separately, then highlight their differences. Then end your response with a binary judgment, saying either \"Yes\" or \"No\". Change to a new line after your explanation and just say Yes or No with no punctuation in the end.\n"

    prompt_messages = [{"role": "user", "content": prompt}]
    response, cost = call_api(openai_client, model, prompt_messages, temperature=0., max_tokens=3000, seed=seed, json_output=False, client_type=client_type)
    return prompt, response, cost

@retry.retry(tries=3, delay=2)
def all_checks(topic_description, experiment_plan, client, model, seed, consistency_check=True, feasibility_check=True, significance_check=True, relevance_check=False, self_novelty_check=False, retrieve_novelty_check=True, client_type=None):
    all_cost = 0
    
    ## perform all the checks
    if consistency_check:
        print ("\nPerforming Consistency Check")
        consistency_prompt, consistency_response, consistency_cost = consistency_score(experiment_plan, client, model, seed, client_type=client_type)
        all_cost += consistency_cost
        # print (consistency_prompt)
        print (consistency_response)
        if consistency_response.lower().split()[-1].strip() != "yes":
            print ("Failed Consistency Check!")
            return False, None
        
    if feasibility_check:
        print ("\nPerforming Feasibility Check")
        feasibility_prompt, feasibility_response, feasibility_cost = feasibility_score(experiment_plan, client, model, seed, client_type=client_type)
        all_cost += feasibility_cost
        # print (feasibility_prompt)
        print (feasibility_response)
        if feasibility_response.lower().split()[-1].strip() != "yes":
            print ("Failed Feasibility Check!")
            return False, None
    
    if significance_check:
        print ("\nPerforming Significance Check")
        significance_prompt, significance_response, significance_cost = significance_score(experiment_plan, client, model, seed, client_type=client_type)
        all_cost += significance_cost
        # print (significance_prompt)
        print (significance_response)
        if significance_response.lower().split()[-1].strip() != "yes":
            print ("Failed Significance Check!")
            return False, None
    
    if relevance_check:
        print ("\nPerforming Relevance Check")
        relevance_prompt, relevance_response, relevance_cost = relevance_score(experiment_plan, topic_description, client, model, seed, client_type=client_type)
        all_cost += relevance_cost
        # print (relevance_prompt)
        print (relevance_response)
        if relevance_response.lower().split()[-1].strip() != "yes":
            print ("Failed Relevance Check!")
            return False, None
    
    if self_novelty_check:
        print ("\nPerforming Self-Novelty Check")
        self_novelty_prompt, self_novelty_response, self_novelty_cost = self_novelty_score(experiment_plan, client, model, seed, client_type=client_type)
        all_cost += self_novelty_cost
        # print (self_novelty_prompt)
        print (self_novelty_response)
        if self_novelty_response.lower().split()[-1].strip() != "yes":
            print ("Failed Self-Novelty Check!")
            return False, None
    
    if retrieve_novelty_check:
        print ("\nPerforming Retrieval-Novelty Check")
        try:
            paper_bank, total_cost, all_queries = collect_papers(topic_description, client, model, seed, grounding_k=10, max_papers=100, print_all=False, mode="idea", idea=experiment_plan, client_type=client_type)
            all_cost += total_cost
            print ("Top-10 Retrieved Papers:")
            output = format_papers_for_printing(paper_bank[ : 10])
            print (output)
            print ("\n")
            ## check through the top-10 papers
            for related_paper in paper_bank[ : 10]:
                retrieve_novelty_prompt, retrieve_novelty_response, retrieve_novelty_cost = retrieve_novelty_score(experiment_plan, related_paper, client, model, seed, client_type=client_type)
                all_cost += retrieve_novelty_cost
                if retrieve_novelty_response.lower().split()[-1].strip() != "no":
                    print ("Failed Related Paper Check!")
                    print (retrieve_novelty_prompt)
                    print (retrieve_novelty_response)
                    return False, None
        except:
            print ("Retrieval Error. Default to failure.")
            return False, None

    print ("cost: ", all_cost)
    return True, paper_bank[ : 10]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', type=str, default='claude-3-5-sonnet-20240620', help='api engine; https://openai.com/api/')
    parser.add_argument('--cache_dir', type=str, default="uncertainty_prompting_method_prompting", help='cache file name for the retrieved papers')
    parser.add_argument('--cache_name', type=str, default="uncertainty_prompting_method_prompting", help='cache file name for the retrieved papers')
    parser.add_argument('--score_file', type=str, default="uncertainty_score_predictions_swiss_round_5", help='score file for reranking ideas')
    parser.add_argument('--passed_cache_dir', type=str, default="uncertainty_prompting_method_prompting", help='cache dir for all passed ideas')
    parser.add_argument('--seed', type=int, default=2024, help="seed for GPT-4 generation")
    args = parser.parse_args()

    client, client_type = create_client(args.engine)
    random.seed(args.seed)
    
    with open(args.score_file, "r") as f:
        scores = json.load(f)
    
    top_ideas = sorted(scores, key=scores.get, reverse=True)
    print ("#ideas: ", len(top_ideas))
    
    passed_filenames = []
    passed_ideas = []
    for filename in tqdm(top_ideas):
        with open(os.path.join(args.cache_dir, args.cache_name, filename), "r") as f:
            idea = json.load(f)
            experiment_plan = idea["full_experiment_plan"]
            topic_description = idea["topic_description"]
        
        check, paper_bank = all_checks(topic_description, experiment_plan, client, args.engine, args.seed, client_type=client_type)
        if check:
            print ("Idea Passed: ", filename)
            print (format_plan_json(experiment_plan, indent_level=0, skip_test_cases=False, skip_fallback=False) + "\n\n")
            
            idea["novelty_check_papers"] = paper_bank
            passed_ideas.append(idea)
            passed_filenames.append(filename)

            ## save passed ideas including the novelty check papers
            cache_file = os.path.join(args.passed_cache_dir, args.cache_name, filename)
            if not os.path.exists(os.path.dirname(cache_file)):
                os.makedirs(os.path.dirname(cache_file))
            with open(cache_file, "w") as f:
                json.dump(idea, f, indent=4)
        
        print ("#passed ideas: ", len(passed_ideas))
        print ("\n\n")

        # if len(passed_ideas) >= 20:
        #     break
    
    print ("#total passed ideas: ", len(passed_ideas))
    print ("\n\nAll Passed Ideas:")
    print ("-" * 50)
    
    ## print all passed ideas 
    for filename, idea in zip(passed_filenames, passed_ideas):
        print (filename)
        print (format_plan_json(idea["full_experiment_plan"], indent_level=0, skip_test_cases=False, skip_fallback=False) + "\n")
        print ("-" * 50)