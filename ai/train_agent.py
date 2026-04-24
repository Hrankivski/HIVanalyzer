import os
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from ai.rl_environment import HVACEnv


def make_env():
    def _init():
        return HVACEnv()

    return _init


if __name__ == "__main__":
    print("Starting PPO Training Pipeline...")

    # Крок 3: Hardware Optimization (Многопоточність)
    num_cpu = 4
    print(f"Initializing {num_cpu} parallel environments...")
    env = SubprocVecEnv([make_env() for i in range(num_cpu)])

    # Крок 2: Конфігурація RL Агента (PPO)
    policy_kwargs = dict(net_arch=dict(pi=[64, 64], vf=[64, 64]))

    print("Configuring PPO Agent with tuned hyperparameters...")
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        tensorboard_log="./logs/",
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        policy_kwargs=policy_kwargs,
    )

    print("Training Agent... Monitor progress using: tensorboard --logdir ./logs/")
    # Почни з 100 тис. для тесту
    model.learn(total_timesteps=100000)

    # Збереження моделі
    os.makedirs("models", exist_ok=True)
    save_path = "models/recuperator_agent_v1"
    model.save(save_path)
    print(f"Training completed! Model successfully saved to {save_path}.zip")
