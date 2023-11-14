"""This tutorial shows how to train an MADDPG agent on the space invaders atari environment.

Authors: Michael (https://github.com/mikepratt1), Nick (https://github.com/nicku-a)
"""
import os

import numpy as np
import supersuit as ss
import torch
from agilerl.components.multi_agent_replay_buffer import MultiAgentReplayBuffer
from agilerl.hpo.mutation import Mutations
from agilerl.hpo.tournament import TournamentSelection
from agilerl.utils.utils import initialPopulation
from tqdm import trange

from pettingzoo.atari import space_invaders_v2

if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("===== AgileRL Online Multi-Agent Demo =====")

    # Define the network configuration
    NET_CONFIG = {
        "arch": "cnn",  # Network architecture
        "h_size": [32, 32],  # Network hidden size
        "c_size": [3, 32],  # CNN channel size
        "k_size": [(1, 3, 3), (1, 3, 3)],  # CNN kernel size
        "s_size": [2, 2],  # CNN stride size
        "normalize": True,  # Normalize image from range [0,255] to [0,1]
    }

    # Define the initial hyperparameters
    INIT_HP = {
        "POPULATION_SIZE": 2,
        "ALGO": "MADDPG",  # Algorithm
        # Swap image channels dimension from last to first [H, W, C] -> [C, H, W]
        "CHANNELS_LAST": True,
        "BATCH_SIZE": 8,  # Batch size
        "LR": 0.01,  # Learning rate
        "GAMMA": 0.95,  # Discount factor
        "MEMORY_SIZE": 10000,  # Max memory buffer size
        "LEARN_STEP": 5,  # Learning frequency
        "TAU": 0.01,  # For soft update of target parameters
    }

    # Define the space invaders environment as a parallel environment
    env = space_invaders_v2.parallel_env()
    if INIT_HP["CHANNELS_LAST"]:
        # Environment processing for image based observations
        env = ss.frame_skip_v0(env, 4)
        env = ss.clip_reward_v0(env, lower_bound=-1, upper_bound=1)
        env = ss.color_reduction_v0(env, mode="B")
        env = ss.resize_v1(env, x_size=84, y_size=84)
        env = ss.frame_stack_v1(env, 4)
    env.reset()

    # Configure the multi-agent algo input arguments
    try:
        state_dim = [env.observation_space(agent).n for agent in env.agents]
        one_hot = True
    except Exception:
        state_dim = [env.observation_space(agent).shape for agent in env.agents]
        one_hot = False
    try:
        action_dim = [env.action_space(agent).n for agent in env.agents]
        INIT_HP["DISCRETE_ACTIONS"] = True
        INIT_HP["MAX_ACTION"] = None
        INIT_HP["MIN_ACTION"] = None
    except Exception:
        action_dim = [env.action_space(agent).shape[0] for agent in env.agents]
        INIT_HP["DISCRETE_ACTIONS"] = False
        INIT_HP["MAX_ACTION"] = [env.action_space(agent).high for agent in env.agents]
        INIT_HP["MIN_ACTION"] = [env.action_space(agent).low for agent in env.agents]

    # Pre-process image dimensions for pytorch convolutional layers
    if INIT_HP["CHANNELS_LAST"]:
        state_dim = [
            (state_dim[2], state_dim[0], state_dim[1]) for state_dim in state_dim
        ]

    # Append number of agents and agent IDs to the initial hyperparameter dictionary
    INIT_HP["N_AGENTS"] = env.num_agents
    INIT_HP["AGENT_IDS"] = env.agents

    # Create a population ready for evolutionary hyper-parameter optimisation
    pop = initialPopulation(
        INIT_HP["ALGO"],
        state_dim,
        action_dim,
        one_hot,
        NET_CONFIG,
        INIT_HP,
        population_size=INIT_HP["POPULATION_SIZE"],
        device=device,
    )

    # Configure the multi-agent replay buffer
    field_names = ["state", "action", "reward", "next_state", "done"]
    memory = MultiAgentReplayBuffer(
        INIT_HP["MEMORY_SIZE"],
        field_names=field_names,
        agent_ids=INIT_HP["AGENT_IDS"],
        device=device,
    )

    # Instantiate a tournament selection object (used for HPO)
    tournament = TournamentSelection(
        tournament_size=2,  # Tournament selection size
        elitism=True,  # Elitism in tournament selection
        population_size=INIT_HP["POPULATION_SIZE"],  # Population size
        evo_step=1,
    )  # Evaluate using last N fitness scores

    # Instantiate a mutations object (used for HPO)
    mutations = Mutations(
        algo=INIT_HP["ALGO"],
        no_mutation=0.2,  # Probability of no mutation
        architecture=0.2,  # Probability of architecture mutation
        new_layer_prob=0.2,  # Probability of new layer mutation
        parameters=0.2,  # Probability of parameter mutation
        activation=0,  # Probability of activation function mutation
        rl_hp=0.2,  # Probability of RL hyperparameter mutation
        rl_hp_selection=[
            "lr",
            "learn_step",
            "batch_size",
        ],  # RL hyperparams selected for mutation
        mutation_sd=0.1,  # Mutation strength
        # Define search space for each hyperparameter
        min_lr=0.0001,
        max_lr=0.01,
        min_learn_step=1,
        max_learn_step=120,
        min_batch_size=8,
        max_batch_size=64,
        agent_ids=INIT_HP["AGENT_IDS"],  # Agent IDs
        arch=NET_CONFIG["arch"],  # MLP or CNN
        rand_seed=1,
        device=device,
    )

    # Define training loop parameters
    max_episodes = 5  # Total episodes (default: 6000)
    max_steps = 900  # Maximum steps to take in each episode
    epsilon = 1.0  # Starting epsilon value
    eps_end = 0.1  # Final epsilon value
    eps_decay = 0.995  # Epsilon decay
    evo_epochs = 20  # Evolution frequency
    evo_loop = 1  # Number of evaluation episodes
    elite = pop[0]  # Assign a placeholder "elite" agent

    # Training loop
    for idx_epi in trange(max_episodes):
        for agent in pop:  # Loop through population
            state, info = env.reset()  # Reset environment at start of episode
            agent_reward = {agent_id: 0 for agent_id in env.agents}
            if INIT_HP["CHANNELS_LAST"]:
                state = {
                    agent_id: np.moveaxis(np.expand_dims(s, 0), [-1], [-3])
                    for agent_id, s in state.items()
                }
            for _ in range(max_steps):
                agent_mask = info["agent_mask"] if "agent_mask" in info.keys() else None
                env_defined_actions = (
                    info["env_defined_actions"]
                    if "env_defined_actions" in info.keys()
                    else None
                )

                # Get next action from agent
                cont_actions, discrete_action = agent.getAction(
                    state, epsilon, agent_mask, env_defined_actions
                )
                if agent.discrete_actions:
                    action = discrete_action
                else:
                    action = cont_actions

                next_state, reward, termination, truncation, info = env.step(
                    action
                )  # Act in environment

                # Image processing if necessary for the environment
                if INIT_HP["CHANNELS_LAST"]:
                    state = {agent_id: np.squeeze(s) for agent_id, s in state.items()}
                    next_state = {
                        agent_id: np.moveaxis(ns, [-1], [-3])
                        for agent_id, ns in next_state.items()
                    }

                # Save experiences to replay buffer
                memory.save2memory(state, cont_actions, reward, next_state, termination)

                # Collect the reward
                for agent_id, r in reward.items():
                    agent_reward[agent_id] += r

                # Learn according to learning frequency
                if (memory.counter % agent.learn_step == 0) and (
                    len(memory) >= agent.batch_size
                ):
                    experiences = memory.sample(
                        agent.batch_size
                    )  # Sample replay buffer
                    agent.learn(experiences)  # Learn according to agent's RL algorithm

                # Update the state
                if INIT_HP["CHANNELS_LAST"]:
                    next_state = {
                        agent_id: np.expand_dims(ns, 0)
                        for agent_id, ns in next_state.items()
                    }
                state = next_state

                # Stop episode if any agents have terminated
                if any(truncation.values()) or any(termination.values()):
                    break

            # Save the total episode reward
            score = sum(agent_reward.values())
            agent.scores.append(score)

        # Update epsilon for exploration
        epsilon = max(eps_end, epsilon * eps_decay)

        # Now evolve population if necessary
        if (idx_epi + 1) % evo_epochs == 0:
            # Evaluate population
            fitnesses = [
                agent.test(
                    env,
                    swap_channels=INIT_HP["CHANNELS_LAST"],
                    max_steps=max_steps,
                    loop=evo_loop,
                )
                for agent in pop
            ]

            print(f"Episode {idx_epi + 1}/{max_episodes}")
            print(f'Fitnesses: {["%.2f" % fitness for fitness in fitnesses]}')
            print(
                f'100 fitness avgs: {["%.2f" % np.mean(agent.fitness[-100:]) for agent in pop]}'
            )

            # Tournament selection and population mutation
            elite, pop = tournament.select(pop)
            pop = mutations.mutation(pop)

    # Save the trained algorithm
    path = "./models/MADDPG"
    filename = "MADDPG_trained_agent.pt"
    os.makedirs(path, exist_ok=True)
    save_path = os.path.join(path, filename)
    elite.saveCheckpoint(save_path)
